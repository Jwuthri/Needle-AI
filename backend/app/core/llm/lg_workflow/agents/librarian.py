"""Data Librarian Agent - helps users find the right datasets."""
from app.core.llm.lg_workflow.tools.base import list_datasets_tool, get_dataset_info_tool
from .base import create_agent, llm

# Data Librarian Agent
librarian_tools = [list_datasets_tool, get_dataset_info_tool]
librarian_node = create_agent(
    llm, 
    librarian_tools, 
    "You are a Data Librarian. Your goal is to help users find the right datasets. "
    "You have access to the catalog of datasets. "
    "Use `list_datasets` to see what's available and `get_dataset_info` to understand schemas. "
    "When you have found the relevant dataset IDs, report them back."
)
