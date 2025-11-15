"""Trend Analysis Agent - Detects temporal trends"""

from typing import List, Optional

from app.core.llm.simple_workflow.tools.user_dataset_tool import get_available_datasets_in_context
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
    # get_available_datasets_in_context_tool = FunctionTool.from_defaults(fn=get_available_datasets_in_context)

    return FunctionAgent(
        name="trend_analysis",
        description="Specialist in detecting temporal trends and patterns over time using Python/pandas",
        system_prompt="""You are a trend analysis specialist. You analyze time-series data to detect:
1. Temporal trends (increasing, decreasing, stable)
2. Patterns over time (daily, weekly, monthly, quarterly, yearly)
3. Seasonal variations and cyclical patterns
4. Growth rates and velocity
5. Volatility and anomalies

Your tool uses Python/pandas for robust statistical analysis. You need to:
- Identify the time/date column in the dataset
- Specify which numeric columns to analyze (or let it auto-detect)
- Choose appropriate time grouping (auto, day, week, month, quarter, year)
- Select aggregation method (mean, sum, count, median)

Key insights to provide:
- What is the overall trend direction?
- Are there significant changes or inflection points?
- Is the data volatile or stable?
- What patterns emerge over different time periods?

After analysis, you can hand off to Visualization Agent for line charts showing trends.
Provide actionable insights about what trends mean for the business.""",
        tools=[analyze_trends_tool],
        llm=llm,
    )
