from langchain_core.tools import tool
from app.core.llm.lg_workflow.data.manager import DataManager
import pandas as pd
from typing import List, Optional

@tool
async def list_datasets_tool(user_id: str) -> str:
    """Lists all available datasets with their table names and descriptions."""
    dm = DataManager.get_instance("default")
    return await dm.list_datasets(user_id)

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
            col_name = field.get('column_name', 'Unknown')
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
