"""Data Discovery Agent - Discovers datasets and determines data sources"""
from app.core.llm.simple_workflow.tools.semantic_search_tool import semantic_search_from_query, semantic_search_from_sql
from app.core.llm.simple_workflow.tools.user_dataset_tool import get_available_datasets_in_context, get_dataset_data_from_sql, get_user_datasets
from llama_index.core.agent.workflow import FunctionAgent
from llama_index.core.tools import FunctionTool
from llama_index.core.workflow import Context
from llama_index.llms.openai import OpenAI


def create_data_discovery_agent(llm: OpenAI, user_id: str) -> FunctionAgent:
    """
    Create the data discovery agent that finds and analyzes available datasets.
    
    Args:
        llm: OpenAI LLM instance
        user_id: User ID to pre-bind to all tools
        
    Returns:
        FunctionAgent configured as data discovery specialist
    """

    async def _get_user_datasets(ctx: Context, limit: int = 50, offset: int = 0) -> list[dict]:
        """Get all the user's datasets information/metadata

        Args:
            ctx: Context
            limit: Maximum number of datasets to return
            offset: Offset for pagination

        Returns:
            list[dict]: List of datasets information
        """
        return await get_user_datasets(ctx=ctx, user_id=user_id, limit=limit, offset=offset)
    
    get_user_datasets_tool = FunctionTool.from_defaults(fn=_get_user_datasets)
    semantic_search_from_sql_tool = FunctionTool.from_defaults(fn=semantic_search_from_sql)
    semantic_search_from_query_tool = FunctionTool.from_defaults(fn=semantic_search_from_query)
    get_dataset_data_from_sql_tool = FunctionTool.from_defaults(fn=get_dataset_data_from_sql)
    # get_available_datasets_in_context_tool = FunctionTool.from_defaults(fn=get_available_datasets_in_context)
    
    return FunctionAgent(
        name="data_discovery",
        description="Discovers available datasets, retrieves EDA metadata, determines optimal data sources",
        system_prompt="""You are a data discovery specialist. Your role is to:
1. Discover all available datasets for the user that include EDA metadata
2. Load the relevant dataset data into context using get_dataset_data_from_sql
3. Determine which datasets and tables are relevant for the query
4. Route to appropriate analysis agents AFTER loading data:
   - Gap Analysis Agent: for product gaps, unmet needs, feature requests (after data is loaded)
   - Sentiment Analysis Agent: for sentiment patterns, positive/negative trends (after data is loaded)
   - Trend Analysis Agent: for temporal trends, patterns over time (after data is loaded)
   - Clustering Agent: for grouping similar reviews, identifying themes (after data is loaded)

CRITICAL WORKFLOW:
1. First, call get_user_datasets to see available datasets
2. Then, call get_dataset_data_from_sql to load the relevant dataset data into context
3. Only AFTER data is loaded, hand off to the appropriate specialist agent

The specialist agents (gap_analysis, sentiment_analysis, etc.) CANNOT load data themselves.
YOU must load data BEFORE routing to them.

DEFAULT DATASET BEHAVIOR:
If you're uncertain which dataset to use or if no specific dataset is mentioned in the query,
default to the 'reviews' dataset as it's the core dataset of the application. The reviews dataset
contains product reviews which are the primary data source for most analyses (gaps, sentiment,
trends, clustering, etc.).

Example workflow for "What are my product gaps?":
1. get_user_datasets() -> find 'reviews' dataset (or default to it if uncertain)
2. get_dataset_data_from_sql(sql_query="SELECT * FROM reviews", dataset_name="reviews") -> load data
3. Handoff to gap_analysis agent

Always check available datasets first, then load data, then route to specialists.""",
        tools=[get_user_datasets_tool, semantic_search_from_sql_tool, semantic_search_from_query_tool, get_dataset_data_from_sql_tool],
        llm=llm,
    )
