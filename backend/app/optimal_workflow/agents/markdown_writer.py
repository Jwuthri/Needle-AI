"""
Markdown writer agent for creating well-structured markdown reports.
"""

from llama_index.core.agent.workflow import FunctionAgent

from .base import get_llm


def create_markdown_writer() -> FunctionAgent:
    """
    Create a markdown writer agent.
    """
    llm = get_llm()
    
    return FunctionAgent(
        name="MarkdownWriter",
        description="Writes comprehensive markdown reports with proper structure and formatting.",
        system_prompt="""You are the MarkdownWriter. You specialize in creating well-structured markdown reports.
        
        Your responsibilities:
        - Create reports with clear headings and sections
        - Use bullet points, numbered lists, and emphasis effectively
        - Include Introduction, Analysis, Findings, and Recommendations sections
        - Format data insights in readable tables when appropriate
        - Use proper markdown syntax (*italic*, **bold**, `code`)
        
        When you receive context, write a comprehensive markdown report.""",
        llm=llm,
        # can_handoff_to=["ReportCoordinator"],
    )