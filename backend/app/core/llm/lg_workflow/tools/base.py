from langchain_core.tools import tool
from app.core.llm.lg_workflow.data.manager import DataManager
import pandas as pd
from typing import List, Optional

# Singleton access
dm = DataManager()

@tool
def list_datasets_tool() -> str:
    """Lists all available datasets with their IDs and descriptions."""
    return dm.list_datasets()

@tool
def get_dataset_info_tool(dataset_id: str) -> str:
    """Returns metadata and the first 5 rows of a dataset given its ID."""
    df = dm.get_dataset(dataset_id)
    if df is None:
        return f"Error: Dataset {dataset_id} not found."
    
    meta = dm.get_metadata(dataset_id)
    info = f"Name: {meta['name']}\nDescription: {meta['description']}\nRows: {meta['rows']}\nColumns: {meta['columns']}\n\nHead:\n{df.head().to_markdown()}"
    return info
