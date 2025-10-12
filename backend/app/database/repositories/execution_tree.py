"""
Repository for execution tree operations.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models.execution_tree import (
    ExecutionTreeSession,
    ExecutionTreeNode,
    ExecutionNodeType,
    ExecutionNodeStatus,
)
from app.utils.logging import get_logger

logger = get_logger("execution_tree_repository")


class ExecutionTreeRepository:
    """Repository for execution tree database operations."""

    @staticmethod
    async def create_session(
        db: AsyncSession,
        session_id: str,
        query: str,
        user_id: Optional[str] = None,
        message_id: Optional[str] = None,
        extra_metadata: Optional[Dict[str, Any]] = None,
    ) -> ExecutionTreeSession:
        """Create a new execution tree session."""
        tree_session = ExecutionTreeSession(
            session_id=session_id,
            message_id=message_id,
            user_id=user_id,
            query=query,
            status=ExecutionNodeStatus.RUNNING,
            started_at=datetime.utcnow(),
            extra_metadata=extra_metadata or {},
        )
        db.add(tree_session)
        await db.flush()
        return tree_session

    @staticmethod
    async def complete_session(
        db: AsyncSession,
        tree_session_id: int,
        result_summary: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> Optional[ExecutionTreeSession]:
        """Complete an execution tree session."""
        result = await db.execute(
            select(ExecutionTreeSession).where(ExecutionTreeSession.id == tree_session_id)
        )
        tree_session = result.scalar_one_or_none()
        
        if tree_session:
            tree_session.completed_at = datetime.utcnow()
            tree_session.status = ExecutionNodeStatus.FAILED if error_message else ExecutionNodeStatus.COMPLETED
            tree_session.result_summary = result_summary
            tree_session.error_message = error_message
            
            # Calculate duration
            if tree_session.started_at:
                duration = (tree_session.completed_at - tree_session.started_at).total_seconds() * 1000
                tree_session.duration_ms = duration
            
            await db.flush()
        
        return tree_session

    @staticmethod
    async def add_node(
        db: AsyncSession,
        tree_session_id: int,
        node_id: str,
        node_type: ExecutionNodeType,
        name: str,
        parent_node_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        tool_name: Optional[str] = None,
        tool_args: Optional[Dict[str, Any]] = None,
        input_summary: Optional[str] = None,
        extra_metadata: Optional[Dict[str, Any]] = None,
    ) -> ExecutionTreeNode:
        """Add a node to the execution tree."""
        node = ExecutionTreeNode(
            tree_session_id=tree_session_id,
            node_id=node_id,
            parent_node_id=parent_node_id,
            node_type=node_type,
            name=name,
            status=ExecutionNodeStatus.RUNNING,
            agent_id=agent_id,
            tool_name=tool_name,
            tool_args=tool_args,
            input_summary=input_summary,
            started_at=datetime.utcnow(),
            extra_metadata=extra_metadata or {},
        )
        db.add(node)
        await db.flush()
        return node

    @staticmethod
    async def complete_node(
        db: AsyncSession,
        tree_session_id: int,
        node_id: str,
        output_summary: Optional[str] = None,
        tool_result: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        prompt_tokens: Optional[int] = None,
        completion_tokens: Optional[int] = None,
        total_tokens: Optional[int] = None,
    ) -> Optional[ExecutionTreeNode]:
        """Complete a node in the execution tree."""
        result = await db.execute(
            select(ExecutionTreeNode).where(
                ExecutionTreeNode.tree_session_id == tree_session_id,
                ExecutionTreeNode.node_id == node_id,
            )
        )
        node = result.scalar_one_or_none()
        
        if node:
            node.completed_at = datetime.utcnow()
            node.status = ExecutionNodeStatus.FAILED if error_message else ExecutionNodeStatus.COMPLETED
            node.output_summary = output_summary
            node.tool_result = tool_result
            node.error_message = error_message
            node.prompt_tokens = prompt_tokens
            node.completion_tokens = completion_tokens
            node.total_tokens = total_tokens
            
            # Calculate duration
            if node.started_at:
                duration = (node.completed_at - node.started_at).total_seconds() * 1000
                node.duration_ms = duration
            
            await db.flush()
        
        return node

    @staticmethod
    async def get_session_by_id(
        db: AsyncSession,
        tree_session_id: int,
        include_nodes: bool = True,
    ) -> Optional[ExecutionTreeSession]:
        """Get an execution tree session by ID."""
        query = select(ExecutionTreeSession).where(ExecutionTreeSession.id == tree_session_id)
        
        if include_nodes:
            query = query.options(selectinload(ExecutionTreeSession.nodes))
        
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_sessions_by_chat_session(
        db: AsyncSession,
        session_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> List[ExecutionTreeSession]:
        """Get all execution tree sessions for a chat session."""
        query = (
            select(ExecutionTreeSession)
            .where(ExecutionTreeSession.session_id == session_id)
            .options(selectinload(ExecutionTreeSession.nodes))
            .order_by(desc(ExecutionTreeSession.created_at))
            .limit(limit)
            .offset(offset)
        )
        
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_session_by_message_id(
        db: AsyncSession,
        message_id: str,
        include_nodes: bool = True,
    ) -> Optional[ExecutionTreeSession]:
        """Get an execution tree session by message ID."""
        query = select(ExecutionTreeSession).where(ExecutionTreeSession.message_id == message_id)
        
        if include_nodes:
            query = query.options(selectinload(ExecutionTreeSession.nodes))
        
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_sessions_by_user(
        db: AsyncSession,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> List[ExecutionTreeSession]:
        """Get all execution tree sessions for a user."""
        query = (
            select(ExecutionTreeSession)
            .where(ExecutionTreeSession.user_id == user_id)
            .options(selectinload(ExecutionTreeSession.nodes))
            .order_by(desc(ExecutionTreeSession.created_at))
            .limit(limit)
            .offset(offset)
        )
        
        result = await db.execute(query)
        return list(result.scalars().all())

