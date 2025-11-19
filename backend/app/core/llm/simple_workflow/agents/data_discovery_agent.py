"""Data Discovery Agent - Discovers datasets and determines data sources"""
import asyncio
import json
from app.core.llm.simple_workflow.tools.semantic_search_tool import semantic_search_from_query, semantic_search_from_sql
from app.core.llm.simple_workflow.tools.user_dataset_tool import get_available_datasets_in_context, get_dataset_data_from_sql, get_user_datasets
from llama_index.core.agent.workflow import FunctionAgent
from llama_index.core.tools import FunctionTool
from llama_index.core.workflow import Context
from llama_index.llms.openai import OpenAI


async def create_data_discovery_agent_with_datasets(llm: OpenAI, user_id: str) -> FunctionAgent:
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
    
    semantic_search_from_sql_tool = FunctionTool.from_defaults(fn=semantic_search_from_sql)
    semantic_search_from_query_tool = FunctionTool.from_defaults(fn=semantic_search_from_query)
    get_dataset_data_from_sql_tool = FunctionTool.from_defaults(fn=get_dataset_data_from_sql)
    
    system_prompt = f"""You are a data discovery specialist. Load data, then route to specialists. BE BRIEF.

{json.dumps(datasets, indent=2)}

WORKFLOW:
1. Review the available datasets above - you already have this information
2. Load required data using semantic_search_from_sql or get_dataset_data_from_sql
3. Once data is loaded, hand off to appropriate specialist:
   - Sentiment questions (with or without viz requests) → "sentiment_analysis"
   - Trend questions (with or without viz requests) → "trend_analysis"
   - Gap/missing features → "gap_analysis"
   - Grouping/clustering → "clustering"
   - General analysis → "report_writer"

CRITICAL ROUTING RULES:
- NEVER route directly to "visualization" agent
- Analysis agents (sentiment/trend/gap/clustering) handle their own visualizations
- If user asks for "sentiment graph", route to "sentiment_analysis" (not visualization)
- If user asks for "trend chart", route to "trend_analysis" (not visualization)

CRITICAL SQL RULES:
- ALWAYS use SELECT * in queries - NEVER filter columns
- Filtering columns breaks downstream analysis tools
- Example: SELECT * FROM table_name WHERE condition LIMIT 100
- Use the table_name field (shown above) in SQL queries, NOT the dataset name
- Check columns to ensure required data exists before loading
- ALWAYS load data before handing off to specialists
- If no datasets available, explain to user they need to upload data first

BREVITY RULES:
- NO explanations of what you're doing
- Work silently in the background
- NEVER mention routing, agents, or internal workflow
- If you must respond, keep it under 20 words"""
    
    return FunctionAgent(
        name="data_discovery",
        description="Loads datasets and routes to analysis agents. BRIEF responses only.",
        system_prompt=system_prompt,
        tools=[semantic_search_from_sql_tool, semantic_search_from_query_tool, get_dataset_data_from_sql_tool],
        llm=llm,
    )


def create_data_discovery_agent(llm: OpenAI, user_id: str) -> FunctionAgent:
    """
    Create the data discovery agent (synchronous version for backward compatibility).
    
    Note: This version requires the agent to call get_user_datasets tool.
    For better performance, use create_data_discovery_agent_with_datasets instead.
    
    Args:
        llm: OpenAI LLM instance
        user_id: User ID to pre-bind to all tools
        
    Returns:
        FunctionAgent configured as data discovery specialist
    """

    async def _get_user_datasets(ctx: Context, limit: int = 50, offset: int = 0) -> list[dict]:
        """Get all the user's datasets information/metadata

        Args:
            ctx: Context
            limit: Maximum number of datasets to return
            offset: Offset for pagination

        Returns:
            list[dict]: List of datasets information
        """
        return await get_user_datasets(ctx=ctx, user_id=user_id, limit=limit, offset=offset)
    
    get_user_datasets_tool = FunctionTool.from_defaults(fn=_get_user_datasets)
    semantic_search_from_sql_tool = FunctionTool.from_defaults(fn=semantic_search_from_sql)
    semantic_search_from_query_tool = FunctionTool.from_defaults(fn=semantic_search_from_query)
    get_dataset_data_from_sql_tool = FunctionTool.from_defaults(fn=get_dataset_data_from_sql)
    
    return FunctionAgent(
        name="data_discovery",
        description="Loads datasets and routes to analysis agents. BRIEF responses only.",
        system_prompt="""You are a data discovery specialist. Load data, then route to specialists. BE BRIEF.

WORKFLOW:
1. FIRST call get_user_datasets to see available datasets - this returns:
   - name: Dataset name
   - table_name: Database table name (use THIS in SQL queries!)
   - columns: Available columns with types
   - row_count: Number of rows
2. Load required data using semantic_search_from_sql or get_dataset_data_from_sql
3. Once data is loaded, hand off to appropriate specialist:
   - Sentiment questions (with or without viz requests) → "sentiment_analysis"
   - Trend questions (with or without viz requests) → "trend_analysis"
   - Gap/missing features → "gap_analysis"
   - Grouping/clustering → "clustering"
   - General analysis → "report_writer"

CRITICAL ROUTING RULES:
- NEVER route directly to "visualization" agent
- Analysis agents (sentiment/trend/gap/clustering) handle their own visualizations
- If user asks for "sentiment graph", route to "sentiment_analysis" (not visualization)
- If user asks for "trend chart", route to "trend_analysis" (not visualization)

CRITICAL SQL RULES:
- ALWAYS use SELECT * in queries - NEVER filter columns
- Filtering columns breaks downstream analysis tools
- Example: SELECT * FROM table_name WHERE condition LIMIT 100
- ALWAYS call get_user_datasets FIRST to see what's available
- Use the table_name field (not name) in SQL queries
- Check columns to ensure required data exists
- ALWAYS load data before handing off to specialists
- If no datasets, tell user to upload data first

BREVITY RULES:
- NO explanations of what you're doing
- Work silently in the background
- NEVER mention routing, agents, or internal workflow
- If you must respond, keep it under 20 words""",
        tools=[get_user_datasets_tool, semantic_search_from_sql_tool, semantic_search_from_query_tool, get_dataset_data_from_sql_tool],
        llm=llm,
    )
