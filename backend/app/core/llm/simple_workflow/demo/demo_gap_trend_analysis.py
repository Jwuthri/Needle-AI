"""
🎯 Demo Script for Gap & Trend Analysis Tools
===============================================

This script demonstrates the new gap analysis and trend analysis tools:
1. Load a dataset
2. Perform clustering (if needed)
3. Run gap analysis to identify underrepresented clusters and outliers
4. Run trend analysis to detect temporal patterns

Run this script to see the new tools in action!
"""

import asyncio
from typing import Any, Dict

from llama_index.core.workflow import Context, Workflow, StartEvent, StopEvent, step

from app.core.llm.simple_workflow.tools.user_dataset_tool import (
    get_user_datasets,
    get_dataset_data_from_sql,
)
from app.core.llm.simple_workflow.tools.gap_analysis_tool import detect_gaps_from_clusters
from app.core.llm.simple_workflow.tools.trend_analysis_tool import analyze_temporal_trends
from app.utils.logging import get_logger, setup_logging

setup_logging(log_level="INFO", environment="development")
logger = get_logger(__name__)


class GapTrendDemoWorkflow(Workflow):
    """Demo workflow showcasing gap analysis and trend analysis tools."""

    @step
    async def start(self, ctx: Context, ev: StartEvent) -> StopEvent:
        """Execute the complete demo workflow."""
        
        logger.info("\n" + "="*60)
        logger.info("🚀 Starting Gap & Trend Analysis Demo")
        logger.info("="*60 + "\n")
        
        user_id = "user_33gDeY7n9vlwAzkUBRgdS1Yy4lS"

        # Step 1: Initialize context state
        logger.info("📦 Step 1: Initializing workflow context...")
        async with ctx.store.edit_state() as ctx_state:
            ctx_state["state"] = {
                "user_id": user_id,
                "dataset_data": {},
                "list_of_user_datasets": {},
            }
        logger.info("✅ Context initialized successfully!\n")
        
        # Step 2: Get list of available datasets
        logger.info("📊 Step 2: Fetching available datasets...")
        datasets = await get_user_datasets(ctx, user_id, limit=10)
        datasets_dict = {ds.get("table_name"): ds for ds in datasets if ds.get("table_name")}

        async with ctx.store.edit_state() as ctx_state:
            ctx_state["state"]["list_of_user_datasets"] = datasets_dict
        
        if isinstance(datasets, dict) and "error" in datasets:
            logger.info(f"❌ Error fetching datasets: {datasets['error']}\n")
            return StopEvent(result={"error": datasets["error"]})
        
        logger.info(f"✅ Found {len(datasets)} datasets!")
        for i, ds in enumerate(datasets, 1):
            logger.info(f"   {i}. 📁 {ds.get('table_name', 'Unknown')} ({ds.get('row_count', 0)} rows)")
        logger.info("")
        
        # Step 3: Load dataset
        dataset_name = "__user_user_33gdey7n9vlwazkubrgds1yy4ls_customer_profiles"
        logger.info(f"🔍 Step 3: Loading dataset '{dataset_name}'...")
        
        sql_query = f"""
            SELECT 
                *
            FROM {dataset_name}
            LIMIT 100;
        """
        sql_result = await get_dataset_data_from_sql(ctx, sql_query, dataset_name)
        if isinstance(sql_result, dict) and "error" in sql_result:
            logger.info(f"❌ Error loading dataset: {sql_result['error']}\n")
            return StopEvent(result={"error": sql_result["error"]})
        
        logger.info(f"✅ Dataset loaded successfully!")
        logger.info(f"   Preview:\n{sql_result}\n")
        
        # Step 4: Run gap analysis (will trigger clustering if needed)
        logger.info("🔎 Step 4: Running Gap Analysis...")
        logger.info("   This will automatically perform clustering if not done yet...")
        
        gap_result = await detect_gaps_from_clusters(
            ctx,
            dataset_name=dataset_name,
            min_cluster_size=3
        )
        
        if gap_result.startswith("Error"):
            logger.info(f"❌ {gap_result}\n")
        else:
            logger.info("✅ Gap analysis completed!")
            logger.info("\n" + "-"*60)
            logger.info(gap_result)
            logger.info("-"*60 + "\n")
        
        # Step 5: Run trend analysis (if dataset has time column)
        logger.info("📈 Step 5: Running Trend Analysis...")
        
        # Check if dataset has time columns
        ctx_state = await ctx.store.get("state", {})
        dataset_metadata = ctx_state.get("list_of_user_datasets", {}).get(dataset_name, {})
        field_metadata = dataset_metadata.get("field_metadata", {})
        
        # Find time columns (handle both dict and list formats)
        time_columns = []
        if isinstance(field_metadata, dict):
            time_columns = [
                field for field, meta in field_metadata.items()
                if isinstance(meta, dict) and meta.get("type") in ["date", "datetime", "timestamp"]
            ]
        elif isinstance(field_metadata, list):
            time_columns = [
                field.get("name") for field in field_metadata
                if isinstance(field, dict) and field.get("type") in ["date", "datetime", "timestamp"]
            ]
        
        time_columns = ["subscription_date"]
        if time_columns:
            time_column = time_columns[0]
            logger.info(f"   Found time column: {time_column}")
            
            trend_result = await analyze_temporal_trends(
                ctx,
                dataset_name=dataset_name,
                time_column=time_column,
                value_columns=None,  # Auto-detect
                aggregation="mean",
                time_grouping="auto"
            )
            
            if trend_result.startswith("Error"):
                logger.info(f"❌ {trend_result}\n")
            else:
                logger.info("✅ Trend analysis completed!")
                logger.info("\n" + "-"*60)
                logger.info(trend_result)
                logger.info("-"*60 + "\n")
        else:
            logger.info("⚠️ No time columns found in dataset. Skipping trend analysis.\n")
        
        # Final summary
        logger.info("="*60)
        logger.info("🎉 Gap & Trend Analysis Demo Completed!")
        logger.info("="*60)
        
        final_state = await ctx.store.get("state", {})
        
        summary = {
            "status": "success",
            "dataset_analyzed": dataset_name,
            "gap_analysis_performed": "gap_analysis" in final_state,
            "trend_analysis_performed": "trend_analysis" in final_state,
        }
        
        logger.info("\n📊 Summary:")
        logger.info(f"   • Dataset: {summary['dataset_analyzed']}")
        logger.info(f"   • Gap Analysis: {'✓' if summary['gap_analysis_performed'] else '✗'}")
        logger.info(f"   • Trend Analysis: {'✓' if summary['trend_analysis_performed'] else '✗'}")
        logger.info("")
        
        return StopEvent(result=summary)


async def run_demo(user_id: str) -> Dict[str, Any]:
    """
    Run the gap & trend analysis demo workflow.
    
    Args:
        user_id: User ID to fetch datasets for
    
    Returns:
        Dict containing workflow results
    """
    workflow = GapTrendDemoWorkflow(timeout=300)
    ctx = Context(workflow)
    
    result = await workflow.run(
        user_msg="perform gap and trend analysis",
        initial_state={"user_id": user_id},
        ctx=ctx
    )
    
    return result


if __name__ == "__main__":
    logger.info("\n" + "🌟"*30)
    logger.info("   Gap & Trend Analysis Demo - Example Usage")
    logger.info("🌟"*30 + "\n")

    asyncio.run(run_demo(user_id="user_33gDeY7n9vlwAzkUBRgdS1Yy4lS"))

