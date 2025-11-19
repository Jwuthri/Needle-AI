"""Trend Analysis Agent - Detects temporal trends"""

import json
from typing import List, Optional

from app.core.llm.simple_workflow.tools.semantic_search_tool import semantic_search_from_query, semantic_search_from_sql
from app.core.llm.simple_workflow.tools.user_dataset_tool import get_available_datasets_in_context, get_dataset_data_from_sql, get_user_datasets
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
        description="Detects trends. BRIEF responses only.",
        system_prompt="""You are a trend specialist. Detect trends, BE BRIEF.

ANALYZE:
- Trend direction (up/down/stable)
- Key inflection points
- Volatility

BREVITY RULES:
- Keep findings under 80 words
- Use bullet points only
- NO lengthy explanations
- NEVER mention routing, agents, or internal workflow
- Example: "Trend: increasing 15% monthly, stable volatility" """,
        tools=[analyze_trends_tool],
        llm=llm,
    )


async def create_trend_analysis_agent_with_datasets(llm: OpenAI, user_id: str) -> FunctionAgent:
    """
    Create the trend analysis agent for detecting temporal trends using Python/pandas.
    
    Args:
        llm: OpenAI LLM instance
        user_id: User ID to pre-bind to all tools
        
    Returns:
        FunctionAgent configured as trend analysis specialist
    """
    # Fetch user datasets
    datasets = await get_user_datasets(user_id=user_id, limit=50, offset=0)
    analyze_trends_tool = FunctionTool.from_defaults(fn=analyze_temporal_trends)
    semantic_search_from_sql_tool = FunctionTool.from_defaults(fn=semantic_search_from_sql)
    semantic_search_from_query_tool = FunctionTool.from_defaults(fn=semantic_search_from_query)
    get_available_datasets_in_context_tool = FunctionTool.from_defaults(fn=get_available_datasets_in_context)
    get_dataset_data_from_sql_tool = FunctionTool.from_defaults(fn=get_dataset_data_from_sql)

    return FunctionAgent(
        name="trend_analysis",
        description="Detects trends, creates visualizations, then hands off to report_writer",
        system_prompt=f"""You are a trend specialist. Detect trends, create visualizations, then HAND OFF to report_writer.

{json.dumps(datasets, indent=2)}

CRITICAL RULES:
1. You MUST call at least one tool before providing analysis
2. NEVER write the final answer yourself
3. After analysis, hand off to "visualization" to create charts
4. After visualization completes, hand off to "report_writer" with findings

WORKFLOW:
1. Call get_dataset_data_from_sql to fetch data
2. Call analyze_temporal_trends tool to analyze
3. Collect findings (trends, inflection points, volatility)
4. Hand off to "visualization" with:
   - Trend data over time (dates and values)
   - Request for line chart showing trend
   - Request for bar chart if categorical comparisons exist
5. After visualization completes, hand off to "report_writer" with ALL findings and viz paths

CRITICAL SQL RULES:
- ALWAYS use SELECT * in queries - NEVER filter columns
- Filtering columns breaks downstream analysis tools
- Example: SELECT * FROM table_name WHERE condition LIMIT 100

VISUALIZATION HANDOFF FORMAT:
When handing off to visualization, provide:
"Create trend visualizations: Sentiment increasing 15% monthly from Jan (0.10) to Dec (0.25). Create line chart showing trend over time."

REPORT WRITER HANDOFF FORMAT (KEEP IT SHORT):
After visualizations are done, pass to report_writer with BRIEF message like:
"Trend analysis done. Increasing 15% monthly. Peak in Q3. Volatility stable. Visualizations created. Format report."

CRITICAL HANDOFF RULES:
- Keep handoff messages under 80 words MAX
- Only direction, rate, key inflection point
- NO detailed data, NO lengthy explanations
- The report_writer will expand everything

NEVER mention routing, agents, or internal workflow to the end user.""",
        tools=[analyze_trends_tool, semantic_search_from_sql_tool, semantic_search_from_query_tool, get_available_datasets_in_context_tool, get_dataset_data_from_sql_tool],
        llm=llm,
    )
