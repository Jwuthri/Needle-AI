"""
Chat session repository for NeedleAi.
"""

from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import and_, desc, func
from sqlalchemy.orm import Session, joinedload, selectinload

from ...utils.logging import get_logger
from ..models.chat_message import ChatMessage
from ..models.chat_session import ChatSession

logger = get_logger("chat_session_repository")


class ChatSessionRepository:
    """Repository for ChatSession model operations."""

    @staticmethod
    def create(db: Session, user_id: str = None, **kwargs) -> ChatSession:
        """Create a new chat session."""
        session = ChatSession(user_id=user_id, **kwargs)
        db.add(session)
        db.commit()
        db.refresh(session)
        logger.info(f"Created chat session: {session.id}")
        return session

    @staticmethod
    def get_by_id(
        db: Session,
        session_id: str,
        include_user: bool = False,
        include_messages: bool = False
    ) -> Optional[ChatSession]:
        """Get session by ID with optional eager loading."""
        query = db.query(ChatSession).filter(ChatSession.id == session_id)

        # Eager load relationships to prevent N+1 queries
        if include_user:
            query = query.options(joinedload(ChatSession.user))

        if include_messages:
            query = query.options(selectinload(ChatSession.messages))

        return query.first()

    @staticmethod
    def get_by_ids(
        db: Session,
        session_ids: List[str],
        include_user: bool = False,
        include_messages: bool = False
    ) -> List[ChatSession]:
        """Bulk get sessions by IDs to prevent N+1 queries."""
        query = db.query(ChatSession).filter(ChatSession.id.in_(session_ids))

        # Eager load relationships
        if include_user:
            query = query.options(joinedload(ChatSession.user))

        if include_messages:
            query = query.options(selectinload(ChatSession.messages))

        return query.all()

    @staticmethod
    def get_user_sessions(
        db: Session,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
        active_only: bool = True,
        include_user: bool = False,
        include_messages: bool = False
    ) -> List[ChatSession]:
        """Get user's chat sessions with optional eager loading to prevent N+1 queries."""
        query = db.query(ChatSession).filter(ChatSession.user_id == user_id)

        if active_only:
            query = query.filter(ChatSession.is_active == True)

        # Eager load relationships to prevent N+1 queries
        if include_user:
            query = query.options(joinedload(ChatSession.user))

        if include_messages:
            query = query.options(selectinload(ChatSession.messages))

        return query.order_by(desc(ChatSession.updated_at)).offset(offset).limit(limit).all()

    @staticmethod
    def get_all(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        active_only: bool = False
    ) -> List[ChatSession]:
        """Get all sessions with pagination."""
        query = db.query(ChatSession)

        if active_only:
            query = query.filter(ChatSession.is_active == True)

        return query.order_by(desc(ChatSession.created_at)).offset(skip).limit(limit).all()

    @staticmethod
    def update(db: Session, session_id: str, **kwargs) -> Optional[ChatSession]:
        """Update chat session."""
        session = ChatSessionRepository.get_by_id(db, session_id)
        if not session:
            return None

        for key, value in kwargs.items():
            if hasattr(session, key):
                setattr(session, key, value)

        session.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(session)
        return session

    @staticmethod
    def get_sessions_with_message_counts(
        db: Session,
        user_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[tuple]:
        """
        Get sessions with message counts in a single query to prevent N+1.
        Returns tuples of (ChatSession, message_count).
        """
        query = db.query(
            ChatSession,
            func.count(ChatMessage.id).label('message_count')
        ).outerjoin(ChatMessage)

        if user_id:
            query = query.filter(ChatSession.user_id == user_id)

        query = query.group_by(ChatSession.id)
        query = query.order_by(desc(ChatSession.updated_at))
        query = query.offset(offset).limit(limit)

        return query.all()

    @staticmethod
    def get_popular_sessions(
        db: Session,
        days: int = 30,
        limit: int = 10
    ) -> List[tuple]:
        """
        Get most popular sessions by message count in the last N days.
        Returns tuples of (ChatSession, message_count).
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        query = db.query(
            ChatSession,
            func.count(ChatMessage.id).label('message_count')
        ).join(ChatMessage).filter(
            ChatMessage.created_at >= cutoff_date,
            ChatSession.is_active == True
        ).group_by(ChatSession.id).order_by(
            desc(func.count(ChatMessage.id))
        ).limit(limit)

        return query.all()

    @staticmethod
    def increment_message_count(db: Session, session_id: str, tokens: int = 0):
        """Increment session message and token counts."""
        session = ChatSessionRepository.get_by_id(db, session_id)
        if session:
            session.message_count += 1
            session.total_tokens += tokens
            session.updated_at = datetime.utcnow()
            session.last_message_at = datetime.utcnow()
            db.commit()

    @staticmethod
    def deactivate(db: Session, session_id: str) -> bool:
        """Deactivate a chat session."""
        session = ChatSessionRepository.get_by_id(db, session_id)
        if session:
            session.is_active = False
            session.updated_at = datetime.utcnow()
            db.commit()
            return True
        return False

    @staticmethod
    def delete(db: Session, session_id: str) -> bool:
        """Hard delete a chat session and its messages."""
        session = ChatSessionRepository.get_by_id(db, session_id)
        if session:
            # Delete associated messages first
            db.query(ChatMessage).filter(ChatMessage.session_id == session_id).delete()
            # Delete session
            db.delete(session)
            db.commit()
            logger.info(f"Deleted chat session: {session_id}")
            return True
        return False

    @staticmethod
    def cleanup_old_sessions(db: Session, days_old: int = 30) -> int:
        """Clean up old inactive sessions."""
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)

        # First, get session IDs to delete
        old_sessions = db.query(ChatSession).filter(
            and_(
                ChatSession.updated_at < cutoff_date,
                ChatSession.is_active == False
            )
        ).all()

        session_ids = [s.id for s in old_sessions]

        if not session_ids:
            return 0

        # Delete messages first (due to foreign key constraints)
        deleted_messages = db.query(ChatMessage).filter(
            ChatMessage.session_id.in_(session_ids)
        ).delete(synchronize_session=False)

        # Delete sessions
        deleted_sessions = db.query(ChatSession).filter(
            ChatSession.id.in_(session_ids)
        ).delete(synchronize_session=False)

        db.commit()

        logger.info(f"Cleaned up {deleted_sessions} old sessions and {deleted_messages} messages")
        return deleted_sessions

    @staticmethod
    def search_sessions(
        db: Session,
        user_id: str = None,
        search_term: str = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[ChatSession]:
        """Search sessions by title or content."""
        query = db.query(ChatSession)

        if user_id:
            query = query.filter(ChatSession.user_id == user_id)

        if search_term:
            query = query.filter(ChatSession.title.ilike(f"%{search_term}%"))

        return query.order_by(desc(ChatSession.updated_at)).offset(skip).limit(limit).all()
