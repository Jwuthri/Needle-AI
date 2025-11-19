from app.database.session import get_async_session
from app.services.user_dataset_service import UserDatasetService
from app.utils.logging import get_logger

import pandas as pd
from llama_index.core.workflow import Context

logger = get_logger(__name__)


async def semantic_search_from_sql(ctx: Context, sql_query: str, query: str, dataset_name: str) -> pd.DataFrame:
    """Perform semantic search on a dataset.

    CRITICAL: ALWAYS use SELECT * in your queries - NEVER filter columns.
    Filtering columns will break downstream analysis tools.

    Args:
        ctx: Context
        sql_query: SQL query to execute (use table_name from get_user_datasets)
        query: Semantic search query text
        dataset_name: Name of the dataset to search on (use table_name from get_user_datasets)

    Example:
    ```
    # First get user datasets to find the table_name
    datasets = await get_user_datasets(ctx)
    table_name = datasets[0]["table_name"]  # e.g., "__user_123_customer_reviews"
    
    semantic_search_from_sql(
        sql_query=f'''
            SELECT
                *,
                1 - (__embedding__ <=> '[PLACEHOLDER_QUERY_VECTOR]'::vector) AS __similarity_score__
            FROM {table_name}
            ORDER BY __similarity_score__ DESC
            LIMIT 100;
        ''',
        query="customer service issues",
        dataset_name=table_name,
    )
    ```

    Returns:
        pd.DataFrame: DataFrame with search results
    """
    async with get_async_session() as db:
        try:
            data = await UserDatasetService(db).get_dataset_data_from_semantic_search_from_sql(sql_query, query)
            async with ctx.store.edit_state() as ctx_state:
                if "state" not in ctx_state:
                    ctx_state["state"] = {}
                if "dataset_data" not in ctx_state["state"]:
                    ctx_state["state"]["dataset_data"] = {}
                ctx_state["state"]["dataset_data"][dataset_name] = data
            ddata = data.copy()
            if "__embedding__" in ddata.columns:
                ddata.drop(columns=["__embedding__"], inplace=True)
            return ddata.head(10).to_markdown()
        except Exception as e:
            logger.error(f"Error getting dataset data: {e}", exc_info=True)
            return {"error": str(e)}


async def semantic_search_from_query(ctx: Context, query: str, dataset_name: str, top_n: int = -1) -> pd.DataFrame:
    """Perform semantic search on a dataset.

    Args:
        ctx: Context
        query: semantic search query
        dataset_name: Name of the dataset to search on (use table_name from get_user_datasets)
        top_n: Maximum number of results (-1 for all)

    Example:
    ```
    # First get user datasets to find the table_name
    datasets = await get_user_datasets(ctx)
    table_name = datasets[0]["table_name"]  # e.g., "__user_123_customer_reviews"
    
    semantic_search_from_query(
        query="customer service issues",
        dataset_name=table_name,
        top_n=10
    )
    ```

    Returns:
        pd.DataFrame: DataFrame with search results
    """
    async with get_async_session() as db:
        try:
            data = await UserDatasetService(db).get_dataset_data_from_semantic_search(query, dataset_name, top_n)
            async with ctx.store.edit_state() as ctx_state:
                if "state" not in ctx_state:
                    ctx_state["state"] = {}
                if "dataset_data" not in ctx_state["state"]:
                    ctx_state["state"]["dataset_data"] = {}
                ctx_state["state"]["dataset_data"][dataset_name] = data
            ddata = data.copy()
            if "__embedding__" in ddata.columns:
                ddata.drop(columns=["__embedding__"], inplace=True)
            return ddata.head(10).to_markdown()
        except Exception as e:
            logger.error(f"Error getting dataset data: {e}", exc_info=True)
            return {"error": str(e)}