"""Sentiment Analysis Agent - Analyzes sentiment patterns"""

from typing import Any, Dict, List, Optional

from app.core.llm.simple_workflow.tools.sentiment_analysis_tool import analyze_sentiment
from app.core.llm.simple_workflow.tools.user_dataset_tool import get_available_datasets_in_context
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

    analyze_sentiment_tool = FunctionTool.from_defaults(fn=analyze_sentiment)
    # get_available_datasets_in_context_tool = FunctionTool.from_defaults(fn=get_available_datasets_in_context)

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
        # tools=[analyze_sentiment_tool, get_review_stats_tool, query_user_reviews_tool],
        tools=[analyze_sentiment_tool],
        llm=llm,
    )
