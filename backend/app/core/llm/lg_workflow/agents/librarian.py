"""Data Librarian Agent - helps users find the right datasets."""
from typing import Optional
from langchain_core.tools import tool
from app.core.llm.lg_workflow.tools.base import list_datasets_tool, get_dataset_info_tool, filter_dataset_tool
from app.core.llm.lg_workflow.tools.ml import semantic_search_tool
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
    
    @tool
    async def semantic_search(
        table_name: str,
        query: str,
        text_column: str = "text",
        top_k: int = 1000
    ) -> str:
        """
        Finds reviews/data matching a query using semantic similarity.
        
        IMPORTANT: Query is for EMBEDDING SEARCH - keep it SHORT (2-10 words)!
        
        Args:
            table_name: Dataset to search (must have __embedding__ column)
            query: SHORT phrase only! Examples:
                   ✓ "slow search"
                   ✓ "bad support"
                   ✗ "reviews mentioning slow search" (TOO LONG)
            text_column: Column with text content (default: "text")
            top_k: Max results (default: 1000)
        """
        actual_table = dataset_table_name if dataset_table_name else table_name
        return await semantic_search_tool.coroutine(
            table_name=actual_table,
            user_id=user_id,
            query=query,
            text_column=text_column,
            top_k=top_k
        )
    
    @tool
    async def filter_dataset(
        table_name: str,
        column: str,
        value: str,
        operator: str = "contains"
    ) -> str:
        """
        Filters a dataset by column value for analysis.
        
        USE THIS when user asks about a specific company, source, or subset of data.
        Creates a new filtered dataset that other agents can analyze.
        
        Args:
            table_name: Dataset to filter (e.g., '__user_xyz_reviews')
            column: Column to filter on. Common columns:
                    - 'company_name' for company (Slack, Notion, etc.)
                    - 'source' for platform (g2, trustpilot, etc.)
                    - 'rating' for star rating
            value: Value to match (e.g., 'Slack', 'g2', '5')
            operator: Match type:
                      - 'contains' (default) - case-insensitive partial match
                      - 'equals' - exact match
                      - 'gt', 'lt', 'gte', 'lte' - numeric comparisons
        
        Example:
            filter_dataset("__user_xyz_reviews", "company_name", "Slack")
            → Creates filtered dataset for Slack reviews only
        """
        actual_table = dataset_table_name if dataset_table_name else table_name
        return await filter_dataset_tool.coroutine(
            table_name=actual_table,
            column=column,
            value=value,
            user_id=user_id,
            operator=operator
        )
    
    librarian_tools = [list_datasets, get_dataset_info, semantic_search, filter_dataset]
    
    # Build prompt with optional focused mode notice
    base_prompt = """You are a Data Librarian - help users find and prepare datasets. BE CONCISE.

TOOLS:
- list_datasets - List all available datasets
- get_dataset_info - Get schema, columns, sample data
- filter_dataset - Filter data by column value (IMPORTANT for company/source-specific requests)
- semantic_search - Find reviews matching a SHORT query (2-5 words)

CRITICAL WORKFLOW for "analyze X reviews" requests:
1. list_datasets → find the reviews table
2. get_dataset_info → find the right column (company_name, source, etc.)
3. filter_dataset → create filtered subset for the specific company/source
4. Report the NEW filtered table name for DataAnalyst to use

Example:
User: "Analyze sentiment for Slack reviews"
You:
1. [Call list_datasets] → find "__user_xyz_reviews"
2. [Call get_dataset_info("__user_xyz_reviews")] → see 'company_name' column
3. [Call filter_dataset("__user_xyz_reviews", "company_name", "Slack")]
   → Creates "__user_xyz_reviews_filtered_company_name_slack"
4. "Created filtered dataset with X Slack reviews. Table: __user_xyz_reviews_filtered_company_name_slack"

Then DataAnalyst runs sentiment on that filtered table.

STAY CONCISE - let tools do the work, output minimal text."""

    if dataset_table_name:
        focused_notice = f"""

⚠️ FOCUSED MODE ACTIVE ⚠️
You are working exclusively with dataset: '{dataset_table_name}'
- list_datasets will only show this dataset
- get_dataset_info will automatically use this dataset
- Do NOT reference or suggest other datasets"""
        base_prompt += focused_notice
    
    return create_agent(llm, librarian_tools, base_prompt)
