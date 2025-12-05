"""Visualizer Agent - creates plots from datasets."""
from typing import Any, Optional
from langchain_core.tools import tool
from app.core.llm.lg_workflow.tools.base import get_dataset_info_tool
from app.core.llm.lg_workflow.tools.viz import generate_plot_from_data_tool, generate_plot_tool
from .base import create_agent, llm

def create_visualizer_node(user_id: str, dataset_table_name: Optional[str] = None):
    """Create visualizer agent with tools bound to user_id and optional focused dataset."""
    
    # Create wrapper tools with user_id bound (and optional default table_name)
    @tool
    async def get_dataset_info(table_name: str) -> str:
        """
        Returns comprehensive metadata and sample data for a dataset.
        
        Includes:
        - Table name and description
        - Total rows and columns
        - Column details (name, type, description)
        - Column statistics
        - Sample data (first 5 rows)
        - Embedding information if available
        
        Args:
            table_name: Name of the dataset to get info for
        """
        actual_table = dataset_table_name if dataset_table_name else table_name
        return await get_dataset_info_tool.coroutine(table_name=actual_table, user_id=user_id)

    @tool
    async def generate_plot_from_data(data: list[dict[str, Any]], x_column: str, y_column: str, title: str, plot_type: str = "bar") -> str:
        """
        Generate a high-quality plot from raw data using Plotly.
        
        Use this when you have data already computed/aggregated and don't need to read from a table.
        Saves the plot as a PNG file and returns a markdown report with the file path.
        
        Args:
            data: List of dictionaries containing the data to plot (e.g., [{"category": "A", "value": 10}, ...])
            x_column: Key name for x-axis values in the data dictionaries
            y_column: Key name for y-axis values in the data dictionaries
            title: Chart title
            plot_type: Type of plot - 'bar' (default), 'scatter', 'line', 'pie', 'histogram'
        """
        return await generate_plot_from_data_tool.coroutine(data=data, x_column=x_column, y_column=y_column, user_id=user_id, title=title, plot_type=plot_type)
    
    @tool
    async def generate_plot(table_name: str, x_column: str, y_column: str, plot_type: str = "scatter", title: str = "") -> str:
        """
        Generate a high-quality interactive plot for a dataset using Plotly.
        
        Saves the plot as a PNG file to the user's graph directory and returns a markdown report.
        
        Args:
            table_name: Name of the dataset to plot
            x_column: Column name for x-axis
            y_column: Column name for y-axis (use empty string "" for histogram or pie with auto-count)
            plot_type: Type of plot - Options:
                - 'scatter': Scatter plot (default)
                - 'line': Line chart for trends
                - 'bar': Bar chart for comparisons
                - 'histogram': Distribution histogram (uses only x_column)
                - 'pie': Pie chart (x_column=labels, y_column="" for auto-count or values column)
                - 'box': Box plot for distribution analysis
            title: Custom chart title (optional, auto-generated if not provided)
        """
        actual_table = dataset_table_name if dataset_table_name else table_name
        return await generate_plot_tool.coroutine(table_name=actual_table, x_column=x_column, y_column=y_column, user_id=user_id, plot_type=plot_type, title=title)
    
    visualizer_tools = [get_dataset_info, generate_plot, generate_plot_from_data]
    
    # Build prompt with optional focused mode notice
    base_prompt = """You are a Visualizer - create charts from datasets.

TOOLS:
- get_dataset_info - Get schema and sample data
- generate_plot - Create high-quality chart

WORKFLOW:
1. Read conversation history for context (table name, columns, recent analysis)
2. IF columns unclear: Call get_dataset_info(table_name)
3. Call generate_plot(table_name, x_column, y_column, plot_type)
4. Tool returns full markdown report with chart path

CHART TYPES:
- scatter, line, bar, histogram (y_column=""), pie (x_column=category, y_column=""), box

COLUMN PATTERNS:
- sentiment → sentiment_polarity, sentiment_label
- rating → rating, score, stars
- date → date, created_at, timestamp
- text → text, review, comment

PIE CHART RULE (for categorical data like sentiment):
- x_column = category column name (e.g., "sentiment_label")
- y_column = "" (empty string - triggers auto-count)

CRITICAL RULES:
- generate_plot returns complete markdown report with chart details
- DO NOT add commentary or explanations
- Just call the tool and pass output through

Example:
User: "Show sentiment as pie chart"
You: [Call generate_plot(table="reviews", x_column="sentiment_label", y_column="", plot_type="pie")]
[Tool returns full report]
Pass it through

Remember: Tool output is comprehensive. Just call it correctly."""

    if dataset_table_name:
        focused_notice = f"""

⚠️ FOCUSED MODE ACTIVE ⚠️
You are working exclusively with dataset: '{dataset_table_name}'
- ALWAYS use table_name='{dataset_table_name}' for all tool calls
- Do NOT reference or visualize other datasets
- The table_name parameter will auto-redirect to this dataset"""
        base_prompt += focused_notice
    
    return create_agent(llm, visualizer_tools, base_prompt)
