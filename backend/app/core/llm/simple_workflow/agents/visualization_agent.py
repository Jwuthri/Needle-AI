"""Visualization Agent - Generates charts and graphs"""

from typing import Any, Dict, List, Optional

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
    # Create wrapper functions that hide user_id from LLM
    def generate_bar_chart(
        data: Optional[List[Dict[str, Any]]] = None,
        title: str = "",
        x_label: str = "",
        y_label: str = "",
        context_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate a bar chart visualization."""
        return review_analysis_tools.generate_bar_chart(
            data=data, title=title, x_label=x_label, y_label=y_label,
            user_id=user_id, context_key=context_key
        )
    
    def generate_line_chart(
        data: Optional[List[Dict[str, Any]]] = None,
        title: str = "",
        x_label: str = "",
        y_label: str = "",
        context_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate a line chart visualization."""
        return review_analysis_tools.generate_line_chart(
            data=data, title=title, x_label=x_label, y_label=y_label,
            user_id=user_id, context_key=context_key
        )
    
    def generate_pie_chart(
        data: Optional[List[Dict[str, Any]]] = None,
        title: str = "",
        context_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate a pie chart visualization."""
        return review_analysis_tools.generate_pie_chart(
            data=data, title=title, user_id=user_id, context_key=context_key
        )
    
    def generate_heatmap(
        data: Optional[List[Dict[str, Any]]] = None,
        title: str = "",
        context_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate a heatmap visualization."""
        return review_analysis_tools.generate_heatmap(
            data=data, title=title, user_id=user_id, context_key=context_key
        )
    
    generate_bar_chart_tool = FunctionTool.from_defaults(fn=generate_bar_chart)
    generate_line_chart_tool = FunctionTool.from_defaults(fn=generate_line_chart)
    generate_pie_chart_tool = FunctionTool.from_defaults(fn=generate_pie_chart)
    generate_heatmap_tool = FunctionTool.from_defaults(fn=generate_heatmap)
    
    return FunctionAgent(
        name="visualization",
        description="Specialist in generating charts, graphs, and visualizations",
        system_prompt="""You are a data visualization specialist. You create:
1. Bar charts for categorical comparisons
2. Line charts for trends over time
3. Pie charts for distributions
4. Heatmaps for correlation analysis

Choose the appropriate chart type based on the data and analysis needs.
Generate PNG files and return the image paths.

IMPORTANT: 
- Visualization tools can automatically access data from previous analysis agents via context_key parameter
- Use context_key to reference stored data (this avoids passing large datasets through tool calls):
  * "gap_analysis_data" for gap analysis bar charts
  * "trend_data" or "sentiment_trend_data" for trend line charts  
  * "sentiment_distribution_data" for sentiment pie charts
  * "cluster_data" for cluster size bar/pie charts
- Example: generate_line_chart(context_key="trend_data", title="Rating Trends", x_label="Period", y_label="Average Rating")
- You can also pass data directly, but using context_key is preferred for large datasets and avoids token costs

After creating visualizations, hand off to Report Writer to include them in the final report.
Always create clear, informative visualizations with proper labels and titles.""",
        tools=[
            generate_bar_chart_tool,
            generate_line_chart_tool,
            generate_pie_chart_tool,
            generate_heatmap_tool,
        ],
        llm=llm,
    )
