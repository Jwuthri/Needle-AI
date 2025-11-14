"""Data Discovery Agent - Discovers datasets and determines data sources"""
from app.core.llm.simple_workflow.tools.user_dataset_tool import get_user_datasets
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
    
    return FunctionAgent(
        name="data_discovery",
        description="Discovers available datasets, retrieves EDA metadata, determines optimal data sources",
        system_prompt="""You are a data discovery specialist. Your role is to:
1. Discover all available datasets for the user, that include an EDA metadata
2. Determine which datasets and tables are relevant for the query
3. Route to appropriate analysis agents:
   - Gap Analysis Agent: for product gaps, unmet needs, feature requests
   - Sentiment Analysis Agent: for sentiment patterns, positive/negative trends
   - Trend Analysis Agent: for temporal trends, patterns over time
   - Clustering Agent: for grouping similar reviews, identifying themes

IMPORTANT: When calling tools that require user_id, get it from workflow context/initial_state.
Always check available datasets first, then analyze EDA metadata to understand the data structure.
Based on the query, determine which analysis agents should be involved.""",
        tools=[get_user_datasets_tool],
        llm=llm,
    )
