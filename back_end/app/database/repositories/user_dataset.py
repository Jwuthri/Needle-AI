"""UserDataset repository for database operations."""

from typing import List
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from back_end.app.database.models.user_dataset import UserDataset
from back_end.app.database.repositories.base_async import BaseAsyncRepository


class UserDatasetRepository(BaseAsyncRepository[UserDataset]):
    """Repository for UserDataset model operations."""

    def __init__(self, session: AsyncSession):
        """
        Initialize UserDataset repository.

        Args:
            session: Async database session
        """
        super().__init__(UserDataset, session)

    async def get_by_user_id(
        self, user_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[UserDataset]:
        """
        Get all datasets for a user.

        Args:
            user_id: User UUID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of user datasets ordered by creation time
        """
        result = await self.session.execute(
            select(UserDataset)
            .where(UserDataset.user_id == user_id)
            .order_by(UserDataset.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_name(
        self, user_id: UUID, name: str
    ) -> List[UserDataset]:
        """
        Get datasets by name for a user.

        Args:
            user_id: User UUID
            name: Dataset name (case-insensitive search)

        Returns:
            List of matching user datasets
        """
        result = await self.session.execute(
            select(UserDataset)
            .where(
                UserDataset.user_id == user_id,
                UserDataset.name.ilike(f"%{name}%")
            )
            .order_by(UserDataset.created_at.desc())
        )
        return list(result.scalars().all())
