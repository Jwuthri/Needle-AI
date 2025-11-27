"""Data Librarian Agent - helps users find the right datasets."""
from langchain_core.tools import tool
from app.core.llm.lg_workflow.tools.base import list_datasets_tool, get_dataset_info_tool
from .base import create_agent, llm

def create_librarian_node(user_id: str):
    """Create librarian agent with tools bound to user_id."""
    
    # Create wrapper tools with user_id bound
    @tool
    async def list_datasets() -> str:
        """Lists all available datasets with their table names and descriptions."""
        return await list_datasets_tool.coroutine(user_id=user_id)
    
    @tool
    async def get_dataset_info(table_name: str) -> str:
        """Returns metadata and the first 5 rows of a dataset given its table name."""
        return await get_dataset_info_tool.coroutine(table_name=table_name, user_id=user_id)
    
    librarian_tools = [list_datasets, get_dataset_info]
    
    return create_agent(
        llm, 
        librarian_tools, 
        """You are a Data Librarian - help users find datasets. BE VERY CONCISE.

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
    )
