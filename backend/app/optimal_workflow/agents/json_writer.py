"""
JSON writer agent for creating structured JSON responses.
"""

from llama_index.core.agent.workflow import FunctionAgent

from .base import get_llm


def create_json_writer() -> FunctionAgent:
    """
    Create a JSON writer agent.
    """
    llm = get_llm()
    
    return FunctionAgent(
        name="JsonWriter",
        description="Writes structured JSON responses.",
        system_prompt="""You are the JsonWriter. You specialize in creating structured JSON responses.
        
        Your responsibilities:
        - Structure responses as valid JSON objects
        - Organize data hierarchically with clear keys
        - Include metadata like timestamps, counts, and summaries
        - Ensure all strings are properly escaped
        - Provide structured data that's API-ready
        
        When you receive context, create a JSON-formatted report and then hand off to the coordinator.""",
        llm=llm,
        can_handoff_to=["ReportCoordinator"],
    )