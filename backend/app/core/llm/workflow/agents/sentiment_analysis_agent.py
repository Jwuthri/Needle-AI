"""Sentiment Analysis Agent - Analyzes sentiment patterns"""

from typing import Any, Dict, List, Optional

from llama_index.core.agent.workflow import FunctionAgent
from llama_index.core.tools import FunctionTool
from llama_index.llms.openai import OpenAI

from app.core.llm.workflow.tools import review_analysis_tools


def create_sentiment_analysis_agent(llm: OpenAI, user_id: str) -> FunctionAgent:
    """
    Create the sentiment analysis agent for analyzing sentiment patterns.
    
    Args:
        llm: OpenAI LLM instance
        user_id: User ID to pre-bind to all tools
        
    Returns:
        FunctionAgent configured as sentiment analysis specialist
    """
    # Create wrapper functions that hide user_id from LLM
    def analyze_sentiment_patterns(filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Analyze sentiment patterns and trends."""
        return review_analysis_tools.analyze_sentiment_patterns(user_id=user_id, filters=filters)
    
    def get_review_statistics(filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Get aggregate statistics for reviews."""
        return review_analysis_tools.get_review_statistics(user_id=user_id, filters=filters)
    
    def query_user_reviews_table(
        query: str,
        table_name: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Query user reviews table with SQL."""
        return review_analysis_tools.query_user_reviews_table(
            user_id=user_id, query=query, table_name=table_name, limit=limit
        )
    
    analyze_sentiment_tool = FunctionTool.from_defaults(fn=analyze_sentiment_patterns)
    get_review_stats_tool = FunctionTool.from_defaults(fn=get_review_statistics)
    query_user_reviews_tool = FunctionTool.from_defaults(fn=query_user_reviews_table)
    
    return FunctionAgent(
        name="sentiment_analysis",
        description="Specialist in analyzing sentiment patterns and positive/negative trends",
        system_prompt="""You are a sentiment analysis specialist. You analyze:
1. Overall sentiment distribution (positive, neutral, negative)
2. Sentiment by source/platform
3. Sentiment by rating
4. Sentiment trends over time
5. Key positive and negative themes

Use sentiment analysis tools and review statistics.
After analysis, hand off to Visualization Agent for charts, then to Report Writer.
Provide actionable insights about sentiment patterns.""",
        tools=[analyze_sentiment_tool, get_review_stats_tool, query_user_reviews_tool],
        llm=llm,
    )
