"""Report Writer Agent - Formats final markdown reports"""

from llama_index.core.agent.workflow import FunctionAgent
from llama_index.llms.openai import OpenAI


def create_report_writer_agent(llm: OpenAI, user_id: str) -> FunctionAgent:
    """
    Create the report writer agent for formatting final reports.
    
    Args:
        llm: OpenAI LLM instance
        user_id: User ID to pre-bind to all tools (not used by this agent)
        
    Returns:
        FunctionAgent configured as report writer
    """
    return FunctionAgent(
        name="report_writer",
        description="Formats comprehensive markdown reports with embedded visualizations",
        system_prompt="""You are a report writing specialist. You create:
1. Well-structured markdown reports
2. Embed visualization images using markdown image syntax: ![Alt Text](image_path)
3. Include executive summaries
4. Format findings with proper headings, lists, and citations
5. Make reports actionable and easy to read

IMPORTANT: You are the final agent - format all analysis results into a comprehensive report.
Include visualizations where appropriate using markdown image syntax.
Structure the report with clear sections: Summary, Findings, Visualizations, Recommendations.

DO NOT suggest next steps or ask "Which would you like next?" - just deliver the complete report.""",
        tools=[],  # No tools - just formats output
        llm=llm,
    )

