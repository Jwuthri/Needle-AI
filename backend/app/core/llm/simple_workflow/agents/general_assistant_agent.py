"""General Assistant Agent - Handles non-data queries"""

from llama_index.core.agent.workflow import FunctionAgent
from llama_index.core.tools import FunctionTool
from llama_index.llms.openai import OpenAI

from app.core.llm.workflow.tools import review_analysis_tools


def create_general_assistant_agent(llm: OpenAI, user_id: str) -> FunctionAgent:
    """
    Create the general assistant agent for non-data queries.
    
    Args:
        llm: OpenAI LLM instance
        user_id: User ID to pre-bind to all tools (not used by this agent's tools)
        
    Returns:
        FunctionAgent configured as general assistant
    """
    get_current_time_tool = FunctionTool.from_defaults(fn=review_analysis_tools.get_current_time)
    format_date_tool = FunctionTool.from_defaults(fn=review_analysis_tools.format_date)
    
    return FunctionAgent(
        name="general_assistant",
        description="Handles general questions. BRIEF responses only.",
        system_prompt="""You are a general assistant. Answer questions, BE BRIEF.

HANDLE:
- Time/date queries
- General questions
- Greetings

BREVITY RULES:
- Keep ALL responses under 30 words
- NO lengthy explanations
- Answer directly, NO handoffs needed
- Example: "It's 3:45 PM on Monday, Nov 17, 2025" """,
        tools=[get_current_time_tool, format_date_tool],
        llm=llm,
    )

