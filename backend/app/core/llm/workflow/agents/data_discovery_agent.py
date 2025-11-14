"""Data Discovery Agent - Discovers datasets and determines data sources"""

from typing import Any, Dict, List

from llama_index.core.agent.workflow import FunctionAgent
from llama_index.core.tools import FunctionTool
from llama_index.llms.openai import OpenAI

from app.core.llm.workflow.tools import review_analysis_tools


def create_data_discovery_agent(llm: OpenAI, user_id: str) -> FunctionAgent:
    """
    Create the data discovery agent that finds and analyzes available datasets.
    
    Args:
        llm: OpenAI LLM instance
        user_id: User ID to pre-bind to all tools
        
    Returns:
        FunctionAgent configured as data discovery specialist
    """
    # Create wrapper functions that hide user_id from LLM
    def get_user_datasets() -> Dict[str, Any]:
        """List all user datasets with metadata."""
        return review_analysis_tools.get_user_datasets(user_id=user_id)
    
    def get_table_eda(table_name: str) -> Dict[str, Any]:
        """Get EDA metadata for a table."""
        return review_analysis_tools.get_table_eda(user_id=user_id, table_name=table_name)
    
    def query_user_reviews_table(
        query: str,
        table_name: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Query user reviews table with SQL."""
        return review_analysis_tools.query_user_reviews_table(
            user_id=user_id, query=query, table_name=table_name, limit=limit
        )
    
    get_user_datasets_tool = FunctionTool.from_defaults(fn=get_user_datasets)
    get_table_eda_tool = FunctionTool.from_defaults(fn=get_table_eda)
    query_user_reviews_tool = FunctionTool.from_defaults(fn=query_user_reviews_table)
    
    return FunctionAgent(
        name="data_discovery",
        description="Discovers available datasets, retrieves EDA metadata, determines optimal data sources",
        system_prompt="""You are a data discovery specialist. Your role is to:
1. Discover all available datasets for the user
2. Analyze EDA metadata to understand data structure
3. Determine which datasets and tables are relevant for the query
4. Route to appropriate analysis agents:
   - Gap Analysis Agent: for product gaps, unmet needs, feature requests
   - Sentiment Analysis Agent: for sentiment patterns, positive/negative trends
   - Trend Analysis Agent: for temporal trends, patterns over time
   - Clustering Agent: for grouping similar reviews, identifying themes

IMPORTANT: When calling tools that require user_id, get it from workflow context/initial_state.
Always check available datasets first, then analyze EDA metadata to understand the data structure.
Based on the query, determine which analysis agents should be involved.""",
        tools=[get_user_datasets_tool, get_table_eda_tool, query_user_reviews_tool],
        llm=llm,
    )

