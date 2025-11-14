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
            async with ctx.store.edit_state() as ctx_state:
                ctx_state["state"]["list_of_user_datasets"] = datasets
            
            return datasets
        except Exception as e:
            logger.error(f"Error getting user datasets: {e}", exc_info=True)
            return {"error": str(e)}


async def get_dataset_data_from_sql(ctx: Context, sql_query: str, dataset_name: str) -> pd.DataFrame:
    """Get dataset data from a SQL query.

    Args:
        ctx: Context
        sql_query: SQL query to execute
        dataset_name: Name of the dataset to search on

    Returns:
        pd.DataFrame: Dataset data as markdown table
    """
    async with get_async_session() as db:
        try:
            data = await UserDatasetService(db).get_dataset_data_from_sql(sql_query)
            async with ctx.store.edit_state() as ctx_state:
                ctx_state["state"]["dataset_data"]["sql_search"][dataset_name] = data

            return data.head(10).to_markdown()
        except Exception as e:
            logger.error(f"Error getting dataset data: {e}", exc_info=True)
            return {"error": str(e)}


async def get_available_datasets_in_context(ctx: Context) -> list[str]:
    """Get all the available dataset data names available in the context.

    Args:
        ctx: Context

    Returns:
        list[str]: List of datasets names
    """
    async with ctx.store.get_state() as ctx_state:
        try:
            return list(ctx_state["state"]["dataset_data"].keys())
        except Exception as e:
            logger.error(f"Error getting datasets in context: {e}", exc_info=True)
            return {"error": str(e)}
