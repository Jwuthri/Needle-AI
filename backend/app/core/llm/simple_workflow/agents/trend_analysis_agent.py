"""Trend Analysis Agent - Detects temporal trends"""

from typing import Any, Dict, List, Optional

from llama_index.core.agent.workflow import FunctionAgent
from llama_index.core.tools import FunctionTool
from llama_index.llms.openai import OpenAI

from app.core.llm.workflow.tools import review_analysis_tools


def create_trend_analysis_agent(llm: OpenAI, user_id: str) -> FunctionAgent:
    """
    Create the trend analysis agent for detecting temporal trends.
    
    Args:
        llm: OpenAI LLM instance
        user_id: User ID to pre-bind to all tools
        
    Returns:
        FunctionAgent configured as trend analysis specialist
    """
    # Create wrapper functions that hide user_id from LLM
    def detect_trends(time_field: str = "date", metric: str = "rating") -> Dict[str, Any]:
        """Detect temporal trends in reviews."""
        return review_analysis_tools.detect_trends(user_id=user_id, time_field=time_field, metric=metric)
    
    def query_user_reviews_table(
        query: str,
        table_name: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Query user reviews table with SQL."""
        return review_analysis_tools.query_user_reviews_table(
            user_id=user_id, query=query, table_name=table_name, limit=limit
        )
    
    def get_review_statistics(filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Get aggregate statistics for reviews."""
        return review_analysis_tools.get_review_statistics(user_id=user_id, filters=filters)
    
    detect_trends_tool = FunctionTool.from_defaults(fn=detect_trends)
    query_user_reviews_tool = FunctionTool.from_defaults(fn=query_user_reviews_table)
    get_review_stats_tool = FunctionTool.from_defaults(fn=get_review_statistics)
    
    return FunctionAgent(
        name="trend_analysis",
        description="Specialist in detecting temporal trends and patterns over time",
        system_prompt="""You are a trend analysis specialist. You detect:
1. Temporal trends in ratings, sentiment, or review volume
2. Patterns over time (daily, weekly, monthly)
3. Seasonal variations
4. Trend direction (improving, declining, stable)

Use trend detection tools and time-series analysis.
After analysis, hand off to Visualization Agent for line charts showing trends.
Provide insights about what trends mean for the product.""",
        tools=[detect_trends_tool, query_user_reviews_tool, get_review_stats_tool],
        llm=llm,
    )
