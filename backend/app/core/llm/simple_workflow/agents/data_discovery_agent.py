"""Data Discovery Agent - Discovers datasets and determines data sources"""
from app.core.llm.simple_workflow.tools.semantic_search_tool import semantic_search_from_query, semantic_search_from_sql
from app.core.llm.simple_workflow.tools.user_dataset_tool import get_available_datasets_in_context, get_dataset_data_from_sql, get_user_datasets
from app.core.llm.simple_workflow.tools.forfeit_tool import forfeit_request
from llama_index.core.agent.workflow import FunctionAgent
from llama_index.core.tools import FunctionTool
from llama_index.core.workflow import Context
from llama_index.llms.openai import OpenAI


def create_data_discovery_agent(llm: OpenAI, user_id: str) -> FunctionAgent:
    """
    Create the data discovery agent that finds and analyzes available datasets.
    
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
    forfeit_tool = FunctionTool.from_defaults(fn=forfeit_request)
    # get_available_datasets_in_context_tool = FunctionTool.from_defaults(fn=get_available_datasets_in_context)
    
    return FunctionAgent(
        name="data_discovery",
        description="Loads datasets and routes to analysis agents. BRIEF responses only.",
        system_prompt="""You are a data discovery specialist. Load data, BE BRIEF.

WORKFLOW:
1. ALWAYS start by calling get_user_datasets to see available datasets
2. Check context - is data already loaded?
3. If YES → Proceed with analysis
4. If NO → Load data using the dataset table_name from get_user_datasets

IMPORTANT: You can ONLY access user datasets returned by get_user_datasets. 
The table_name field contains the actual database table name to use in SQL queries.

FORFEIT WHEN:
- No datasets available for the user
- Required data columns don't exist
- SQL queries repeatedly fail
- Data format is incompatible with analysis
Call forfeit_request with clear reason and attempted actions.

BREVITY RULES:
- NO explanations of what you're doing
- Work silently in the background
- NEVER mention routing, agents, or internal workflow
- If you must respond, keep it under 20 words""",
        tools=[get_user_datasets_tool, semantic_search_from_sql_tool, semantic_search_from_query_tool, get_dataset_data_from_sql_tool, forfeit_tool],
        llm=llm,
    )
