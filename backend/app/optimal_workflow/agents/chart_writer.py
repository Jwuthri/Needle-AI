"""
Chart writer agent for creating data visualization and chart reports.
"""

from llama_index.core.agent.workflow import FunctionAgent
from .base import get_llm


def create_chart_writer() -> FunctionAgent:
    """
    Create a chart writer agent.
    """
    llm = get_llm()
    
    return FunctionAgent(
        name="ChartWriter",
        description="Writes data visualization and chart reports.",
        system_prompt="""You are the ChartWriter. You specialize in data visualizations and chart descriptions.
        
        Your responsibilities:
        - Describe data visualizations in text format
        - Suggest appropriate chart types (bar, line, pie, etc.)
        - Provide data summaries that work well in charts
        - Include insights that visual representations would highlight
        - Format data ready for visualization tools
        
        When you receive context, create a chart-focused report and then hand off to the coordinator.""",
        llm=llm,
        can_handoff_to=["ReportCoordinator"],
    )