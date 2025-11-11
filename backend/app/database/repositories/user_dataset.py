"""
UserDataset repository for managing user-uploaded datasets.
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database.models.user_dataset import UserDataset
from app.utils.logging import get_logger

logger = get_logger("user_dataset_repository")


class UserDatasetRepository:
    """Repository for UserDataset model operations."""

    @staticmethod
    async def create(
        db: AsyncSession,
        user_id: str,
        origin: str,
        table_name: str,
        row_count: int = 0,
        description: Optional[str] = None,
        meta: Optional[dict] = None
    ) -> UserDataset:
        """Create a new user dataset."""
        user_dataset = UserDataset(
            user_id=user_id,
            origin=origin,
            table_name=table_name,
            row_count=row_count,
            description=description,
            meta=meta
        )
        db.add(user_dataset)
        await db.flush()
        await db.refresh(user_dataset)
        logger.info(f"Created user dataset: {user_dataset.id} (table: {table_name})")
        return user_dataset

    @staticmethod
    async def get_by_id(db: AsyncSession, dataset_id: str) -> Optional[UserDataset]:
        """Get user dataset by ID."""
        result = await db.execute(select(UserDataset).filter(UserDataset.id == dataset_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_table_name(
        db: AsyncSession,
        user_id: str,
        table_name: str
    ) -> Optional[UserDataset]:
        """Get user dataset by user ID and table name."""
        result = await db.execute(
            select(UserDataset).filter(
                UserDataset.user_id == user_id,
                UserDataset.table_name == table_name
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_user_datasets(
        db: AsyncSession,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[UserDataset]:
        """List user's datasets."""
        result = await db.execute(
            select(UserDataset)
            .filter(UserDataset.user_id == user_id)
            .order_by(desc(UserDataset.created_at))
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    @staticmethod
    async def update(
        db: AsyncSession,
        dataset_id: str,
        **kwargs
    ) -> Optional[UserDataset]:
        """Update user dataset."""
        user_dataset = await UserDatasetRepository.get_by_id(db, dataset_id)
        if not user_dataset:
            return None

        for key, value in kwargs.items():
            if hasattr(user_dataset, key):
                setattr(user_dataset, key, value)

        user_dataset.updated_at = datetime.utcnow()
        await db.flush()
        await db.refresh(user_dataset)
        return user_dataset

    @staticmethod
    async def delete(db: AsyncSession, dataset_id: str) -> bool:
        """Delete user dataset by ID."""
        user_dataset = await UserDatasetRepository.get_by_id(db, dataset_id)
        if user_dataset:
            await db.delete(user_dataset)
            await db.flush()
            logger.info(f"Deleted user dataset: {dataset_id}")
            return True
        return False

    @staticmethod
    async def count_user_datasets(db: AsyncSession, user_id: str) -> int:
        """Count user's datasets."""
        from sqlalchemy import func
        result = await db.execute(
            select(func.count(UserDataset.id))
            .filter(UserDataset.user_id == user_id)
        )
        return result.scalar() or 0

    @staticmethod
    async def get_all_table_names(db: AsyncSession, user_id: str) -> List[str]:
        """Get all table names for a user."""
        result = await db.execute(
            select(UserDataset.table_name)
            .filter(UserDataset.user_id == user_id)
        )
        return [row[0] for row in result.all()]

