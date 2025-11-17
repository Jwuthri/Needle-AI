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

USE CONTEXT_KEY:
- "gap_analysis_data" → bar charts
- "trend_data" → line charts
- "sentiment_distribution_data" → pie charts
- "cluster_data" → bar/pie charts

BREVITY RULES:
- Generate chart, then route to Report Writer
- NO explanations
- If you must respond, keep under 15 words
- Example: "Created chart" then route""",
        tools=[
            generate_bar_chart_tool,
            generate_line_chart_tool,
            generate_pie_chart_tool,
            generate_heatmap_tool,
        ],
        llm=llm,
    )
