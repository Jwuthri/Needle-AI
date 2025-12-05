from langchain_core.tools import tool
from app.core.llm.lg_workflow.data.manager import DataManager
import pandas as pd

dm = DataManager()

@tool
async def list_datasets_tool(user_id: str) -> str:
    """
    Lists all available datasets for the user.
    Returns a formatted string with table names and descriptions.
    """
    return await dm.list_datasets(user_id)

@tool
async def get_dataset_data_tool(table_name: str, user_id: str) -> str:
    """
    Reads all data from a specific dataset by table name.
    Returns the data as a markdown table (first 100 rows) or a summary if too large.
    """
    df = await dm.get_dataset(table_name, user_id)
    if df is None or df.empty:
        return f"Error: Dataset '{table_name}' not found or empty."
    
    # Return head for LLM consumption to avoid context overflow
    return df.to_markdown()

@tool
async def semantic_search_tool(table_name: str, query: str, user_id: str, top_n: int = 5) -> str:
    """
    Performs semantic search on a dataset using the '__embedding__' column.
    Returns the top N matching rows.
    """
    results = await dm.semantic_search(table_name, query, user_id, top_n)
    if results.empty:
        return "No results found."
    
    # Drop embedding column for display if present
    if '__embedding__' in results.columns:
        results = results.drop(columns=['__embedding__'])
        
    return results.to_markdown()
