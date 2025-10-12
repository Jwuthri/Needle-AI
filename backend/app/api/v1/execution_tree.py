"""
Execution Tree API endpoints for querying execution history.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.response_wrapper import success_response
from app.database.repositories.execution_tree import ExecutionTreeRepository
from app.models.execution_tree import (
    ExecutionTreeSessionResponse,
    ExecutionTreeListResponse,
)
from app.utils.logging import get_logger

logger = get_logger("execution_tree_api")

router = APIRouter(prefix="/execution-trees", tags=["Execution Trees"])


@router.get("/{tree_id}", response_model=ExecutionTreeSessionResponse)
async def get_execution_tree(
    tree_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific execution tree by ID.
    
    Returns the full execution tree including all nodes/steps.
    """
    tree = await ExecutionTreeRepository.get_session_by_id(db, tree_id, include_nodes=True)
    
    if not tree:
        raise HTTPException(status_code=404, detail="Execution tree not found")
    
    return tree


@router.get("/session/{session_id}", response_model=ExecutionTreeListResponse)
async def get_execution_trees_by_session(
    session_id: str,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all execution trees for a chat session.
    
    Returns a paginated list of execution trees.
    """
    trees = await ExecutionTreeRepository.get_sessions_by_chat_session(
        db, session_id, limit=limit, offset=offset
    )
    
    return ExecutionTreeListResponse(
        trees=trees,
        total=len(trees),
        limit=limit,
        offset=offset,
    )


@router.get("/message/{message_id}", response_model=ExecutionTreeSessionResponse)
async def get_execution_tree_by_message(
    message_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get the execution tree for a specific message.
    
    Returns the full execution tree including all nodes/steps.
    """
    tree = await ExecutionTreeRepository.get_session_by_message_id(
        db, message_id, include_nodes=True
    )
    
    if not tree:
        raise HTTPException(status_code=404, detail="Execution tree not found for message")
    
    return tree


@router.get("/user/{user_id}", response_model=ExecutionTreeListResponse)
async def get_execution_trees_by_user(
    user_id: str,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all execution trees for a user.
    
    Returns a paginated list of execution trees.
    """
    trees = await ExecutionTreeRepository.get_sessions_by_user(
        db, user_id, limit=limit, offset=offset
    )
    
    return ExecutionTreeListResponse(
        trees=trees,
        total=len(trees),
        limit=limit,
        offset=offset,
    )

