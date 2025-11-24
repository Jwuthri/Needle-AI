"""Visualizer Agent - creates plots from datasets."""
from app.core.llm.lg_workflow.tools.base import get_dataset_info_tool
from app.core.llm.lg_workflow.tools.viz import generate_plot_tool
from .base import create_agent, llm

# Visualizer Agent
visualizer_tools = [get_dataset_info_tool, generate_plot_tool]
visualizer_node = create_agent(
    llm,
    visualizer_tools,
    "You are a Visualizer. Your goal is to create plots from datasets. "
    "IMPORTANT: You MUST follow this workflow:\\n"
    "1. First, use `get_dataset_info_tool` to fetch the dataset's schema and see what columns are available.\\n"
    "2. Then, intelligently map the user's request to the actual column names. For example:\\n"
    "   - If user says 'sentiment polarity', look for columns like 'polarity', 'sentiment', 'compound', etc.\\n"
    "   - If user says 'price', look for columns like 'price', 'amount', 'cost', etc.\\n"
    "3. Finally, call `generate_plot_tool` with the correct dataset_id and actual column names.\\n"
    "Look at the conversation history to find the `dataset_id`. "
    "Infer the best `plot_type` (e.g., 'hist' for distributions, 'bar' for categorical data, 'scatter' for numerical relationships). "
    "NEVER assume a column name exists - always check first with get_dataset_info_tool."
)
