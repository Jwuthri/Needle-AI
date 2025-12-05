from langchain_core.tools import tool
from app.core.llm.lg_workflow.data.manager import DataManager
import pandas as pd
from typing import List, Optional, Literal

@tool
async def list_datasets_tool(user_id: str) -> str:
    """Lists all available datasets with their table names and descriptions."""
    dm = DataManager.get_instance("default")
    return await dm.list_datasets(user_id)


@tool
async def filter_dataset_tool(
    table_name: str,
    column: str,
    value: str,
    user_id: str,
    operator: str = "contains"
) -> str:
    """
    Filters a dataset by column value and saves the result for analysis.
    
    Args:
        table_name: Source dataset to filter
        column: Column name to filter on (e.g., 'company_name', 'source', 'rating')
        value: Value to filter for
        user_id: User ID
        operator: How to match - 'contains' (case-insensitive), 'equals', 'gt', 'lt', 'gte', 'lte'
    
    Returns:
        Info about the filtered dataset and its new table name for subsequent analysis.
    """
    dm = DataManager.get_instance("default")
    df = await dm.get_dataset(table_name, user_id)
    
    if df is None or df.empty:
        return f"Error: Dataset '{table_name}' not found."
    
    if column not in df.columns:
        available = ", ".join(df.columns.tolist()[:20])
        return f"Error: Column '{column}' not found. Available columns: {available}"
    
    # Apply filter based on operator
    original_count = len(df)
    try:
        if operator == "contains":
            # Case-insensitive contains
            mask = df[column].astype(str).str.lower().str.contains(value.lower(), na=False)
        elif operator == "equals":
            # Try numeric comparison first, then string
            try:
                mask = df[column] == float(value)
            except (ValueError, TypeError):
                mask = df[column].astype(str).str.lower() == value.lower()
        elif operator == "gt":
            mask = pd.to_numeric(df[column], errors='coerce') > float(value)
        elif operator == "lt":
            mask = pd.to_numeric(df[column], errors='coerce') < float(value)
        elif operator == "gte":
            mask = pd.to_numeric(df[column], errors='coerce') >= float(value)
        elif operator == "lte":
            mask = pd.to_numeric(df[column], errors='coerce') <= float(value)
        else:
            return f"Error: Unknown operator '{operator}'. Use: contains, equals, gt, lt, gte, lte"
        
        filtered_df = df[mask].copy()
    except Exception as e:
        return f"Error filtering: {str(e)}"
    
    if filtered_df.empty:
        return f"No rows match filter: {column} {operator} '{value}'. Original dataset has {original_count} rows."
    
    # Create artifact name from filter
    safe_value = "".join(c if c.isalnum() else "_" for c in value.lower())[:20]
    artifact_name = f"{table_name}_filtered_{column}_{safe_value}"
    
    # Save to cache for subsequent tools
    description = f"Filtered from {table_name} where {column} {operator} '{value}'"
    await dm.save_artifact(filtered_df, artifact_name, description, user_id)
    
    # Return summary
    output = [
        f"✅ **Filtered Dataset Created**",
        f"",
        f"**New Table Name:** `{artifact_name}` (use this for analysis)",
        f"**Filter:** {column} {operator} '{value}'",
        f"**Rows:** {len(filtered_df)} (from {original_count} original)",
        f"",
        f"**Sample of filtered data:**"
    ]
    
    # Show sample
    sample = filtered_df.head(3)
    # Only show key columns if too many
    if len(sample.columns) > 6:
        key_cols = [c for c in ['text', 'content', 'rating', 'source', column] if c in sample.columns]
        if len(key_cols) < 3:
            key_cols = list(sample.columns)[:5]
        sample = sample[key_cols]
    
    output.append(sample.to_markdown(index=False))
    
    return "\n".join(output)

@tool
async def get_dataset_info_tool(table_name: str, user_id: str) -> str:
    """Returns comprehensive metadata and sample data for a dataset given its table name."""
    dm = DataManager.get_instance("default")
    df = await dm.get_dataset(table_name, user_id)
    if df is None or df.empty:
        return f"Error: Dataset '{table_name}' not found."
    
    meta = await dm.get_metadata(table_name, user_id)
    
    # Build comprehensive info output
    output = []
    output.append(f"# Dataset Information: '{table_name}'")
    output.append(f"\n**Table Name:** {meta.get('table_name', table_name)}")
    output.append(f"**Description:** {meta.get('description', 'N/A')}")
    output.append(f"**Total Rows:** {meta.get('row_count', 0)}")
    output.append(f"**Total Columns:** {len(df.columns)}")
    
    # Field Metadata (column descriptions and types)
    if meta.get('field_metadata'):
        output.append("\n## Column Details")
        for field in meta['field_metadata']:
            # Support both 'column_name' and 'field_name' keys
            col_name = field.get('column_name') or field.get('field_name') or field.get('name', 'Unknown')
            data_type = field.get('data_type', 'Unknown')
            description = field.get('description', '')
            output.append(f"- **{col_name}** ({data_type}): {description if description else 'No description'}")
    
    # Column Statistics
    if meta.get('column_stats'):
        output.append("\n## Column Statistics")
        try:
            import pandas as pd
            stats_df = pd.DataFrame.from_dict(meta['column_stats'], orient='index')
            output.append(stats_df.to_markdown())
        except Exception:
            output.append(str(meta['column_stats']))
    
    # Sample Data
    if meta.get('sample_data'):
        output.append("\n## Sample Data (First 5 Rows)")
        try:
            import pandas as pd
            sample_df = pd.DataFrame(meta['sample_data'])
            output.append(sample_df.to_markdown(index=False))
        except Exception:
            # Fallback to dataframe head if sample_data fails
            output.append(df.head().to_markdown(index=False))
    else:
        # Use dataframe head as fallback
        output.append("\n## Sample Data (First 5 Rows)")
        output.append(df.head().to_markdown(index=False))
    
    # Vector store columns (if embeddings are available)
    if meta.get('vector_store_columns'):
        vector_cols = meta['vector_store_columns']
        output.append("\n## Embedding Information")
        output.append(f"- **Main Column:** {vector_cols.get('main_column', 'N/A')}")
        if vector_cols.get('alternative_columns'):
            output.append(f"- **Alternative Columns:** {', '.join(vector_cols.get('alternative_columns', []))}")
        output.append("- **Note:** This dataset has embeddings available for semantic search")
    
    return "\n".join(output)
