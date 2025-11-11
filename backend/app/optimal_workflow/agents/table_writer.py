"""
Table writer agent for creating structured tabular data reports.
"""

from llama_index.core.agent.workflow import FunctionAgent
from .base import get_llm


def create_table_writer() -> FunctionAgent:
    """
    Create a table writer agent.
    """
    llm = get_llm()
    
    return FunctionAgent(
        name="TableWriter", 
        description="Writes structured tabular data reports.",
        system_prompt="""You are the TableWriter. You specialize in presenting data in clear, well-formatted tables.
        
        Your responsibilities:
        - Present data in clear, well-formatted tables
        - Use markdown table syntax with proper alignment
        - Include headers and organize data logically
        - Add summary rows when appropriate
        - Ensure tables are readable and informative
        
        When you receive context, create a table-focused report.""",
        llm=llm,
        # can_handoff_to=["ReportCoordinator"],
    )