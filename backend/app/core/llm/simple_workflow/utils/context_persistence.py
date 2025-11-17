"""
Context State Persistence Utilities

Handles serialization and deserialization of LlamaIndex Context state
for persistence across conversation turns.
"""

import json
from typing import Any, Dict, Optional
from datetime import datetime

import pandas as pd
import numpy as np
from llama_index.core.workflow import Context
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.repositories.chat_session import ChatSessionRepository
from app.utils.logging import get_logger

logger = get_logger(__name__)


def _serialize_value(value: Any) -> Any:
    """
    Recursively serialize a value to be JSON-compatible.
    
    Handles:
    - pandas DataFrames (store metadata only for large ones)
    - numpy types
    - datetime objects
    - nested dicts and lists
    """
    if value is None:
        return None
    
    # Handle pandas DataFrame
    if isinstance(value, pd.DataFrame):
        # For large DataFrames, store only metadata to avoid bloat
        if len(value) > 1000:
            return {
                "_type": "dataframe_metadata",
                "shape": value.shape,
                "columns": list(value.columns),
                "dtypes": {col: str(dtype) for col, dtype in value.dtypes.items()},
                "sample": value.head(5).to_dict(orient="records"),
                "note": "Large DataFrame - only metadata stored"
            }
        else:
            # For smaller DataFrames, store full data
            return {
                "_type": "dataframe",
                "data": value.to_dict(orient="records"),
                "columns": list(value.columns),
                "dtypes": {col: str(dtype) for col, dtype in value.dtypes.items()}
            }
    
    # Handle pandas Series
    if isinstance(value, pd.Series):
        return {
            "_type": "series",
            "data": value.to_dict(),
            "name": value.name,
            "dtype": str(value.dtype)
        }
    
    # Handle numpy types
    if isinstance(value, (np.integer, np.floating)):
        return value.item()
    
    if isinstance(value, np.ndarray):
        return value.tolist()
    
    # Handle datetime
    if isinstance(value, datetime):
        return {"_type": "datetime", "value": value.isoformat()}
    
    # Handle dict recursively
    if isinstance(value, dict):
        return {k: _serialize_value(v) for k, v in value.items()}
    
    # Handle list/tuple recursively
    if isinstance(value, (list, tuple)):
        return [_serialize_value(item) for item in value]
    
    # Handle basic types
    if isinstance(value, (str, int, float, bool)):
        return value
    
    # Fallback: convert to string
    try:
        return str(value)
    except Exception as e:
        logger.warning(f"Failed to serialize value of type {type(value)}: {e}")
        return None


def _deserialize_value(value: Any) -> Any:
    """
    Recursively deserialize a value from JSON-compatible format.
    
    Handles special types marked with _type field.
    """
    if value is None:
        return None
    
    # Handle special types
    if isinstance(value, dict) and "_type" in value:
        type_marker = value["_type"]
        
        if type_marker == "dataframe":
            df = pd.DataFrame(value["data"])
            # Restore dtypes if possible
            for col, dtype_str in value.get("dtypes", {}).items():
                try:
                    if col in df.columns:
                        df[col] = df[col].astype(dtype_str)
                except Exception:
                    pass  # Keep original dtype if conversion fails
            return df
        
        elif type_marker == "dataframe_metadata":
            # For metadata-only DataFrames, return None (data not available)
            # The workflow will need to reload if needed
            logger.info(f"Skipping large DataFrame restoration (shape: {value['shape']})")
            return None
        
        elif type_marker == "series":
            return pd.Series(value["data"], name=value.get("name"))
        
        elif type_marker == "datetime":
            return datetime.fromisoformat(value["value"])
    
    # Handle dict recursively
    if isinstance(value, dict):
        return {k: _deserialize_value(v) for k, v in value.items()}
    
    # Handle list recursively
    if isinstance(value, list):
        return [_deserialize_value(item) for item in value]
    
    # Return as-is for basic types
    return value


async def serialize_context_state(ctx: Context) -> dict:
    """
    Serialize Context state to a JSON-compatible dictionary.
    
    Args:
        ctx: LlamaIndex Context object
        
    Returns:
        dict: Serialized state that can be stored as JSON
    """
    try:
        # Get the full state from context
        state = await ctx.store.get("state", {})
        
        # Serialize the state
        serialized = _serialize_value(state)
        
        logger.info(f"Serialized context state with {len(serialized)} top-level keys")
        return serialized
    
    except Exception as e:
        logger.error(f"Failed to serialize context state: {e}", exc_info=True)
        return {}


async def deserialize_context_state(ctx: Context, state_dict: dict) -> None:
    """
    Deserialize and restore Context state from a dictionary.
    
    Args:
        ctx: LlamaIndex Context object to restore state into
        state_dict: Serialized state dictionary
    """
    try:
        if not state_dict:
            logger.info("No context state to restore")
            return
        
        # Deserialize the state
        deserialized = _deserialize_value(state_dict)
        
        # Restore to context
        await ctx.store.set("state", deserialized)
        
        logger.info(f"Restored context state with {len(deserialized)} top-level keys")
    
    except Exception as e:
        logger.error(f"Failed to deserialize context state: {e}", exc_info=True)
        # Don't raise - allow workflow to continue without restored state


async def save_context_to_session(
    session_id: str, 
    ctx: Context, 
    db: AsyncSession
) -> bool:
    """
    Save Context state to session metadata in database.
    
    Args:
        session_id: Chat session ID
        ctx: Context object to save
        db: Database session
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Serialize context state
        serialized_state = await serialize_context_state(ctx)
        
        if not serialized_state:
            logger.warning("No context state to save")
            return False
        
        # Get current session
        session = await ChatSessionRepository.get_by_id(db, session_id)
        if not session:
            logger.error(f"Session {session_id} not found")
            return False
        
        # Update extra_metadata with context state (convert to dict if needed)
        current_metadata = dict(session.extra_metadata) if session.extra_metadata else {}
        current_metadata["context_state"] = serialized_state
        current_metadata["context_saved_at"] = datetime.utcnow().isoformat()
        
        # Save to database
        await ChatSessionRepository.update(
            db, 
            session_id, 
            extra_metadata=current_metadata
        )
        
        logger.info(f"Saved context state to session {session_id}")
        return True
    
    except Exception as e:
        logger.error(f"Failed to save context to session: {e}", exc_info=True)
        return False


async def load_context_from_session(
    session_id: str, 
    ctx: Context, 
    db: AsyncSession
) -> bool:
    """
    Load Context state from session metadata in database.
    
    Args:
        session_id: Chat session ID
        ctx: Context object to restore state into
        db: Database session
        
    Returns:
        bool: True if state was loaded, False otherwise
    """
    try:
        # Get session
        session = await ChatSessionRepository.get_by_id(db, session_id)
        if not session:
            logger.info(f"Session {session_id} not found - starting fresh")
            return False
        
        # Get context state from extra_metadata (convert to dict if needed)
        metadata = dict(session.extra_metadata) if session.extra_metadata else {}
        context_state = metadata.get("context_state")
        
        if not context_state:
            logger.info(f"No saved context state for session {session_id}")
            return False
        
        # Restore context state
        await deserialize_context_state(ctx, context_state)
        
        saved_at = metadata.get("context_saved_at", "unknown")
        logger.info(f"Loaded context state from session {session_id} (saved at {saved_at})")
        return True
    
    except Exception as e:
        logger.error(f"Failed to load context from session: {e}", exc_info=True)
        return False

