"""
Report coordinator agent for managing the writing team and finalizing reports.
"""

from llama_index.core.agent.workflow import FunctionAgent
from .base import get_llm


def create_report_coordinator(format_type: str = "markdown") -> FunctionAgent:
    """
    Create a report coordinator agent.
    """
    llm = get_llm()
    
    return FunctionAgent(
        name="ReportCoordinator",
        description="Coordinates the writing team and finalizes reports.",
        system_prompt=f"""You are the ReportCoordinator. You manage the writing team and finalize reports.
        
        The requested format is: {format_type}
        
        Your responsibilities:
        - Receive completed reports from writer agents
        - Ensure the report matches the requested format
        - Make final adjustments if needed
        - Provide the final polished report
        
        You are the final step in the writing process.""",
        llm=llm,
        tools=[],
        can_handoff_to=[],  # Final agent, no handoffs
    )