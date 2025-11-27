from langchain_core.tools import tool
from app.core.llm.lg_workflow.data.manager import DataManager
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
import pandas as pd
import asyncio
import numpy as np


@tool
async def clustering_tool(table_name: str, target_column: str, user_id: str, n_clusters: int = 3) -> str:
    """
    Performs K-Means clustering on a numeric column of a dataset.
    Returns a comprehensive clustering analysis report with:
    - Cluster distribution and sizes
    - Statistical summary for each cluster
    - Sample data from each cluster
    - Insights about cluster characteristics
    
    Updates the dataset with a new 'cluster' column containing cluster IDs (0 to n_clusters-1).
    """
    dm = DataManager.get_instance("default")
    
    df = await dm.get_dataset(table_name, user_id)
    if df is None or df.empty:
        return f"Error: Dataset '{table_name}' not found or empty."
    
    if target_column not in df.columns:
        available_cols = ", ".join(df.columns[:10].tolist())
        return f"Error: Column '{target_column}' not found. Available columns: {available_cols}"
        
    # Simple numeric check
    if not pd.api.types.is_numeric_dtype(df[target_column]):
        return f"Error: Column '{target_column}' is not numeric. K-Means clustering requires numeric data."

    # Perform Clustering
    def _cluster():
        # Prepare data - only use rows without NaN in target column
        data = df[[target_column]].dropna()
        
        if len(data) < n_clusters:
            return None, None, f"Error: Not enough data points ({len(data)}) for {n_clusters} clusters. Need at least {n_clusters} data points."
        
        # Perform K-Means clustering
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        clusters = kmeans.fit_predict(data)
        
        # Create result dataframe with cluster assignments
        result_df = df.copy()
        result_df['cluster'] = pd.Series(-1, index=result_df.index)  # Initialize with -1 (unclustered)
        result_df.loc[data.index, 'cluster'] = clusters
        
        # Build comprehensive report
        report = []
        report.append(f"# K-Means Clustering Analysis: '{table_name}'")
        report.append(f"\n**Target Column:** {target_column}")
        report.append(f"**Number of Clusters:** {n_clusters}")
        report.append(f"**Algorithm:** K-Means")
        report.append(f"**Total Data Points:** {len(result_df)}")
        report.append(f"**Clustered Points:** {len(data)}")
        
        unclustered = len(result_df) - len(data)
        if unclustered > 0:
            report.append(f"**Unclustered (NaN values):** {unclustered}\n")
        else:
            report.append("")
        
        # Cluster centers
        report.append("## Cluster Centers")
        report.append("\n**K-Means Centroids:**\n")
        center_data = []
        for i in range(n_clusters):
            center_data.append({
                "Cluster": i,
                f"{target_column} (Center)": f"{kmeans.cluster_centers_[i][0]:.3f}"
            })
        center_df = pd.DataFrame(center_data)
        report.append(center_df.to_markdown(index=False))
        
        # Overall distribution
        report.append("\n## Cluster Distribution")
        cluster_counts = result_df[result_df['cluster'] != -1]['cluster'].value_counts().sort_index()
        
        report.append("\n**Cluster Sizes:**\n")
        dist_data = []
        for cluster_id in range(n_clusters):
            count = cluster_counts.get(cluster_id, 0)
            pct = (count / len(data)) * 100
            
            # Visual bar
            bar_length = int(pct / 5)  # Scale down for display
            bar = "█" * bar_length
            
            dist_data.append({
                "Cluster": cluster_id,
                "Size": count,
                "Percentage": f"{pct:.1f}%",
                "Distribution": bar
            })
        
        dist_df = pd.DataFrame(dist_data)
        report.append(dist_df.to_markdown(index=False))
        
        # Detailed cluster information
        report.append("\n## Detailed Cluster Analysis")
        
        for cluster_id in range(n_clusters):
            cluster_data = result_df[result_df['cluster'] == cluster_id]
            cluster_size = len(cluster_data)
            
            report.append(f"\n### Cluster {cluster_id}")
            report.append(f"**Size:** {cluster_size} items ({(cluster_size / len(data) * 100):.1f}% of total)")
            
            # Statistics for this cluster
            cluster_values = cluster_data[target_column].dropna()
            if len(cluster_values) > 0:
                report.append(f"\n**{target_column} Statistics:**")
                report.append(f"- Mean: {cluster_values.mean():.3f}")
                report.append(f"- Median: {cluster_values.median():.3f}")
                report.append(f"- Std Dev: {cluster_values.std():.3f}")
                report.append(f"- Min: {cluster_values.min():.3f}")
                report.append(f"- Max: {cluster_values.max():.3f}")
                report.append(f"- Range: {cluster_values.max() - cluster_values.min():.3f}")
            
            # Show sample data (first 5 rows)
            if cluster_size > 0:
                report.append("\n**Sample Data:**")
                # Select relevant columns for display (exclude internal columns)
                sample_cols = [col for col in result_df.columns if not col.startswith("__") and col != 'cluster'][:6]
                sample_cols.append('cluster')
                report.append(cluster_data[sample_cols].head(5).to_markdown(index=False))
        
        # Insights
        report.append("\n## Key Insights")
        
        # Calculate cluster separation
        cluster_means = [result_df[result_df['cluster'] == i][target_column].mean() for i in range(n_clusters)]
        cluster_stds = [result_df[result_df['cluster'] == i][target_column].std() for i in range(n_clusters)]
        
        # Find well-separated clusters
        mean_range = max(cluster_means) - min(cluster_means)
        avg_std = np.mean(cluster_stds)
        
        report.append("\n**Cluster Quality:**\n")
        
        if mean_range > 3 * avg_std:
            report.append("- ✅ **Well-Separated Clusters**: Clusters are clearly distinct from each other")
        elif mean_range > avg_std:
            report.append("- 🟡 **Moderate Separation**: Clusters have some overlap")
        else:
            report.append("- ⚠️ **Poor Separation**: Clusters are not well-separated. Consider reducing the number of clusters.")
        
        # Check for imbalanced clusters
        max_size = max(cluster_counts.values)
        min_size = min(cluster_counts.values)
        
        if max_size > 3 * min_size:
            report.append("- ⚠️ **Imbalanced Clusters**: Some clusters are much larger than others")
        else:
            report.append("- ✅ **Balanced Clusters**: Cluster sizes are relatively even")
        
        # Identify extreme clusters
        sorted_means = sorted(enumerate(cluster_means), key=lambda x: x[1])
        lowest_cluster = sorted_means[0][0]
        highest_cluster = sorted_means[-1][0]
        
        report.append(f"\n**Cluster Characteristics:**")
        report.append(f"- **Lowest {target_column}**: Cluster {lowest_cluster} (mean: {cluster_means[lowest_cluster]:.3f})")
        report.append(f"- **Highest {target_column}**: Cluster {highest_cluster} (mean: {cluster_means[highest_cluster]:.3f})")
        
        report.append("\n## Data Updated")
        report.append(f"\n✅ Added 'cluster' column to dataset '{table_name}'")
        report.append(f"- Cluster IDs range from 0 to {n_clusters - 1}")
        report.append(f"- Use the cluster column to filter, group, or visualize your data")
        
        return result_df, kmeans, "\n".join(report)

    loop = asyncio.get_running_loop()
    try:
        result = await loop.run_in_executor(None, _cluster)
        
        if result[0] is None:
            return result[2]  # Error message
        
        result_df, kmeans, report = result
        
        # Update dataset
        success = await dm.update_dataset(table_name, result_df, user_id)
        
        if not success:
            return f"Error: Failed to update dataset '{table_name}' with clustering results."
        
        return report
        
    except Exception as e:
        return f"Error performing clustering: {str(e)}"

@tool
async def tfidf_tool(table_name: str, text_column: str, user_id: str, max_features: int = 10) -> str:
    """
    Computes TF-IDF (Term Frequency-Inverse Document Frequency) analysis for a text column.
    Identifies the most important terms/keywords based on their frequency and uniqueness.
    Returns a comprehensive report with top terms, scores, and vocabulary statistics.
    """
    dm = DataManager.get_instance("default")
    df = await dm.get_dataset(table_name, user_id)
    if df is None or df.empty:
        return f"Error: Dataset '{table_name}' not found."
        
    if text_column not in df.columns:
        available_cols = ", ".join(df.columns[:10].tolist())
        return f"Error: Column '{text_column}' not found. Available columns: {available_cols}"

    def _tfidf():
        # Clean and prepare texts
        texts = df[text_column].dropna().astype(str).tolist()
        
        if len(texts) == 0:
            return "Error: No valid text data found in column."
        
        # Configure TF-IDF vectorizer
        vectorizer = TfidfVectorizer(
            max_features=max_features * 3,  # Extract more features for analysis
            min_df=2,  # Must appear in at least 2 documents
            max_df=0.8,  # Ignore terms in more than 80% of docs
            ngram_range=(1, 2),  # Include single words and 2-word phrases
            stop_words='english'
        )
        
        try:
            tfidf_matrix = vectorizer.fit_transform(texts)
            feature_names = vectorizer.get_feature_names_out()
            
            # Calculate average TF-IDF scores across all documents
            avg_scores = tfidf_matrix.mean(axis=0).A1
            top_indices = avg_scores.argsort()[-max_features:][::-1]
            
            # Build comprehensive report
            report = []
            report.append(f"# TF-IDF Analysis Report: '{table_name}'")
            report.append(f"\n**Text Column:** {text_column}")
            report.append(f"**Total Documents:** {len(texts)}")
            report.append(f"**Vocabulary Size:** {len(feature_names)} unique terms")
            report.append(f"**N-gram Range:** 1-2 (single words and 2-word phrases)\n")
            
            # Top terms section
            report.append(f"## Top {max_features} Most Important Terms")
            report.append("\n**TF-IDF Rankings:**\n")
            
            # Create table data
            term_data = []
            for rank, idx in enumerate(top_indices, 1):
                term = feature_names[idx]
                score = avg_scores[idx]
                
                # Add visual indicator
                if score > 0.3:
                    indicator = "🔥"
                elif score > 0.2:
                    indicator = "⭐"
                elif score > 0.1:
                    indicator = "✓"
                else:
                    indicator = "·"
                
                term_data.append({
                    "Rank": rank,
                    "": indicator,
                    "Term": term,
                    "TF-IDF Score": f"{score:.4f}"
                })
            
            # Convert to markdown table
            import pandas as pd
            term_df = pd.DataFrame(term_data)
            report.append(term_df.to_markdown(index=False))
            
            # Key insights
            report.append("\n## Key Insights")
            report.append("\n**Term Analysis:**\n")
            
            top_term = feature_names[top_indices[0]]
            top_score = avg_scores[top_indices[0]]
            
            report.append(f"- 🎯 **Most Important Term**: '{top_term}' (score: {top_score:.4f})")
            
            # Check for phrases vs single words
            phrases = [feature_names[i] for i in top_indices if ' ' in feature_names[i]]
            if phrases:
                report.append(f"- 💬 **Top Phrases Found**: {len(phrases)} multi-word terms in top {max_features}")
                report.append(f"  - Examples: {', '.join(phrases[:3])}")
            
            # Vocabulary coverage
            coverage_pct = (len(feature_names) / len(texts)) * 100 if len(texts) > 0 else 0
            report.append(f"- 📊 **Vocabulary Density**: {coverage_pct:.1f} unique terms per document on average")
            
            report.append("\n## About TF-IDF")
            report.append("\nTF-IDF measures how important a term is to a document in a collection:")
            report.append("- **High scores**: Terms that appear frequently in specific documents (important keywords)")
            report.append("- **Low scores**: Common terms that appear everywhere (less distinctive)")
            report.append("- **Filtered out**: Very rare terms (< 2 docs) and very common terms (> 80% of docs)")
            
            return "\n".join(report)
            
        except Exception as e:
            return f"Error computing TF-IDF: {str(e)}"

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _tfidf)

@tool
async def describe_tool(table_name: str, user_id: str) -> str:
    """
    Returns descriptive statistics and metadata for a dataset.
    Uses cached metadata (field descriptions, column stats, sample data) instead of raw data.
    """
    dm = DataManager.get_instance("default")
    metadata = await dm.get_metadata(table_name, user_id)
    if not metadata:
        return f"Error: Dataset '{table_name}' not found."
        
    # Format the output
    output = [f"Dataset: {metadata.get('table_name')}"]
    output.append(f"Description: {metadata.get('description')}")
    output.append(f"Rows: {metadata.get('row_count')}")
    
    # Field Metadata
    if metadata.get('field_metadata'):
        output.append("\n## Fields:")
        for field in metadata['field_metadata']:
            output.append(f"- {field.get('column_name')} ({field.get('data_type')}): {field.get('description')}")
            
    # Column Stats
    if metadata.get('column_stats'):
        output.append("\n## Statistics:")
        try:
            stats_df = pd.DataFrame.from_dict(metadata['column_stats'], orient='index')
            output.append(stats_df.to_markdown())
        except Exception:
            output.append(str(metadata['column_stats']))

    # Sample Data
    if metadata.get('sample_data'):
        output.append("\n## Sample Data (First 5 rows):")
        try:
            sample_df = pd.DataFrame(metadata['sample_data'])
            output.append(sample_df.to_markdown(index=False))
        except Exception:
            output.append(str(metadata['sample_data']))
            
    return "\n".join(output)
