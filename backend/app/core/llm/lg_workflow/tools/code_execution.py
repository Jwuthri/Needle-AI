"""
Code execution tool for LLM agents.

Allows the LLM to write and execute Python code for data analysis.
"""

from typing import Optional

from app.services.code_execution_service import SafeCodeExecutor, validate_code
from app.utils.logging import get_logger

logger = get_logger("code_execution_tool")


CODE_EXECUTION_DESCRIPTION = """
Execute Python code for data analysis on user datasets.

## Available Functions
- `get_dataset(dataset_id)` - Load a dataset as pandas DataFrame
- `list_datasets()` - List available dataset IDs
- `dataset_info(dataset_id)` - Get schema info about a dataset

## Available Libraries
- `pandas` (as `pd`) - Data manipulation
- `numpy` (as `np`) - Numerical computing
- `math`, `statistics` - Mathematical functions
- `datetime` - Date/time handling
- `collections`, `itertools` - Data structures
- `json`, `re` - JSON and regex

## Guidelines
1. Always use `get_dataset(dataset_id)` to load data
2. Store final results in a variable called `result`
3. Use `print()` to show intermediate outputs
4. Keep code concise and efficient
5. Handle potential errors gracefully

## Security Restrictions
- No file I/O operations
- No network access
- No system commands
- No dangerous imports (os, sys, subprocess, etc.)
- 30 second execution timeout

## Example
```python
# Load the dataset
df = get_dataset("dataset_123")

# Analyze sentiment distribution
sentiment_counts = df['rating'].value_counts()
print("Rating distribution:")
print(sentiment_counts)

# Calculate average rating by source
avg_by_source = df.groupby('source')['rating'].mean()
print("\\nAverage rating by source:")
print(avg_by_source)

# Store final result
result = avg_by_source.to_dict()
```
"""


async def execute_code_tool(
    code: str,
    dataset_id: Optional[str] = None,
    user_id: Optional[str] = None
) -> str:
    """
    Execute Python code for data analysis.
    
    Args:
        code: Python code to execute. Must use get_dataset() to load data.
        dataset_id: Optional dataset ID to pre-load (will be available as 'df')
        user_id: User ID for loading datasets
        
    Returns:
        Execution output and results as formatted string
    """
    from app.services.user_dataset_service import UserDatasetService
    from app.database.session import get_async_session
    import pandas as pd
    
    # First validate the code
    errors = validate_code(code)
    if errors:
        return f"❌ Code validation failed:\n" + "\n".join(f"- {e}" for e in errors)
    
    # Create executor
    executor = SafeCodeExecutor()
    
    # Load datasets for this user
    if user_id:
        try:
            async with get_async_session() as session:
                service = UserDatasetService(session)
                
                # Get all user datasets
                datasets = await service.list_datasets(user_id, limit=50, offset=0)
                
                for ds in datasets:
                    try:
                        # Load dataset data
                        data = await service.get_dataset_data(
                            dataset_id=ds.id,
                            user_id=user_id,
                            limit=50000,  # Load up to 50k rows
                            offset=0
                        )
                        if data and data.get('data'):
                            df = pd.DataFrame(data['data'])
                            executor.add_dataset(ds.id, df)
                            # Also add by table name for convenience
                            executor.add_dataset(ds.table_name, df)
                    except Exception as e:
                        logger.warning(f"Failed to load dataset {ds.id}: {e}")
                        continue
                        
        except Exception as e:
            logger.error(f"Error loading datasets: {e}")
            return f"❌ Error loading datasets: {str(e)}"
    
    # If specific dataset requested, pre-load it as 'df'
    if dataset_id and dataset_id in executor.datasets:
        code = f"df = get_dataset('{dataset_id}')\n" + code
    
    # Execute the code
    logger.info(f"Executing code for user {user_id}")
    result = executor.execute(code)
    
    # Format output
    output_parts = []
    
    if result.success:
        output_parts.append("✅ **Code executed successfully**")
        output_parts.append(f"⏱️ Execution time: {result.execution_time:.2f}s")
        
        if result.output.strip():
            output_parts.append("\n**Output:**")
            output_parts.append(f"```\n{result.output.strip()}\n```")
        
        if result.result_data:
            output_parts.append("\n**Result:**")
            if isinstance(result.result_data, dict):
                if result.result_data.get('type') == 'dataframe':
                    df_info = result.result_data
                    output_parts.append(f"DataFrame with shape {df_info['shape']}")
                    output_parts.append(f"Columns: {', '.join(df_info['columns'])}")
                    if df_info.get('truncated'):
                        output_parts.append("(showing first 100 rows)")
                    # Show sample data as markdown table
                    if df_info['data']:
                        sample_df = pd.DataFrame(df_info['data'][:10])
                        output_parts.append(f"\n{sample_df.to_markdown(index=False)}")
                elif result.result_data.get('type') == 'series':
                    output_parts.append(f"Series: {result.result_data['name']}")
                    output_parts.append(f"```\n{result.result_data['data']}\n```")
                else:
                    import json
                    output_parts.append(f"```json\n{json.dumps(result.result_data, indent=2, default=str)}\n```")
            else:
                output_parts.append(f"```\n{result.result_data}\n```")
    else:
        output_parts.append("❌ **Code execution failed**")
        if result.output.strip():
            output_parts.append(f"\n**Partial output:**\n```\n{result.output.strip()}\n```")
        output_parts.append(f"\n**Error:**\n```\n{result.error}\n```")
    
    return "\n".join(output_parts)


# Tool definition for LangGraph agents
CODE_EXECUTION_TOOL = {
    "name": "execute_python_code",
    "description": CODE_EXECUTION_DESCRIPTION,
    "parameters": {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "Python code to execute. Use get_dataset(id) to load data."
            },
            "dataset_id": {
                "type": "string",
                "description": "Optional: Dataset ID to pre-load as 'df' variable"
            }
        },
        "required": ["code"]
    }
}

