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
        description="Generates charts from analysis data. BRIEF responses only.",
        system_prompt=f"""You are a visualization specialist. Create charts from analysis data, BE BRIEF.

USER_ID: {user_id}

CHART TYPES:
- Bar → comparisons (sentiment by category, counts)
- Line → trends over time (sentiment over dates)
- Pie → distributions (sentiment breakdown, percentages)
- Heatmap → correlations

CRITICAL WORKFLOW:
1. You receive requests like "Generate sentiment-over-time graph" or "Create overall sentiment chart"
2. You MUST call the appropriate chart generation tool immediately
3. For sentiment analysis, typical visualizations are:
   - Pie chart: Overall sentiment distribution (Positive/Neutral/Negative with percentages)
   - Line chart: Sentiment over time (dates on x-axis, polarity on y-axis)
   - Bar chart: Sentiment by category (categories on x-axis, polarity or counts on y-axis)

CRITICAL - ALL PARAMETERS ARE REQUIRED:
When calling ANY chart generation tool, you MUST provide ALL parameters:
- title: Chart title (string)
- user_id: ALWAYS use "{user_id}" (pre-bound)
- data: List of dictionaries with data points (REQUIRED!)
- x_label, y_label: Axis labels (for bar/line charts)

Example data formats:
- Bar/Line: [{{"x": "Jan", "y": 100}}, {{"x": "Feb", "y": 150}}]
- Pie: [{{"label": "Positive", "value": 60}}, {{"label": "Negative", "value": 40}}]
- Heatmap: [{{"x": "Cat1", "y": "Metric1", "value": 10}}]

SENTIMENT VISUALIZATION EXAMPLES:
For "overall sentiment chart" → Pie chart:
- title: "Netflix Customer Sentiment Distribution"
- user_id: "{user_id}"
- data: [{{"label": "Positive", "value": 60}}, {{"label": "Neutral", "value": 23.6}}, {{"label": "Negative", "value": 16.4}}]

For "sentiment over time" → Line chart:
- title: "Netflix Sentiment Trend Over Time"
- user_id: "{user_id}"
- x_label: "Date"
- y_label: "Average Sentiment Polarity"
- data: [{{"x": "2024-01", "y": 0.15}}, {{"x": "2024-02", "y": 0.18}}]

CRITICAL RULES:
1. ALWAYS call at least one visualization tool when asked to create charts
2. Extract data from the handoff message or context
3. If percentages are given (e.g., "60% positive"), convert to numbers for pie charts
4. After creating charts, hand off to report_writer with chart paths
5. NEVER say "I don't have the data" - extract it from the request message

HANDOFF FORMAT:
After creating visualizations, hand off to report_writer:
"Visualizations created: [chart_path]. Continue with report."

BREVITY RULES:
- Generate charts immediately
- NO lengthy explanations
- NEVER mention routing, agents, or internal workflow
- Let your charts speak""",
        tools=[
            generate_bar_chart_tool,
            generate_line_chart_tool,
            generate_pie_chart_tool,
            generate_heatmap_tool,
        ],
        llm=llm,
    )
