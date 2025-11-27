"""Visualizer Agent - creates plots from datasets."""
from typing import Optional
from langchain_core.tools import tool
from app.core.llm.lg_workflow.tools.base import get_dataset_info_tool
from app.core.llm.lg_workflow.tools.viz import generate_plot_tool
from .base import create_agent, llm

def create_visualizer_node(user_id: str, dataset_table_name: Optional[str] = None):
    """Create visualizer agent with tools bound to user_id and optional focused dataset."""
    
    # Create wrapper tools with user_id bound (and optional default table_name)
    @tool
    async def get_dataset_info(table_name: str) -> str:
        """Returns metadata and the first 5 rows of a dataset given its table name."""
        actual_table = dataset_table_name if dataset_table_name else table_name
        return await get_dataset_info_tool.coroutine(table_name=actual_table, user_id=user_id)

    @tool
    async def generate_plot(table_name: str, x_column: str, y_column: str, plot_type: str = "scatter") -> str:
        """Generate a high-quality plot for a dataset using Plotly."""
        actual_table = dataset_table_name if dataset_table_name else table_name
        return await generate_plot_tool.coroutine(table_name=actual_table, x_column=x_column, y_column=y_column, user_id=user_id, plot_type=plot_type)
    
    visualizer_tools = [get_dataset_info, generate_plot]
    
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
