"""Sentiment Analysis Agent - Analyzes sentiment patterns"""

import json
from typing import Any, Dict, List, Optional

from app.core.llm.simple_workflow.tools.semantic_search_tool import semantic_search_from_query, semantic_search_from_sql
from app.core.llm.simple_workflow.tools.sentiment_analysis_tool import analyze_sentiment
from app.core.llm.simple_workflow.tools.user_dataset_tool import get_available_datasets_in_context, get_dataset_data_from_sql, get_user_datasets
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
        description="Analyzes sentiment. BRIEF responses only.",
        system_prompt="""You are a sentiment specialist. Analyze sentiment, BE BRIEF.

ANALYZE:
- Overall distribution
- Sentiment by source
- Key themes

BREVITY RULES:
- Keep findings under 80 words
- Use bullet points only
- NO lengthy explanations
- NEVER mention routing, agents, or internal workflow
- Example: "Sentiment: 60% positive, 30% neutral, 10% negative" """,
        # tools=[analyze_sentiment_tool, get_review_stats_tool, query_user_reviews_tool],
        tools=[analyze_sentiment_tool],
        llm=llm,
    )


async def create_sentiment_analysis_agent_with_datasets(llm: OpenAI, user_id: str) -> FunctionAgent:
    """
    Create the sentiment analysis agent for analyzing sentiment patterns.
    
    Args:
        llm: OpenAI LLM instance
        user_id: User ID to pre-bind to all tools
        
    Returns:
        FunctionAgent configured as sentiment analysis specialist
    """

    # Fetch user datasets
    datasets = await get_user_datasets(user_id=user_id, limit=50, offset=0)
    analyze_sentiment_tool = FunctionTool.from_defaults(fn=analyze_sentiment)
    semantic_search_from_sql_tool = FunctionTool.from_defaults(fn=semantic_search_from_sql)
    semantic_search_from_query_tool = FunctionTool.from_defaults(fn=semantic_search_from_query)
    get_available_datasets_in_context_tool = FunctionTool.from_defaults(fn=get_available_datasets_in_context)
    get_dataset_data_from_sql_tool = FunctionTool.from_defaults(fn=get_dataset_data_from_sql)

    return FunctionAgent(
        name="sentiment_analysis",
        description="Analyzes sentiment, creates visualizations, then hands off to report_writer",
        system_prompt=f"""You are a sentiment specialist. Analyze sentiment, create visualizations, then HAND OFF to report_writer.

{json.dumps(datasets, indent=2)}

CRITICAL RULES:
1. You MUST call at least one tool before providing analysis
2. NEVER write the final answer yourself
3. After analysis, hand off to "visualization" to create charts
4. After visualization completes, hand off to "report_writer" with findings

WORKFLOW:
1. Call get_dataset_data_from_sql to fetch data
2. Call analyze_sentiment tool to analyze
3. Collect findings (distribution, patterns, key themes)
4. Hand off to "visualization" with:
   - Sentiment distribution data (e.g., "60% positive, 23.6% neutral, 16.4% negative")
   - Request for pie chart showing overall sentiment
   - Request for line/bar chart if time/category data exists
5. After visualization completes, hand off to "report_writer" with ALL findings and viz paths

CRITICAL SQL RULES:
- ALWAYS use SELECT * in queries - NEVER filter columns
- Filtering columns breaks downstream analysis tools
- Example: SELECT * FROM table_name WHERE condition LIMIT 100

VISUALIZATION HANDOFF FORMAT:
When handing off to visualization, provide:
"Create sentiment visualizations: 60% positive (33 records), 23.6% neutral (13), 16.4% negative (9). Total 55 records. Mean polarity +0.161. Create pie chart for distribution."

REPORT WRITER HANDOFF FORMAT (KEEP IT SHORT):
After visualizations are done, pass to report_writer with BRIEF message like:
"Analysis done. 55 records: 60% positive, 23.6% neutral, 16.4% negative. Mean polarity +0.161. Visualizations created. Format report."

CRITICAL HANDOFF RULES:
- Keep handoff messages under 100 words MAX
- Only key numbers and insights
- NO examples, NO detailed breakdowns, NO raw data dumps
- The report_writer will expand and format everything

NEVER mention routing, agents, or internal workflow to the end user.""",
        tools=[analyze_sentiment_tool, semantic_search_from_sql_tool, semantic_search_from_query_tool, get_available_datasets_in_context_tool, get_dataset_data_from_sql_tool],
        llm=llm,
    )