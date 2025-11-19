"""Gap Analysis Agent - Identifies product gaps and unmet needs"""

import json
from app.core.llm.simple_workflow.tools.semantic_search_tool import semantic_search_from_query, semantic_search_from_sql
from app.core.llm.simple_workflow.tools.user_dataset_tool import get_available_datasets_in_context, get_dataset_data_from_sql, get_user_datasets

from llama_index.core.agent.workflow import FunctionAgent
from llama_index.core.tools import FunctionTool
from llama_index.core.workflow import Context
from llama_index.llms.openai import OpenAI

from app.core.llm.simple_workflow.tools.gap_analysis_tool import detect_gaps_from_clusters


def create_gap_analysis_agent(llm: OpenAI, user_id: str) -> FunctionAgent:
    """
    Create the gap analysis agent for identifying product gaps from clustered data.
    
    Args:
        llm: OpenAI LLM instance
        user_id: User ID to pre-bind to all tools
        
    Returns:
        FunctionAgent configured as gap analysis specialist
    """
    
    detect_gaps_from_clusters_tool = FunctionTool.from_defaults(fn=detect_gaps_from_clusters)
    # get_available_datasets_in_context_tool = FunctionTool.from_defaults(fn=get_available_datasets_in_context)
    
    return FunctionAgent(
        name="gap_analysis",
        description="Identifies product gaps. BRIEF responses only.",
        system_prompt="""You are a gap analysis specialist. Identify gaps, BE BRIEF.

ANALYZE:
- Underrepresented clusters
- Outlier patterns
- Missing themes
- Feature requests

BREVITY RULES:
- Keep findings under 100 words total
- Use bullet points only
- NO lengthy explanations
- NEVER mention routing, agents, or internal workflow
- Example output: "3 key gaps found: [gap1], [gap2], [gap3]" """,
        tools=[detect_gaps_from_clusters_tool],
        llm=llm,
    )


async def create_gap_analysis_agent_with_datasets(llm: OpenAI, user_id: str) -> FunctionAgent:
    """
    Create the gap analysis agent for identifying product gaps from clustered data.
    
    Args:
        llm: OpenAI LLM instance
        user_id: User ID to pre-bind to all tools
        
    Returns:
        FunctionAgent configured as gap analysis specialist
    """
    # Fetch user datasets
    datasets = await get_user_datasets(user_id=user_id, limit=50, offset=0)
    detect_gaps_from_clusters_tool = FunctionTool.from_defaults(fn=detect_gaps_from_clusters)
    semantic_search_from_sql_tool = FunctionTool.from_defaults(fn=semantic_search_from_sql)
    semantic_search_from_query_tool = FunctionTool.from_defaults(fn=semantic_search_from_query)
    get_available_datasets_in_context_tool = FunctionTool.from_defaults(fn=get_available_datasets_in_context)
    get_dataset_data_from_sql_tool = FunctionTool.from_defaults(fn=get_dataset_data_from_sql)

    return FunctionAgent(
        name="gap_analysis",
        description="Identifies product gaps and hands off to report_writer",
        system_prompt=f"""You are a gap analysis specialist. Identify gaps, then HAND OFF to report_writer.

{json.dumps(datasets, indent=2)}

CRITICAL RULES:
1. You MUST call at least one tool before providing analysis
2. NEVER write the final answer yourself
3. After analysis, ALWAYS hand off to "report_writer" with your findings
4. Generate visualizations when possible - gap analysis benefits from charts

WORKFLOW:
1. Call get_dataset_data_from_sql to fetch data
2. Call detect_gaps_from_clusters_tool to analyze (may generate visualizations)
3. Collect findings (gaps, patterns, feature requests)
4. Extract visualization paths from tool results if any
5. Hand off to "report_writer" with ALL findings and visualization paths (if any)

VISUALIZATION HANDLING:
- If tool generates charts, extract paths from response
- Look for graph paths (e.g., /Users/.../graphs/filename.png)
- Include visualization filenames in handoff message
- If no visualizations generated, don't mention them in handoff

CRITICAL SQL RULES:
- ALWAYS use SELECT * in queries - NEVER filter columns
- Filtering columns breaks downstream analysis tools
- Example: SELECT * FROM table_name WHERE condition LIMIT 100

HANDOFF FORMAT (KEEP IT SHORT):
Pass to report_writer with BRIEF message like:
"Gap analysis done. 3 key gaps: [gap1], [gap2], [gap3]. Top cluster underrepresented by 40%. Visualizations: [filenames]. Format report."

CRITICAL HANDOFF RULES:
- Keep handoff message under 80 words MAX
- Only top 3-5 insights
- NO lengthy explanations, NO detailed data
- The report_writer will expand everything
- If no visualizations, omit that line entirely

NEVER mention routing, agents, or internal workflow to the end user.""",
        tools=[detect_gaps_from_clusters_tool, semantic_search_from_sql_tool, semantic_search_from_query_tool, get_available_datasets_in_context_tool, get_dataset_data_from_sql_tool],
        llm=llm,
    )
