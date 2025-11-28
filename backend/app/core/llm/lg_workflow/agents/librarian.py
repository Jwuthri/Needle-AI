"""Data Librarian Agent - helps users find the right datasets."""
from typing import Optional
from langchain_core.tools import tool
from app.core.llm.lg_workflow.tools.base import list_datasets_tool, get_dataset_info_tool
from .base import create_agent, llm

def create_librarian_node(user_id: str, dataset_table_name: Optional[str] = None):
    """Create librarian agent with tools bound to user_id and optional focused dataset."""
    
    # Create wrapper tools with user_id bound
    @tool
    async def list_datasets() -> str:
        """
        Lists all available datasets with their table names and descriptions.
        
        Returns a formatted list of datasets the user has access to, including:
        - Table name (use this for other tool calls)
        - Description of the dataset
        - Row count
        """
        result = await list_datasets_tool.coroutine(user_id=user_id)
        
        # If focused on a specific dataset, filter the results
        if dataset_table_name:
            lines = result.split('\n')
            filtered = ["Focused Dataset:"]
            for line in lines[1:]:  # Skip header
                if f"Table: {dataset_table_name}" in line:
                    filtered.append(line)
                    break
            if len(filtered) == 1:
                # Dataset not found in list, return helpful message
                filtered.append(f"- Table: {dataset_table_name} (use get_dataset_info for details)")
            return '\n'.join(filtered)
        return result
    
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
        # If focused mode, override the table_name to ensure we use the focused dataset
        actual_table = dataset_table_name if dataset_table_name else table_name
        return await get_dataset_info_tool.coroutine(table_name=actual_table, user_id=user_id)
    
    librarian_tools = [list_datasets, get_dataset_info]
    
    # Build prompt with optional focused mode notice
    base_prompt = """You are a Data Librarian - help users find datasets. BE VERY CONCISE.

WORKFLOW:
1. Call list_datasets OR get_dataset_info(table_name)
2. Tool returns complete formatted output
3. Add ONE sentence max if needed (e.g., "Found X datasets.")
4. Pass through tool output

CRITICAL - STAY CONCISE:
✗ NO long explanations
✗ NO reformatting tool output
✗ NO detailed summaries
✓ Call tool → Optional 1 sentence → Done

The tool output is already perfect and complete. Just call it and move on.

Example:
User: "What datasets do we have?"
You: [Call list_datasets]
Tool returns formatted list
You: "Found 3 datasets."

Example:
User needs table info
You: [Call get_dataset_info("table_name")]
Tool returns schema + sample data
You: "Dataset info retrieved."

Remember: Tools are comprehensive. You stay minimal - 1 sentence max or nothing."""

    if dataset_table_name:
        focused_notice = f"""

⚠️ FOCUSED MODE ACTIVE ⚠️
You are working exclusively with dataset: '{dataset_table_name}'
- list_datasets will only show this dataset
- get_dataset_info will automatically use this dataset
- Do NOT reference or suggest other datasets"""
        base_prompt += focused_notice
    
    return create_agent(llm, librarian_tools, base_prompt)
