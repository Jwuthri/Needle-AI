"""ChatMessage repository for database operations."""

from typing import List, Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from back_end.app.database.models.chat_message import ChatMessage
from back_end.app.database.repositories.base_async import BaseAsyncRepository


class ChatMessageRepository(BaseAsyncRepository[ChatMessage]):
    """Repository for ChatMessage model operations."""

    def __init__(self, session: AsyncSession):
        """
        Initialize ChatMessage repository.

        Args:
            session: Async database session
        """
        super().__init__(ChatMessage, session)

    async def get_by_session_id(
        self, session_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[ChatMessage]:
        """
        Get all messages for a chat session.

        Args:
            session_id: Session UUID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of chat messages ordered by creation time
        """
        result = await self.session.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.asc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_with_steps(self, message_id: UUID) -> Optional[ChatMessage]:
        """
        Get chat message with all steps eagerly loaded.

        Args:
            message_id: Message UUID

        Returns:
            ChatMessage with steps or None if not found
        """
        result = await self.session.execute(
            select(ChatMessage)
            .where(ChatMessage.id == message_id)
            .options(selectinload(ChatMessage.steps))
        )
        return result.scalar_one_or_none()

    async def get_by_role(
        self, session_id: UUID, role: str, skip: int = 0, limit: int = 100
    ) -> List[ChatMessage]:
        """
        Get messages by role for a session.

        Args:
            session_id: Session UUID
            role: Message role ('user', 'assistant', 'system')
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of chat messages with specified role
        """
        result = await self.session.execute(
            select(ChatMessage)
            .where(
                ChatMessage.session_id == session_id,
                ChatMessage.role == role
            )
            .order_by(ChatMessage.created_at.asc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
