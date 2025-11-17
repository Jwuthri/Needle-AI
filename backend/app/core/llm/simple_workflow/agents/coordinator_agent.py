"""Coordinator Agent - Routes queries to appropriate specialists"""

from app.core.llm.simple_workflow.tools.user_dataset_tool import get_user_datasets
from app.core.llm.simple_workflow.tools.utils_tool import get_current_time, get_user_location
from app.core.llm.simple_workflow.tools.forfeit_tool import forfeit_request

from llama_index.core.agent.workflow import FunctionAgent
from llama_index.core.tools import FunctionTool
from llama_index.core.workflow import Context
from llama_index.llms.openai import OpenAI


def create_coordinator_agent(llm: OpenAI, user_id: str) -> FunctionAgent:
    """
    Create the coordinator agent that routes queries to appropriate specialists.
    
    Args:
        llm: OpenAI LLM instance
        user_id: User ID to pre-bind to all tools
        
    Returns:
        FunctionAgent configured as coordinator
    """

    async def _get_user_datasets(ctx: Context, limit: int = 50, offset: int = 0) -> list[dict]:
        """Get all the user's datasets information.

        Args:
            ctx: Context
            limit: Maximum number of datasets to return
            offset: Offset for pagination
        """
        return await get_user_datasets(ctx=ctx, user_id=user_id, limit=limit, offset=offset)

    get_current_time_tool = FunctionTool.from_defaults(fn=get_current_time)
    get_user_location_tool = FunctionTool.from_defaults(fn=get_user_location)
    get_user_datasets_tool = FunctionTool.from_defaults(fn=_get_user_datasets)
    forfeit_tool = FunctionTool.from_defaults(fn=forfeit_request)
    
    return FunctionAgent(
        name="coordinator",
        description="Routes queries to appropriate specialist. Keeps responses SHORT.",
        system_prompt="""You are a coordinator. Work efficiently and BE BRIEF.

HANDLING RULES:
- Time/greetings → Answer directly
- Follow-ups referencing previous answers → Answer directly (1-2 sentences max)
- New data questions → Delegate to specialists

CONVERSATION HISTORY:
- Check if question references previous context
- If answer is in history, respond directly in 1-2 sentences
- Only delegate if NEW data analysis needed

FORFEIT WHEN STUCK:
- If specialists repeatedly fail or return errors
- If the question is clearly outside capabilities
- Call forfeit_request with clear reason and what was attempted
- Be honest and helpful about limitations

BREVITY RULES:
- Keep ALL responses under 50 words
- NO lengthy explanations
- NEVER mention routing, agents, or internal workflow
- NO "I'll help you with..." preambles
- Work silently and efficiently""",
        tools=[get_current_time_tool, get_user_location_tool, get_user_datasets_tool, forfeit_tool],
        llm=llm,
    )
