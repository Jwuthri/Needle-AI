"""ChatSession repository for database operations."""

from typing import List, Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from back_end.app.database.models.chat_session import ChatSession
from back_end.app.database.repositories.base_async import BaseAsyncRepository


class ChatSessionRepository(BaseAsyncRepository[ChatSession]):
    """Repository for ChatSession model operations."""

    def __init__(self, session: AsyncSession):
        """
        Initialize ChatSession repository.

        Args:
            session: Async database session
        """
        super().__init__(ChatSession, session)

    async def get_by_user_id(
        self, user_id: UUID, skip: int = 0, limit: int = 50
    ) -> List[ChatSession]:
        """
        Get all chat sessions for a user.

        Args:
            user_id: User UUID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of chat sessions
        """
        result = await self.session.execute(
            select(ChatSession)
            .where(ChatSession.user_id == user_id)
            .order_by(ChatSession.updated_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_company_id(
        self, company_id: UUID, skip: int = 0, limit: int = 50
    ) -> List[ChatSession]:
        """
        Get all chat sessions for a company.

        Args:
            company_id: Company UUID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of chat sessions
        """
        result = await self.session.execute(
            select(ChatSession)
            .where(ChatSession.company_id == company_id)
            .order_by(ChatSession.updated_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_with_messages(self, session_id: UUID) -> Optional[ChatSession]:
        """
        Get chat session with all messages eagerly loaded.

        Args:
            session_id: Session UUID

        Returns:
            ChatSession with messages or None if not found
        """
        result = await self.session.execute(
            select(ChatSession)
            .where(ChatSession.id == session_id)
            .options(selectinload(ChatSession.messages))
        )
        return result.scalar_one_or_none()
