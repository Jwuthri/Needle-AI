"""Clustering Agent - Groups similar reviews"""

import json
from typing import Any, Dict, Optional

from app.core.llm.simple_workflow.tools.clustering_analysis_tool import cuterize_dataset
from app.core.llm.simple_workflow.tools.semantic_search_tool import semantic_search_from_query, semantic_search_from_sql
from app.core.llm.simple_workflow.tools.user_dataset_tool import get_available_datasets_in_context, get_dataset_data_from_sql, get_user_datasets
from llama_index.core.agent.workflow import FunctionAgent
from llama_index.core.tools import FunctionTool
from llama_index.llms.openai import OpenAI

from app.core.llm.workflow.tools import review_analysis_tools


def create_clustering_agent(llm: OpenAI, user_id: str) -> FunctionAgent:
    """
    Create the clustering agent for grouping similar reviews.
    
    Args:
        llm: OpenAI LLM instance
        user_id: User ID to pre-bind to all tools
        
    Returns:
        FunctionAgent configured as clustering specialist
    """

    cuterize_dataset_tool = FunctionTool.from_defaults(fn=cuterize_dataset)
    semantic_search_from_sql_tool = FunctionTool.from_defaults(fn=semantic_search_from_sql)
    semantic_search_from_query_tool = FunctionTool.from_defaults(fn=semantic_search_from_query)
    get_available_datasets_in_context_tool = FunctionTool.from_defaults(fn=get_available_datasets_in_context)

    return FunctionAgent(
        name="clustering",
        description="Groups similar reviews. BRIEF responses only.",
        system_prompt="""You are a clustering specialist. Group reviews, BE BRIEF.

ANALYZE:
- Group similar reviews
- Identify themes
- Extract key patterns

BREVITY RULES:
- Keep findings under 80 words
- Use bullet points only
- NO lengthy explanations
- NEVER mention routing, agents, or internal workflow
- Example: "5 clusters found: [theme1], [theme2], [theme3]..." """,
        tools=[cuterize_dataset_tool, get_available_datasets_in_context_tool, semantic_search_from_sql_tool, semantic_search_from_query_tool],
        llm=llm,
    )


async def create_clustering_agent_with_datasets(llm: OpenAI, user_id: str) -> FunctionAgent:
    """
    Create the data discovery agent with datasets pre-loaded in the prompt.
    
    Args:
        llm: OpenAI LLM instance
        user_id: User ID to pre-bind to all tools
        ctx: Workflow context to fetch datasets
        
    Returns:
        FunctionAgent configured as data discovery specialist with datasets in prompt
    """
    # Fetch user datasets
    datasets = await get_user_datasets(user_id=user_id, limit=50, offset=0)
    
    cuterize_dataset_tool = FunctionTool.from_defaults(fn=cuterize_dataset)
    semantic_search_from_sql_tool = FunctionTool.from_defaults(fn=semantic_search_from_sql)
    semantic_search_from_query_tool = FunctionTool.from_defaults(fn=semantic_search_from_query)
    get_available_datasets_in_context_tool = FunctionTool.from_defaults(fn=get_available_datasets_in_context)
    get_dataset_data_from_sql_tool = FunctionTool.from_defaults(fn=get_dataset_data_from_sql)

    return FunctionAgent(
        name="clustering",
        description="Groups similar reviews, creates visualizations, then hands off to report_writer",
        system_prompt=f"""You are a clustering specialist. Group reviews, create visualizations, then HAND OFF to report_writer.

{json.dumps(datasets, indent=2)}

CRITICAL RULES:
1. You MUST call at least one tool before providing analysis
2. NEVER write the final answer yourself
3. After analysis, hand off to "visualization" to create charts
4. After visualization completes, hand off to "report_writer" with findings

WORKFLOW:
1. Call get_dataset_data_from_sql to fetch data
2. Call cuterize_dataset tool to cluster
3. Collect findings (clusters, themes, patterns)
4. Hand off to "visualization" with:
   - Cluster distribution data (cluster names and sizes)
   - Request for bar chart showing cluster sizes
   - Request for pie chart showing cluster distribution
5. After visualization completes, hand off to "report_writer" with ALL findings and viz paths

CRITICAL SQL RULES:
- ALWAYS use SELECT * in queries - NEVER filter columns
- Filtering columns breaks downstream analysis tools
- Example: SELECT * FROM table_name WHERE condition LIMIT 100

VISUALIZATION HANDOFF FORMAT:
When handing off to visualization, provide:
"Create cluster visualizations: 5 clusters - UI Issues (35%), Performance (25%), Features (20%), Pricing (12%), Support (8%). Create bar chart showing cluster sizes."

REPORT WRITER HANDOFF FORMAT (KEEP IT SHORT):
After visualizations are done, pass to report_writer with BRIEF message like:
"Clustering done. 5 clusters: UI Issues, Performance, Features, Pricing, Support. Largest cluster 35%. Visualizations created. Format report."

CRITICAL HANDOFF RULES:
- Keep handoff messages under 80 words MAX
- Only cluster names and key stat
- NO detailed breakdowns, NO examples
- The report_writer will expand everything

NEVER mention routing, agents, or internal workflow to the end user.""",
        tools=[cuterize_dataset_tool, get_available_datasets_in_context_tool, semantic_search_from_sql_tool, semantic_search_from_query_tool, get_dataset_data_from_sql_tool],
        llm=llm,
    )
