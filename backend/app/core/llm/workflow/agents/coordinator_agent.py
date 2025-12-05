"""Coordinator Agent - Routes queries to appropriate specialists"""

from typing import Any, Dict

from llama_index.core.agent.workflow import FunctionAgent
from llama_index.core.tools import FunctionTool
from llama_index.llms.openai import OpenAI

from app.core.llm.workflow.tools import review_analysis_tools


def create_coordinator_agent(llm: OpenAI, user_id: str) -> FunctionAgent:
    """
    Create the coordinator agent that routes queries to appropriate specialists.
    
    Args:
        llm: OpenAI LLM instance
        user_id: User ID to pre-bind to all tools
        
    Returns:
        FunctionAgent configured as coordinator
    """
    # Create wrapper functions that hide user_id from LLM
    def get_user_datasets() -> Dict[str, Any]:
        """List all user datasets with metadata.
        
        Returns:
            Dict with datasets list and metadata
        """
        return review_analysis_tools.get_user_datasets(user_id=user_id)
    
    get_user_datasets_tool = FunctionTool.from_defaults(fn=get_user_datasets)
    get_current_time_tool = FunctionTool.from_defaults(fn=review_analysis_tools.get_current_time)
    
    return FunctionAgent(
        name="coordinator",
        description="First point of contact. Analyzes query intent and routes to appropriate specialist.",
        system_prompt="""You are an intelligent coordinator for product review analysis. Your role is to:
1. Analyze the user's query to understand their intent
2. Determine if the query requires data analysis or is a general question
3. Route to the appropriate specialist:
   - General Assistant: for simple questions (time, date, general info), greetings, non-data queries
   - Data Discovery Agent: for queries about product reviews, gaps, sentiment, trends, or any data analysis

IMPORTANT: Use your judgment to determine query type. Do NOT use rule-based text matching.
- If the query asks about time, date, or general knowledge → General Assistant
- If the query asks about reviews, gaps, sentiment, trends, or requires data → Data Discovery Agent

When handing off, explain which specialist will help them.
Be concise and helpful.""",
        tools=[get_user_datasets_tool, get_current_time_tool],
        llm=llm,
    )

