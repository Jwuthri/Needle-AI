"""
Utilities for creating and managing dynamic database tables from DataFrames.
"""

import json
import re
from typing import Any

from app.config import get_settings
import pandas as pd
from sqlalchemy import text
from sqlalchemy.types import (
    Boolean,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    TypeEngine,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.logging import get_logger

logger = get_logger(__name__)


def sanitize_table_name(name: str) -> str:
    """
    Sanitize table name to prevent SQL injection and ensure valid identifier.
    
    Args:
        name: Original table name
        
    Returns:
        Sanitized table name
    """
    # Replace invalid characters with underscores
    sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', name)
    # Remove leading/trailing underscores
    sanitized = sanitized.strip('_')
    # Ensure it starts with a letter or underscore
    if sanitized and not sanitized[0].isalpha() and sanitized[0] != '_':
        sanitized = '_' + sanitized
    # Limit length (PostgreSQL limit is 63 chars)
    if len(sanitized) > 63:
        sanitized = sanitized[:63]
    return sanitized.lower()


def sanitize_column_name(name: str) -> str:
    """
    Sanitize column name to prevent SQL injection.
    
    Args:
        name: Original column name
        
    Returns:
        Sanitized column name
    """
    # Replace invalid characters with underscores
    sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', str(name))
    # Remove leading/trailing underscores
    sanitized = sanitized.strip('_')
    # Ensure it starts with a letter or underscore
    if sanitized and not sanitized[0].isalpha() and sanitized[0] != '_':
        sanitized = '_' + sanitized
    # Limit length
    if len(sanitized) > 63:
        sanitized = sanitized[:63]
    return sanitized.lower()


def is_json_column(series: pd.Series) -> bool:
    """
    Check if a pandas Series contains JSON/dict-like data.
    
    Args:
        series: Pandas Series to check
        
    Returns:
        True if column contains JSON/dict data
    """
    if len(series) == 0:
        return False
    
    # Sample non-null values to check
    non_null = series.dropna()
    if len(non_null) == 0:
        return False
    
    # Check first few non-null values
    sample_size = min(10, len(non_null))
    sample_values = non_null.head(sample_size)
    
    json_count = 0
    for value in sample_values:
        # Check if value is dict or list
        if isinstance(value, (dict, list)):
            json_count += 1
        # Check if value is a string that looks like JSON
        elif isinstance(value, str) and (
            (value.strip().startswith('{') and value.strip().endswith('}')) or
            (value.strip().startswith('[') and value.strip().endswith(']'))
        ):
            json_count += 1
    
    # If majority of samples are JSON-like, treat as JSON column
    return json_count >= (sample_size * 0.5)


def pandas_dtype_to_sqlalchemy(dtype: Any) -> TypeEngine:
    """
    Convert pandas dtype to SQLAlchemy type.
    
    Args:
        dtype: Pandas dtype
        
    Returns:
        SQLAlchemy type
    """
    dtype_str = str(dtype).lower()
    
    if 'int' in dtype_str:
        return Integer()
    elif 'float' in dtype_str or 'double' in dtype_str:
        return Float()
    elif 'bool' in dtype_str:
        return Boolean()
    elif 'datetime' in dtype_str or 'timestamp' in dtype_str:
        return DateTime()
    elif 'object' in dtype_str or 'string' in dtype_str:
        # Check if it's likely to be long text
        return Text()
    else:
        # Default to String for unknown types
        return String(255)


async def create_dynamic_table(
    db: AsyncSession,
    table_name: str,
    df: pd.DataFrame,
    if_exists: str = 'fail'
) -> bool:
    """
    Create a dynamic table from a DataFrame schema.
    
    Args:
        db: Database session
        table_name: Name of the table to create (should already be sanitized if it's a dynamic table name)
        df: DataFrame with the schema to use
        if_exists: What to do if table exists ('fail', 'replace', 'append')
        
    Returns:
        True if table was created, False otherwise
    """
    # If table_name already starts with __, it's a dynamic table name and already sanitized
    # Otherwise, sanitize it (for backward compatibility)
    if table_name.startswith('__'):
        sanitized_table_name = table_name.lower()  # Just lowercase, preserve structure
    else:
        sanitized_table_name = sanitize_table_name(table_name)
    
    # Check if table exists (use existing transaction, don't start a new one)
    result = await db.execute(
        text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = :table_name
            )
        """),
        {"table_name": sanitized_table_name}
    )
    table_exists = result.scalar()
    
    if table_exists:
        if if_exists == 'fail':
            raise ValueError(f"Table {sanitized_table_name} already exists. Please choose a different table name.")
        elif if_exists == 'replace':
            await db.execute(text(f'DROP TABLE IF EXISTS "{sanitized_table_name}" CASCADE'))
        elif if_exists == 'append':
            # Table exists, we'll append later
            return True
    
    # Build CREATE TABLE SQL statement
    column_definitions = []
    
    for col_name in df.columns:
        sanitized_col_name = sanitize_column_name(col_name)
        pandas_dtype = df[col_name].dtype
        
        # Check if column contains JSON/dict data
        if is_json_column(df[col_name]):
            type_str = "JSONB"
        else:
            sql_type = pandas_dtype_to_sqlalchemy(pandas_dtype)
            
            # Convert SQLAlchemy type to PostgreSQL type string
            if isinstance(sql_type, Integer):
                type_str = "INTEGER"
            elif isinstance(sql_type, Float):
                type_str = "DOUBLE PRECISION"
            elif isinstance(sql_type, Boolean):
                type_str = "BOOLEAN"
            elif isinstance(sql_type, DateTime):
                type_str = "TIMESTAMP"
            elif isinstance(sql_type, Text):
                type_str = "TEXT"
            else:
                type_str = "TEXT"  # Default to TEXT for String and unknown types
        
        column_definitions.append(f'"{sanitized_col_name}" {type_str}')
    
    # Create table using raw SQL (use existing transaction)
    create_table_sql = f'''
        CREATE TABLE "{sanitized_table_name}" (
            {', '.join(column_definitions)}
        )
    '''
    
    await db.execute(text(create_table_sql))
    
    logger.info(f"Created dynamic table: {sanitized_table_name} with {len(column_definitions)} columns")
    return True


async def insert_dataframe_to_table(
    db: AsyncSession,
    table_name: str,
    df: pd.DataFrame,
    if_exists: str = 'append',
    chunk_size: int = 1000
) -> int:
    """
    Insert DataFrame data into a table using bulk insert.
    
    Args:
        db: Database session
        table_name: Name of the table
        df: DataFrame with data to insert
        if_exists: What to do if data exists ('fail', 'replace', 'append')
        chunk_size: Number of rows to insert per chunk
        
    Returns:
        Number of rows inserted
    """
    # If table_name already starts with __, it's a dynamic table name and already sanitized
    # Otherwise, sanitize it (for backward compatibility)
    if table_name.startswith('__'):
        sanitized_table_name = table_name.lower()  # Just lowercase, preserve structure
    else:
        sanitized_table_name = sanitize_table_name(table_name)
    
    # Identify JSON columns before renaming
    json_columns = set()
    for col in df.columns:
        if is_json_column(df[col]):
            sanitized_col = sanitize_column_name(col)
            json_columns.add(sanitized_col)
    
    # Sanitize column names in DataFrame
    df_renamed = df.copy()
    column_mapping = {}
    for col in df.columns:
        sanitized_col = sanitize_column_name(col)
        if col != sanitized_col:
            column_mapping[col] = sanitized_col
            df_renamed = df_renamed.rename(columns={col: sanitized_col})
    
    # Serialize JSON columns for JSONB storage
    for col in df_renamed.columns:
        if col in json_columns:
            # Convert dict/list to JSON string for JSONB columns
            def serialize_json(value):
                if pd.isna(value):
                    return None
                if isinstance(value, (dict, list)):
                    return json.dumps(value)
                elif isinstance(value, str):
                    # If already a JSON string, validate it
                    try:
                        json.loads(value)  # Validate JSON
                        return value
                    except (json.JSONDecodeError, TypeError):
                        return json.dumps(value)
                else:
                    return json.dumps(value)
            
            df_renamed[col] = df_renamed[col].apply(serialize_json)
    
    # Replace NaN with None for proper NULL handling
    df_renamed = df_renamed.where(pd.notna(df_renamed), None)
    
    # Use pandas to_sql for bulk insert (more efficient)
    # We need to use sync connection for pandas, but get it from async session's bind
    from sqlalchemy import create_engine
    
    settings = get_settings()
    # Create sync engine from database URL (pandas requires sync connection)
    sync_engine = create_engine(settings.database_url, pool_pre_ping=True)
    
    rows_inserted = df_renamed.to_sql(
        name=sanitized_table_name,
        con=sync_engine,
        if_exists=if_exists,
        index=False,
        method='multi',
        chunksize=chunk_size
    )
    
    sync_engine.dispose()
    
    logger.info(f"Inserted {rows_inserted} rows into {sanitized_table_name}")
    return rows_inserted


async def drop_dynamic_table(db: AsyncSession, table_name: str) -> bool:
    """
    Drop a dynamic table.
    
    Args:
        db: Database session
        table_name: Name of the table to drop (should already be sanitized if it's a dynamic table name)
        
    Returns:
        True if table was dropped, False otherwise
    """
    # If table_name already starts with __, it's a dynamic table name and already sanitized
    # Otherwise, sanitize it (for backward compatibility)
    if table_name.startswith('__'):
        sanitized_table_name = table_name.lower()  # Just lowercase, preserve structure
    else:
        sanitized_table_name = sanitize_table_name(table_name)
    
    try:
        # Use existing transaction, don't start a new one
        await db.execute(text(f'DROP TABLE IF EXISTS "{sanitized_table_name}" CASCADE'))
        logger.info(f"Dropped dynamic table: {sanitized_table_name}")
        return True
    except Exception as e:
        logger.error(f"Error dropping table {sanitized_table_name}: {e}")
        return False


def generate_dynamic_table_name(user_id: str, table_name: str) -> str:
    """
    Generate dynamic table name in format: __user_{user_id}_{table_name}
    
    Args:
        user_id: User ID
        table_name: User-provided table name
        
    Returns:
        Full dynamic table name
    """
    sanitized_table_name = sanitize_table_name(table_name)
    # Sanitize user_id as well
    sanitized_user_id = sanitize_table_name(user_id)
    
    dynamic_name = f"__user_{sanitized_user_id}_{sanitized_table_name}"
    
    # Ensure total length doesn't exceed PostgreSQL limit
    if len(dynamic_name) > 63:
        # Truncate table_name part if needed
        max_table_len = 63 - len(f"__user_{sanitized_user_id}_")
        if max_table_len > 0:
            sanitized_table_name = sanitized_table_name[:max_table_len]
            dynamic_name = f"__user_{sanitized_user_id}_{sanitized_table_name}"
        else:
            raise ValueError(f"User ID too long for dynamic table name: {user_id}")
    
    return dynamic_name

