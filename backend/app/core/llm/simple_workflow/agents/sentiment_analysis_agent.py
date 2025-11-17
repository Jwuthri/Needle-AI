"""Sentiment Analysis Agent - Analyzes sentiment patterns"""

from typing import Any, Dict, List, Optional

from app.core.llm.simple_workflow.tools.sentiment_analysis_tool import analyze_sentiment
from app.core.llm.simple_workflow.tools.user_dataset_tool import get_available_datasets_in_context
from app.core.llm.simple_workflow.tools.forfeit_tool import forfeit_request
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
    forfeit_tool = FunctionTool.from_defaults(fn=forfeit_request)
    # get_available_datasets_in_context_tool = FunctionTool.from_defaults(fn=get_available_datasets_in_context)

    return FunctionAgent(
        name="sentiment_analysis",
        description="Analyzes sentiment. BRIEF responses only.",
        system_prompt="""You are a sentiment specialist. Analyze sentiment, BE BRIEF.

ANALYZE:
- Overall distribution
- Sentiment by source
- Key themes

FORFEIT WHEN:
- No sentiment data available
- Data lacks required text fields
- Analysis tools repeatedly fail
Call forfeit_request with clear reason.

BREVITY RULES:
- Keep findings under 80 words
- Use bullet points only
- NO lengthy explanations
- NEVER mention routing, agents, or internal workflow
- Example: "Sentiment: 60% positive, 30% neutral, 10% negative" """,
        # tools=[analyze_sentiment_tool, get_review_stats_tool, query_user_reviews_tool],
        tools=[analyze_sentiment_tool, forfeit_tool],
        llm=llm,
    )
