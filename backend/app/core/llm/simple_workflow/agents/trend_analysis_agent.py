"""Trend Analysis Agent - Detects temporal trends"""

from typing import List, Optional

from app.core.llm.simple_workflow.tools.user_dataset_tool import get_available_datasets_in_context
from app.core.llm.simple_workflow.tools.forfeit_tool import forfeit_request
from llama_index.core.agent.workflow import FunctionAgent
from llama_index.core.tools import FunctionTool
from llama_index.core.workflow import Context
from llama_index.llms.openai import OpenAI

from app.core.llm.simple_workflow.tools.trend_analysis_tool import analyze_temporal_trends


def create_trend_analysis_agent(llm: OpenAI, user_id: str) -> FunctionAgent:
    """
    Create the trend analysis agent for detecting temporal trends using Python/pandas.
    
    Args:
        llm: OpenAI LLM instance
        user_id: User ID to pre-bind to all tools
        
    Returns:
        FunctionAgent configured as trend analysis specialist
    """
    
    analyze_trends_tool = FunctionTool.from_defaults(fn=analyze_temporal_trends)
    forfeit_tool = FunctionTool.from_defaults(fn=forfeit_request)
    # get_available_datasets_in_context_tool = FunctionTool.from_defaults(fn=get_available_datasets_in_context)

    return FunctionAgent(
        name="trend_analysis",
        description="Detects trends. BRIEF responses only.",
        system_prompt="""You are a trend specialist. Detect trends, BE BRIEF.

ANALYZE:
- Trend direction (up/down/stable)
- Key inflection points
- Volatility

FORFEIT WHEN:
- No temporal/date data available
- Insufficient data points for trend analysis
- Data format incompatible with time series
Call forfeit_request with clear reason.

BREVITY RULES:
- Keep findings under 80 words
- Use bullet points only
- NO lengthy explanations
- NEVER mention routing, agents, or internal workflow
- Example: "Trend: increasing 15% monthly, stable volatility" """,
        tools=[analyze_trends_tool, forfeit_tool],
        llm=llm,
    )
