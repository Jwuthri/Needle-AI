"""Visualization Agent - Generates charts and graphs"""

from typing import Any, Dict, List, Optional

from app.core.llm.simple_workflow.tools.visualization_tool import generate_bar_chart, generate_heatmap, generate_line_chart, generate_pie_chart
from llama_index.core.agent.workflow import FunctionAgent
from llama_index.core.tools import FunctionTool
from llama_index.llms.openai import OpenAI

from app.core.llm.workflow.tools import review_analysis_tools


def create_visualization_agent(llm: OpenAI, user_id: str) -> FunctionAgent:
    """
    Create the visualization agent for generating charts and graphs.
    
    Args:
        llm: OpenAI LLM instance
        user_id: User ID to pre-bind to all tools
        
    Returns:
        FunctionAgent configured as visualization specialist
    """
    
    generate_bar_chart_tool = FunctionTool.from_defaults(fn=generate_bar_chart)
    generate_line_chart_tool = FunctionTool.from_defaults(fn=generate_line_chart)
    generate_pie_chart_tool = FunctionTool.from_defaults(fn=generate_pie_chart)
    generate_heatmap_tool = FunctionTool.from_defaults(fn=generate_heatmap)
    
    return FunctionAgent(
        name="visualization",
        description="Generates charts. BRIEF responses only.",
        system_prompt="""You are a visualization specialist. Create charts, BE BRIEF.

CHART TYPES:
- Bar → comparisons
- Line → trends
- Pie → distributions
- Heatmap → correlations

CRITICAL - ALL PARAMETERS ARE REQUIRED:
When calling ANY chart generation tool, you MUST provide ALL parameters:
- title: Chart title (string)
- user_id: User identifier (string)
- data: List of dictionaries with data points (REQUIRED!)
- x_label, y_label: Axis labels (for bar/line charts)

Example data formats:
- Bar/Line: [{"x": "Jan", "y": 100}, {"x": "Feb", "y": 150}]
- Pie: [{"label": "Positive", "value": 60}, {"label": "Negative", "value": 40}]
- Heatmap: [{"x": "Cat1", "y": "Metric1", "value": 10}]

BREVITY RULES:
- Generate charts silently
- NO explanations or status messages
- NEVER mention routing, agents, or internal workflow
- Stay completely silent - let your charts speak""",
        tools=[
            generate_bar_chart_tool,
            generate_line_chart_tool,
            generate_pie_chart_tool,
            generate_heatmap_tool,
        ],
        llm=llm,
    )
