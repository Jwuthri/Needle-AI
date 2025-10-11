"""
Chat message repository for NeedleAi.
"""

from typing import List, Optional

from sqlalchemy import asc, desc
from sqlalchemy.orm import Session

from ...utils.logging import get_logger
from ..models.chat_message import ChatMessage, MessageRoleEnum

logger = get_logger("chat_message_repository")


class ChatMessageRepository:
    """Repository for ChatMessage model operations."""

    @staticmethod
    def create(
        db: Session,
        session_id: str,
        content: str,
        role: MessageRoleEnum,
        **kwargs
    ) -> ChatMessage:
        """Create a new chat message."""
        message = ChatMessage(
            session_id=session_id,
            content=content,
            role=role,
            **kwargs
        )
        db.add(message)
        db.commit()
        db.refresh(message)

        # Import here to avoid circular imports
        from .chat_session import ChatSessionRepository
        ChatSessionRepository.increment_message_count(db, session_id, kwargs.get('token_count', 0))

        logger.info(f"Created message: {message.id} in session: {session_id}")
        return message

    @staticmethod
    def get_by_id(db: Session, message_id: str) -> Optional[ChatMessage]:
        """Get message by ID."""
        return db.query(ChatMessage).filter(ChatMessage.id == message_id).first()

    @staticmethod
    def get_session_messages(
        db: Session,
        session_id: str,
        limit: int = 100,
        offset: int = 0,
        role: Optional[MessageRoleEnum] = None
    ) -> List[ChatMessage]:
        """Get messages for a session."""
        query = db.query(ChatMessage).filter(ChatMessage.session_id == session_id)

        if role:
            query = query.filter(ChatMessage.role == role)

        return (
            query
            .order_by(asc(ChatMessage.created_at))
            .offset(offset)
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_recent_messages(
        db: Session,
        session_id: str,
        limit: int = 20
    ) -> List[ChatMessage]:
        """Get recent messages for context."""
        return (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(desc(ChatMessage.created_at))
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_all(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        role: Optional[MessageRoleEnum] = None
    ) -> List[ChatMessage]:
        """Get all messages with pagination."""
        query = db.query(ChatMessage)

        if role:
            query = query.filter(ChatMessage.role == role)

        return query.order_by(desc(ChatMessage.created_at)).offset(skip).limit(limit).all()

    @staticmethod
    def count_session_messages(db: Session, session_id: str) -> int:
        """Count messages in a session."""
        return db.query(ChatMessage).filter(ChatMessage.session_id == session_id).count()

    @staticmethod
    def count_user_messages(db: Session, user_id: str) -> int:
        """Count messages for a user across all sessions."""
        from ..models.chat_session import ChatSession
        return (
            db.query(ChatMessage)
            .join(ChatSession, ChatMessage.session_id == ChatSession.id)
            .filter(ChatSession.user_id == user_id)
            .count()
        )

    @staticmethod
    def update(db: Session, message_id: str, **kwargs) -> Optional[ChatMessage]:
        """Update a chat message."""
        message = ChatMessageRepository.get_by_id(db, message_id)
        if not message:
            return None

        for key, value in kwargs.items():
            if hasattr(message, key):
                setattr(message, key, value)

        db.commit()
        db.refresh(message)
        return message

    @staticmethod
    def delete(db: Session, message_id: str) -> bool:
        """Delete a message."""
        message = ChatMessageRepository.get_by_id(db, message_id)
        if message:
            db.delete(message)
            db.commit()
            logger.info(f"Deleted message: {message_id}")
            return True
        return False

    @staticmethod
    def search_messages(
        db: Session,
        search_term: str,
        user_id: str = None,
        session_id: str = None,
        role: Optional[MessageRoleEnum] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[ChatMessage]:
        """Search messages by content."""
        query = db.query(ChatMessage)

        if search_term:
            query = query.filter(ChatMessage.content.ilike(f"%{search_term}%"))

        if session_id:
            query = query.filter(ChatMessage.session_id == session_id)
        elif user_id:
            from ..models.chat_session import ChatSession
            query = query.join(ChatSession, ChatMessage.session_id == ChatSession.id).filter(ChatSession.user_id == user_id)

        if role:
            query = query.filter(ChatMessage.role == role)

        return query.order_by(desc(ChatMessage.created_at)).offset(skip).limit(limit).all()

    @staticmethod
    def get_conversation_context(
        db: Session,
        session_id: str,
        limit: int = 20
    ) -> List[dict]:
        """Get conversation context for LLM processing."""
        messages = ChatMessageRepository.get_recent_messages(db, session_id, limit)

        # Convert to format expected by LLM service
        context = []
        for msg in reversed(messages):  # Reverse to get chronological order
            context.append({
                "role": msg.role.value,
                "content": msg.content
            })

        return context
