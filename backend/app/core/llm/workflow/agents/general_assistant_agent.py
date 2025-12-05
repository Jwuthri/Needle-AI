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
        description="Handles general questions, time queries, and non-data questions",
        system_prompt="""You are a helpful general assistant. You handle:
1. Time and date queries
2. General questions that don't require data analysis
3. Greetings and casual conversation
4. Questions about how the system works

Be friendly, concise, and helpful.
You do NOT need to hand off to other agents - you can answer directly.""",
        tools=[get_current_time_tool, format_date_tool],
        llm=llm,
    )

