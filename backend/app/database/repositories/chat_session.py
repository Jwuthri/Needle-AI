"""
Chat session repository for NeedleAi.
"""

from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import and_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload, selectinload

from ...utils.logging import get_logger
from ..models.chat_message import ChatMessage
from ..models.chat_session import ChatSession

logger = get_logger("chat_session_repository")


class ChatSessionRepository:
    """Repository for ChatSession model operations."""

    @staticmethod
    async def create(db: AsyncSession, user_id: str = None, **kwargs) -> ChatSession:
        """Create a new chat session."""
        session = ChatSession(user_id=user_id, **kwargs)
        db.add(session)
        await db.flush()
        await db.refresh(session)
        logger.info(f"Created chat session: {session.id}")
        return session

    @staticmethod
    async def get_by_id(
        db: AsyncSession,
        session_id: str,
        include_user: bool = False,
        include_messages: bool = False
    ) -> Optional[ChatSession]:
        """Get session by ID with optional eager loading."""
        query = select(ChatSession).filter(ChatSession.id == session_id)

        # Eager load relationships to prevent N+1 queries
        if include_user:
            query = query.options(joinedload(ChatSession.user))

        if include_messages:
            query = query.options(selectinload(ChatSession.messages))

        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_ids(
        db: AsyncSession,
        session_ids: List[str],
        include_user: bool = False,
        include_messages: bool = False
    ) -> List[ChatSession]:
        """Bulk get sessions by IDs to prevent N+1 queries."""
        query = select(ChatSession).filter(ChatSession.id.in_(session_ids))

        # Eager load relationships
        if include_user:
            query = query.options(joinedload(ChatSession.user))

        if include_messages:
            query = query.options(selectinload(ChatSession.messages))

        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_user_sessions(
        db: AsyncSession,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
        active_only: bool = True,
        include_user: bool = False,
        include_messages: bool = False
    ) -> List[ChatSession]:
        """Get user's chat sessions with optional eager loading to prevent N+1 queries."""
        query = select(ChatSession).filter(ChatSession.user_id == user_id)

        if active_only:
            query = query.filter(ChatSession.is_active == True)

        # Eager load relationships to prevent N+1 queries
        if include_user:
            query = query.options(joinedload(ChatSession.user))

        if include_messages:
            query = query.options(selectinload(ChatSession.messages))

        query = query.order_by(desc(ChatSession.updated_at)).offset(offset).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_all(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        active_only: bool = False
    ) -> List[ChatSession]:
        """Get all sessions with pagination."""
        query = select(ChatSession)

        if active_only:
            query = query.filter(ChatSession.is_active == True)

        query = query.order_by(desc(ChatSession.created_at)).offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def update(db: AsyncSession, session_id: str, **kwargs) -> Optional[ChatSession]:
        """Update chat session."""
        session = await ChatSessionRepository.get_by_id(db, session_id)
        if not session:
            return None

        for key, value in kwargs.items():
            if hasattr(session, key):
                setattr(session, key, value)

        session.updated_at = datetime.utcnow()
        await db.flush()
        await db.refresh(session)
        return session

    @staticmethod
    async def get_sessions_with_message_counts(
        db: AsyncSession,
        user_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[tuple]:
        """
        Get sessions with message counts in a single query to prevent N+1.
        Returns tuples of (ChatSession, message_count).
        """
        query = select(
            ChatSession,
            func.count(ChatMessage.id).label('message_count')
        ).outerjoin(ChatMessage)

        if user_id:
            query = query.filter(ChatSession.user_id == user_id)

        query = query.group_by(ChatSession.id)
        query = query.order_by(desc(ChatSession.updated_at))
        query = query.offset(offset).limit(limit)

        result = await db.execute(query)
        return list(result.all())

    @staticmethod
    async def get_popular_sessions(
        db: AsyncSession,
        days: int = 30,
        limit: int = 10
    ) -> List[tuple]:
        """
        Get most popular sessions by message count in the last N days.
        Returns tuples of (ChatSession, message_count).
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        query = select(
            ChatSession,
            func.count(ChatMessage.id).label('message_count')
        ).join(ChatMessage).filter(
            ChatMessage.created_at >= cutoff_date,
            ChatSession.is_active == True
        ).group_by(ChatSession.id).order_by(
            desc(func.count(ChatMessage.id))
        ).limit(limit)

        result = await db.execute(query)
        return list(result.all())

    @staticmethod
    async def increment_message_count(db: AsyncSession, session_id: str, tokens: int = 0):
        """Increment session message and token counts."""
        session = await ChatSessionRepository.get_by_id(db, session_id)
        if session:
            session.message_count += 1
            session.total_tokens += tokens
            session.updated_at = datetime.utcnow()
            session.last_message_at = datetime.utcnow()
            await db.flush()

    @staticmethod
    async def deactivate(db: AsyncSession, session_id: str) -> bool:
        """Deactivate a chat session."""
        session = await ChatSessionRepository.get_by_id(db, session_id)
        if session:
            session.is_active = False
            session.updated_at = datetime.utcnow()
            await db.flush()
            return True
        return False

    @staticmethod
    async def delete(db: AsyncSession, session_id: str) -> bool:
        """Hard delete a chat session and its messages."""
        session = await ChatSessionRepository.get_by_id(db, session_id)
        if session:
            # Delete associated messages first
            delete_msgs = await db.execute(
                select(ChatMessage).filter(ChatMessage.session_id == session_id)
            )
            messages = delete_msgs.scalars().all()
            for msg in messages:
                await db.delete(msg)
            
            # Delete session
            await db.delete(session)
            await db.flush()
            logger.info(f"Deleted chat session: {session_id}")
            return True
        return False

    @staticmethod
    async def cleanup_old_sessions(db: AsyncSession, days_old: int = 30) -> int:
        """Clean up old inactive sessions."""
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)

        # First, get session IDs to delete
        result = await db.execute(
            select(ChatSession).filter(
                and_(
                    ChatSession.updated_at < cutoff_date,
                    ChatSession.is_active == False
                )
            )
        )
        old_sessions = result.scalars().all()
        session_ids = [s.id for s in old_sessions]

        if not session_ids:
            return 0

        # Delete messages first (due to foreign key constraints)
        msg_result = await db.execute(
            select(ChatMessage).filter(ChatMessage.session_id.in_(session_ids))
        )
        messages = msg_result.scalars().all()
        for msg in messages:
            await db.delete(msg)
        deleted_messages = len(messages)

        # Delete sessions
        for session in old_sessions:
            await db.delete(session)
        deleted_sessions = len(old_sessions)

        await db.flush()

        logger.info(f"Cleaned up {deleted_sessions} old sessions and {deleted_messages} messages")
        return deleted_sessions

    @staticmethod
    async def search_sessions(
        db: AsyncSession,
        user_id: str = None,
        search_term: str = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[ChatSession]:
        """Search sessions by title or content."""
        query = select(ChatSession)

        if user_id:
            query = query.filter(ChatSession.user_id == user_id)

        if search_term:
            query = query.filter(ChatSession.title.ilike(f"%{search_term}%"))

        query = query.order_by(desc(ChatSession.updated_at)).offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())
