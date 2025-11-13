"""ChatMessageStep repository for database operations."""

from typing import List
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from back_end.app.database.models.chat_message_step import ChatMessageStep
from back_end.app.database.repositories.base_async import BaseAsyncRepository


class ChatMessageStepRepository(BaseAsyncRepository[ChatMessageStep]):
    """Repository for ChatMessageStep model operations."""

    def __init__(self, session: AsyncSession):
        """
        Initialize ChatMessageStep repository.

        Args:
            session: Async database session
        """
        super().__init__(ChatMessageStep, session)

    async def get_by_message_id(
        self, message_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[ChatMessageStep]:
        """
        Get all steps for a chat message.

        Args:
            message_id: Message UUID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of chat message steps ordered by creation time
        """
        result = await self.session.execute(
            select(ChatMessageStep)
            .where(ChatMessageStep.message_id == message_id)
            .order_by(ChatMessageStep.created_at.asc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_step_type(
        self, message_id: UUID, step_type: str
    ) -> List[ChatMessageStep]:
        """
        Get steps by type for a message.

        Args:
            message_id: Message UUID
            step_type: Step type (e.g., 'thinking', 'tool_call', 'retrieval')

        Returns:
            List of chat message steps with specified type
        """
        result = await self.session.execute(
            select(ChatMessageStep)
            .where(
                ChatMessageStep.message_id == message_id,
                ChatMessageStep.step_type == step_type
            )
            .order_by(ChatMessageStep.created_at.asc())
        )
        return list(result.scalars().all())
