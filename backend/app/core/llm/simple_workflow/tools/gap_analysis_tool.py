from app.core.llm.simple_workflow.utils.extract_data_from_ctx_by_key import extract_data_from_ctx_by_key
from app.core.llm.simple_workflow.tools.clustering_analysis_tool import cuterize_dataset
from app.database.session import get_async_session
from app.services.user_dataset_service import UserDatasetService
from app.utils.logging import get_logger

import pandas as pd
import numpy as np
from llama_index.core.workflow import Context
from typing import Dict, List, Any

logger = get_logger(__name__)


async def detect_gaps_from_clusters(ctx: Context, dataset_name: str, min_cluster_size: int = 5) -> str:
    """Detect gaps and opportunities from clustered data.
    
    This tool identifies:
    1. Underrepresented clusters (potential gaps)
    2. Outlier patterns (edge cases or niche needs)
    3. Missing themes (by analyzing cluster coverage)
    4. Feature requests or unmet needs from cluster analysis
    
    The tool first checks if clustering has been performed. If not, it triggers clustering
    before performing gap analysis.
    
    Args:
        ctx: Context
        dataset_name: Name of the dataset to analyze
        min_cluster_size: Minimum cluster size for clustering (default: 5)
    
    Returns:
        str: Markdown formatted gap analysis report
    """
    async with get_async_session() as db:
        try:
            # First, check if clustering data exists
            ctx_state = await ctx.store.get("state", {})
            dataset_data = ctx_state.get("dataset_data", {})
            clustering_data = dataset_data.get("clustering", {})
            
            # If clustering doesn't exist, perform it first
            if dataset_name not in clustering_data:
                logger.info(f"No clustering data found for '{dataset_name}'. Performing clustering first...")
                clustering_result = await cuterize_dataset(ctx, dataset_name, min_cluster_size)
                
                if clustering_result.startswith("Error"):
                    return f"Error: Failed to perform clustering before gap analysis: {clustering_result}"
                
                # Refresh context state after clustering
                ctx_state = await ctx.store.get("state", {})
                dataset_data = ctx_state.get("dataset_data", {})
                clustering_data = dataset_data.get("clustering", {})
            
            # Get clustered data
            data = clustering_data.get(dataset_name)
            if data is None or data.empty:
                return f"Error: No clustered data found for '{dataset_name}'"
            
            if "__cluster_id__" not in data.columns:
                return f"Error: Dataset '{dataset_name}' has not been clustered. Run clustering first."
            
            # Analyze clusters for gaps
            cluster_labels = data["__cluster_id__"]
            unique_clusters = sorted([c for c in set(cluster_labels) if c != -1])
            noise_count = (cluster_labels == -1).sum()
            total_points = len(data)
            
            # Calculate cluster sizes and percentages
            cluster_stats = []
            for cluster_id in unique_clusters:
                cluster_data = data[data["__cluster_id__"] == cluster_id]
                cluster_size = len(cluster_data)
                percentage = (cluster_size / total_points) * 100
                cluster_stats.append({
                    "cluster_id": cluster_id,
                    "size": cluster_size,
                    "percentage": percentage,
                    "data": cluster_data
                })
            
            # Sort by size
            cluster_stats.sort(key=lambda x: x["size"], reverse=True)
            
            # Build gap analysis report
            report = []
            report.append(f"# Gap Analysis Report for '{dataset_name}'")
            report.append(f"\n**Total Data Points:** {total_points}")
            report.append(f"**Clustered Points:** {total_points - noise_count} ({((total_points - noise_count) / total_points * 100):.1f}%)")
            report.append(f"**Noise/Outliers:** {noise_count} ({(noise_count / total_points * 100):.1f}%)")
            report.append(f"**Number of Clusters:** {len(unique_clusters)}\n")
            
            # 1. Identify underrepresented clusters (potential gaps)
            report.append("## 1. Underrepresented Clusters (Potential Gaps)")
            avg_cluster_size = np.mean([cs["size"] for cs in cluster_stats])
            underrepresented = [cs for cs in cluster_stats if cs["size"] < avg_cluster_size * 0.5]
            
            if underrepresented:
                report.append(f"\n**Found {len(underrepresented)} underrepresented clusters** (less than 50% of average size):\n")
                for cs in underrepresented[:5]:  # Top 5 smallest
                    report.append(f"### Cluster {cs['cluster_id']}")
                    report.append(f"- **Size:** {cs['size']} items ({cs['percentage']:.1f}% of total)")
                    report.append(f"- **Gap Indicator:** This cluster is {(avg_cluster_size / cs['size']):.1f}x smaller than average")
                    
                    # Show sample data (at least 5 examples)
                    sample_cols = [col for col in data.columns if col not in ["__embedding__", "__cluster_id__"]]
                    report.append("\n**Sample Data:**")
                    report.append(cs["data"][sample_cols].head(5).to_markdown(index=False))
                    report.append("")
            else:
                report.append("\n*No significantly underrepresented clusters found.*\n")
            
            # 2. Outlier analysis (noise points)
            report.append("## 2. Outlier Analysis (Edge Cases & Niche Needs)")
            outlier_percentage = (noise_count / total_points) * 100 if total_points > 0 else 0
            if noise_count > 0:
                report.append(f"\n**{noise_count} outlier points detected** ({outlier_percentage:.1f}% of total)")
                
                if outlier_percentage > 10:
                    report.append("\n⚠️ **High outlier rate** suggests:")
                    report.append("- Diverse, unmet needs not covered by main themes")
                    report.append("- Potential for new product features or segments")
                    report.append("- Data quality issues (if outliers seem irrelevant)")
                
                # Show sample outliers
                outlier_data = data[data["__cluster_id__"] == -1]
                sample_cols = [col for col in data.columns if col not in ["__embedding__", "__cluster_id__"]]
                report.append("\n**Sample Outliers:**")
                report.append(outlier_data[sample_cols].head(5).to_markdown(index=False))
                report.append("")
            else:
                report.append("\n*No significant outliers detected. Good cluster coverage!*\n")
            
            # 3. Cluster distribution analysis with sample data for ALL clusters
            report.append("## 3. All Clusters with Sample Data")
            report.append("\n**Complete Cluster Analysis:**\n")
            
            for cs in cluster_stats:  # ALL clusters
                report.append(f"### Cluster {cs['cluster_id']}")
                report.append(f"- **Size:** {cs['size']} items ({cs['percentage']:.1f}% of total)")
                status = "✓ Well-represented" if cs['size'] >= avg_cluster_size else "⚠️ Underrepresented"
                report.append(f"- **Status:** {status}")
                
                # Show sample data for this cluster (5 examples)
                sample_cols = [col for col in data.columns if col not in ["__embedding__", "__cluster_id__"]]
                report.append("\n**Sample Data:**")
                report.append(cs["data"][sample_cols].head(5).to_markdown(index=False))
                report.append("")
            
            # 4. Gap recommendations
            report.append("## 4. Gap Analysis Recommendations")
            report.append("\n**Key Insights:**\n")
            
            # Calculate concentration (top 3 clusters)
            top3_percentage = sum([cs["percentage"] for cs in cluster_stats[:3]])
            if top3_percentage > 70:
                report.append(f"- 🎯 **High Concentration:** Top 3 clusters contain {top3_percentage:.1f}% of data")
                report.append("  - Consider: Are we over-focusing on a few themes?")
                report.append("  - Opportunity: Explore underrepresented clusters for innovation")
            
            if len(underrepresented) > len(unique_clusters) * 0.3:
                report.append(f"- 📊 **Many Small Clusters:** {len(underrepresented)} clusters are underrepresented")
                report.append("  - Suggests: Diverse needs not being adequately addressed")
                report.append("  - Action: Investigate these clusters for product gaps")
            
            if outlier_percentage > 15:
                report.append(f"- 🔍 **High Outlier Rate:** {outlier_percentage:.1f}% of data points are outliers")
                report.append("  - Indicates: Significant unmet needs or edge cases")
                report.append("  - Recommendation: Deep dive into outlier patterns")
            
            # Store gap analysis results in context
            async with ctx.store.edit_state() as ctx_state:
                if "state" not in ctx_state:
                    ctx_state["state"] = {}
                if "gap_analysis" not in ctx_state["state"]:
                    ctx_state["state"]["gap_analysis"] = {}
                
                ctx_state["state"]["gap_analysis"][dataset_name] = {
                    "total_clusters": len(unique_clusters),
                    "underrepresented_clusters": len(underrepresented),
                    "outlier_count": noise_count,
                    "outlier_percentage": outlier_percentage,
                    "top3_concentration": top3_percentage,
                    "cluster_stats": cluster_stats
                }
            # TODO: add clf to detect gap
            # TODO: add sample on each cluster
            result = "\n".join(report)
            logger.info(f"Gap analysis completed for '{dataset_name}': {len(unique_clusters)} clusters, {len(underrepresented)} gaps identified")
            
            return result
            
        except Exception as e:
            logger.error(f"Error performing gap analysis: {e}", exc_info=True)
            return f"Error: {str(e)}"
