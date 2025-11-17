from app.database.session import get_async_session
from app.services.user_dataset_service import UserDatasetService
from app.utils.logging import get_logger

import pandas as pd
from llama_index.core.workflow import Context

logger = get_logger(__name__)


async def get_user_datasets(ctx: Context, user_id: str, limit: int = 50, offset: int = 0) -> list[dict]:
    """Get all the user's datasets information.

    Args:
        ctx: Context
        user_id: User ID
        limit: Maximum number of datasets to return
        offset: Offset for pagination

    Returns:
        list[dict]: List of datasets information
    """
    async with get_async_session() as db:
        try:
            datasets = await UserDatasetService(db).list_datasets(user_id, limit, offset)
            
            # Store as dict with dataset names as keys for easy lookup
            datasets_dict = {ds.get("table_name"): ds for ds in datasets if ds.get("table_name")}
            
            async with ctx.store.edit_state() as ctx_state:
                if "state" not in ctx_state:
                    ctx_state["state"] = {}
                ctx_state["state"]["list_of_user_datasets"] = datasets_dict
            
            return datasets
        except Exception as e:
            logger.error(f"Error getting user datasets: {e}", exc_info=True)
            return {"error": str(e)}


async def get_dataset_data_from_sql(ctx: Context, sql_query: str, dataset_name: str) -> str:
    """Get dataset data from a SQL query.

    Args:
        ctx: Context
        sql_query: SQL query to execute
        dataset_name: Name of the dataset to search on

    Returns:
        str: Dataset data as markdown table or error message for LLM to fix
    """
    # Track SQL error retries to prevent infinite loops
    ctx_state = await ctx.store.get_state()
    sql_error_count = ctx_state.get("sql_error_count", 0)
    
    if sql_error_count >= 5:
        return f"ERROR: Too many SQL query errors ({sql_error_count}). Please check the dataset schema using get_user_datasets tool first, then try a simpler query."
    
    async with get_async_session() as db:
        try:    
            data = await UserDatasetService(db).get_dataset_data_from_sql(sql_query)
            
            # Reset error count on success
            async with ctx.store.edit_state() as ctx_state:
                if "state" not in ctx_state:
                    ctx_state["state"] = {}
                if "dataset_data" not in ctx_state["state"]:
                    ctx_state["state"]["dataset_data"] = {}
                ctx_state["state"]["dataset_data"][dataset_name] = data
                ctx_state["sql_error_count"] = 0  # Reset on success
                
            ddata = data.copy()
            if "__embedding__" in ddata.columns:
                ddata.drop(columns=["__embedding__"], inplace=True)
            return ddata.head(10).to_markdown()
        except Exception as e:
            logger.error(f"Error getting dataset data: {e}", exc_info=True)
            
            # Increment error count
            async with ctx.store.edit_state() as ctx_state:
                ctx_state["sql_error_count"] = sql_error_count + 1
            
            # Return error message to LLM so it can fix the query
            error_msg = str(e)
            return f"ERROR executing SQL query (attempt {sql_error_count + 1}/5):\n{error_msg}\n\nPlease analyze the error and generate a corrected SQL query. Consider using get_user_datasets to check the available columns first."


async def get_available_datasets_in_context(ctx: Context) -> list[str]:
    """Get all the available dataset data names available in the context.

    Args:
        ctx: Context

    Returns:
        list[str]: List of datasets names
    """
    try:
        ctx_state = await ctx.store.get_state()
        return list(ctx_state.get("state", {}).get("dataset_data", {}).keys())
    except Exception as e:
        logger.error(f"Error getting datasets in context: {e}", exc_info=True)
        return {"error": str(e)}

    # async with ctx.store.get_state() as ctx_state:
    #     try:
    #         return list(ctx_state["state"]["dataset_data"].keys())
    #     except Exception as e:
    #         logger.error(f"Error getting datasets in context: {e}", exc_info=True)
    #         return {"error": str(e)}