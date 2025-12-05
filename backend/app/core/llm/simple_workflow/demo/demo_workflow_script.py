"""
🎯 Demo Workflow Script
=======================

This script demonstrates the complete workflow:
1. Initialize workflow context
2. Fetch a dataset using SQL
3. Perform semantic search on another dataset
4. Display what's in the context
5. Apply clustering analysis on one of the datasets

Run this script to see the full workflow in action!
"""

import asyncio
import json
from typing import Any, Dict

import pandas as pd
from llama_index.core.workflow import Context, Workflow, StartEvent, StopEvent, step

from app.core.llm.simple_workflow.tools.user_dataset_tool import (
    get_user_datasets,
    get_dataset_data_from_sql,
)
from app.core.llm.simple_workflow.tools.semantic_search_tool import (
    semantic_search_from_query,
)
from app.core.llm.simple_workflow.tools.clustering_analysis_tool import (
    cuterize_dataset,
)
from app.utils.logging import get_logger, setup_logging

setup_logging(log_level="INFO", environment="development")
logger = get_logger(__name__)


class DemoWorkflow(Workflow):
    """Demo workflow showcasing dataset operations and clustering."""

    @step
    async def start(self, ctx: Context, ev: StartEvent) -> StopEvent:
        """Execute the complete demo workflow."""
        
        logger.info("\n" + "="*60)
        logger.info("🚀 Starting Demo Workflow")
        logger.info("="*60 + "\n")
        
        # Extract parameters from event
        state = await ctx.store.get("state", {})
        user_id = "user_33gDeY7n9vlwAzkUBRgdS1Yy4lS"

        # Step 1: Initialize context state
        logger.info("📦 Step 1: Initializing workflow context...")
        async with ctx.store.edit_state() as ctx_state:
            ctx_state["state"] = {
                "user_id": user_id,
                "dataset_data": {
                    "sql_search": {},
                    "semantic_search": {},
                    "clustering": {},
                },
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
        
        dataset_name = "__user_user_33gdey7n9vlwazkubrgds1yy4ls_customer_profiles"
        # Step 3: Fetch dataset using SQL
        logger.info(f"🔍 Step 3: Fetching '{dataset_name}' dataset using SQL query...")
        sql_query = f"""
            SELECT 
                *
            FROM {dataset_name}
            LIMIT 100;
        """
        sql_result = await get_dataset_data_from_sql(ctx, sql_query, dataset_name)
        ctx_state = await ctx.store.get("state", {})
        
        if isinstance(sql_result, dict) and "error" in sql_result:
            logger.info(f"❌ Error fetching SQL data: {sql_result['error']}\n")
        else:
            logger.info(f"✅ Successfully fetched data from SQL!")
            logger.info(f"   Preview (first 10 rows):\n")
            logger.info(sql_result)
            logger.info("")
        
        search_query = "Custom API Rate Limits"
        # Step 4: Perform semantic search
        logger.info(f"🔎 Step 4: Performing semantic search on '{dataset_name}'...")
        logger.info(f"   Query: '{search_query}'")
        
        search_result = await semantic_search_from_query(
            ctx, 
            query=search_query,
            dataset_name=f"{dataset_name}",
            top_n=20
        )
        if isinstance(search_result, dict) and "error" in search_result:
            logger.info(f"❌ Error in semantic search: {search_result['error']}\n")
        else:
            logger.info(f"✅ Semantic search completed!")
            logger.info(f"   Results (top 10):\n")
            logger.info(search_result)
            logger.info("")
        
        # Step 5: Display context contents
        logger.info("📋 Step 5: Displaying current context state...")
        ctx_state = await ctx.store.get("state", {})
        
        logger.info(f"   🔑 User ID: {ctx_state.get('user_id')}")
        logger.info(f"   📊 Datasets in context:")
        
        dataset_data = ctx_state.get("dataset_data", {})
        for data_type, datasets_dict in dataset_data.items():
            if isinstance(datasets_dict, dict) and datasets_dict:
                logger.info(f"      • {data_type}: {list(datasets_dict.keys())}")
                for ds_name, df in datasets_dict.items():
                    if isinstance(df, pd.DataFrame):
                        logger.info(f"        - {ds_name}: {len(df)} rows, {len(df.columns)} columns")
        logger.info("")
        
        # Step 6: Apply clustering analysis
        logger.info(f"🎨 Step 6: Applying clustering analysis on '{dataset_name}'...")
        logger.info("   Using UMAP + HDBSCAN for optimal clustering...")
        
        clustering_result = await cuterize_dataset(
            ctx,
            dataset_name=f"{dataset_name}",
            min_cluster_size=3
        )
        
        if clustering_result.startswith("Error"):
            logger.info(f"❌ {clustering_result}\n")
        else:
            logger.info("✅ Clustering completed successfully!")
            logger.info("\n" + "-"*60)
            logger.info(clustering_result)
            logger.info("-"*60 + "\n")
        
        # Final summary
        logger.info("="*60)
        logger.info("🎉 Demo Workflow Completed Successfully!")
        logger.info("="*60)
        
        # Get final context state
        final_state = await ctx.store.get("state", {})
        
        summary = {
            "status": "success",
            "datasets_users": len(datasets),
            "clustered_datasets": list[Any](final_state.get("dataset_data", {}).get("clustering", {}).keys()),
        }
        
        logger.info("\n📊 Summary:")
        logger.info(f"   • User Datasets: {summary['datasets_users']}")
        logger.info(f"   • Clustered datasets: {summary['clustered_datasets']}")
        logger.info("")
        
        return StopEvent(result=summary)


async def run_demo(
    user_id: str,
) -> Dict[str, Any]:
    """
    Run the demo workflow.
    
    Args:
        user_id: User ID to fetch datasets for
        dataset_name: Name of the dataset to analyze (default: "reviews")
        search_query: Query for semantic search (default: "customer service issues")
    
    Returns:
        Dict containing workflow results
    
    Example:
        >>> result = await run_demo(
        ...     user_id="user_123",
        ...     dataset_name="reviews",
        ...     search_query="product quality feedback"
        ... )
    """
    workflow = DemoWorkflow(timeout=300)
    ctx = Context(workflow)
    
    result = await workflow.run(
        user_msg="perform clustering analysis on the dataset",
        initial_state={"user_id": user_id},
        ctx=ctx
    )
    
    return result


if __name__ == "__main__":
    # Example usage
    logger.info("\n" + "🌟"*30)
    logger.info("   Demo Workflow Script - Example Usage")
    logger.info("🌟"*30 + "\n")

    asyncio.run(run_demo(user_id="user_33gDeY7n9vlwAzkUBRgdS1Yy4lS"))
    
    