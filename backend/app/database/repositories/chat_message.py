"""
Chat message repository for NeedleAi.
"""

from typing import List, Optional

from sqlalchemy import asc, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ...utils.logging import get_logger
from ..models.chat_message import ChatMessage, MessageRoleEnum

logger = get_logger("chat_message_repository")


class ChatMessageRepository:
    """Repository for ChatMessage model operations."""

    @staticmethod
    async def create(
        db: AsyncSession,
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
        await db.flush()
        await db.refresh(message)

        # Import here to avoid circular imports
        from .chat_session import ChatSessionRepository
        await ChatSessionRepository.increment_message_count(db, session_id, kwargs.get('token_count', 0))

        logger.info(f"Created message: {message.id} in session: {session_id}")
        return message

    @staticmethod
    async def get_by_id(db: AsyncSession, message_id: str) -> Optional[ChatMessage]:
        """Get message by ID."""
        result = await db.execute(select(ChatMessage).filter(ChatMessage.id == message_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_session_messages(
        db: AsyncSession,
        session_id: str,
        limit: int = 100,
        offset: int = 0,
        role: Optional[MessageRoleEnum] = None
    ) -> List[ChatMessage]:
        """Get messages for a session."""
        query = select(ChatMessage).filter(ChatMessage.session_id == session_id)

        if role:
            query = query.filter(ChatMessage.role == role)

        query = query.order_by(asc(ChatMessage.created_at)).offset(offset).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_recent_messages(
        db: AsyncSession,
        session_id: str,
        limit: int = 20
    ) -> List[ChatMessage]:
        """Get recent messages for context."""
        query = (
            select(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(desc(ChatMessage.created_at))
            .limit(limit)
        )
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_all(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        role: Optional[MessageRoleEnum] = None
    ) -> List[ChatMessage]:
        """Get all messages with pagination."""
        query = select(ChatMessage)

        if role:
            query = query.filter(ChatMessage.role == role)

        query = query.order_by(desc(ChatMessage.created_at)).offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def count_session_messages(db: AsyncSession, session_id: str) -> int:
        """Count messages in a session."""
        result = await db.execute(
            select(ChatMessage).filter(ChatMessage.session_id == session_id)
        )
        return len(list(result.scalars().all()))

    @staticmethod
    async def count_user_messages(db: AsyncSession, user_id: str) -> int:
        """Count messages for a user across all sessions."""
        from ..models.chat_session import ChatSession
        
        query = (
            select(ChatMessage)
            .join(ChatSession, ChatMessage.session_id == ChatSession.id)
            .filter(ChatSession.user_id == user_id)
        )
        result = await db.execute(query)
        return len(list(result.scalars().all()))

    @staticmethod
    async def update(db: AsyncSession, message_id: str, **kwargs) -> Optional[ChatMessage]:
        """Update a chat message."""
        message = await ChatMessageRepository.get_by_id(db, message_id)
        if not message:
            return None

        for key, value in kwargs.items():
            if hasattr(message, key):
                setattr(message, key, value)

        await db.flush()
        await db.refresh(message)
        return message

    @staticmethod
    async def delete(db: AsyncSession, message_id: str) -> bool:
        """Delete a message."""
        message = await ChatMessageRepository.get_by_id(db, message_id)
        if message:
            await db.delete(message)
            await db.flush()
            logger.info(f"Deleted message: {message_id}")
            return True
        return False

    @staticmethod
    async def search_messages(
        db: AsyncSession,
        search_term: str,
        user_id: str = None,
        session_id: str = None,
        role: Optional[MessageRoleEnum] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[ChatMessage]:
        """Search messages by content."""
        query = select(ChatMessage)

        if search_term:
            query = query.filter(ChatMessage.content.ilike(f"%{search_term}%"))

        if session_id:
            query = query.filter(ChatMessage.session_id == session_id)
        elif user_id:
            from ..models.chat_session import ChatSession
            query = query.join(ChatSession, ChatMessage.session_id == ChatSession.id).filter(ChatSession.user_id == user_id)

        if role:
            query = query.filter(ChatMessage.role == role)

        query = query.order_by(desc(ChatMessage.created_at)).offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_conversation_context(
        db: AsyncSession,
        session_id: str,
        limit: int = 20
    ) -> List[dict]:
        """Get conversation context for LLM processing."""
        messages = await ChatMessageRepository.get_recent_messages(db, session_id, limit)

        # Convert to format expected by LLM service
        context = []
        for msg in reversed(messages):  # Reverse to get chronological order
            context.append({
                "role": msg.role.value,
                "content": msg.content
            })

        return context
