"""
ReviewSource repository for managing review sources.
"""

from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database.models.review_source import ReviewSource, SourceTypeEnum
from app.utils.logging import get_logger

logger = get_logger("review_source_repository")


class ReviewSourceRepository:
    """Repository for ReviewSource model operations."""

    @staticmethod
    async def create(
        db: AsyncSession,
        name: str,
        source_type: SourceTypeEnum,
        cost_per_review: float = 0.01,
        description: Optional[str] = None,
        config: Optional[dict] = None
    ) -> ReviewSource:
        """Create a new review source."""
        source = ReviewSource(
            name=name,
            source_type=source_type,
            cost_per_review=cost_per_review,
            description=description,
            config=config or {}
        )
        db.add(source)
        await db.flush()
        await db.refresh(source)
        logger.info(f"Created review source: {source.id} - {source.name}")
        return source

    @staticmethod
    async def get_by_id(db: AsyncSession, source_id: str) -> Optional[ReviewSource]:
        """Get review source by ID."""
        result = await db.execute(select(ReviewSource).filter(ReviewSource.id == source_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_name(db: AsyncSession, name: str) -> Optional[ReviewSource]:
        """Get review source by name."""
        result = await db.execute(select(ReviewSource).filter(ReviewSource.name == name))
        return result.scalar_one_or_none()

    @staticmethod
    async def list_active_sources(db: AsyncSession) -> List[ReviewSource]:
        """List all active review sources."""
        result = await db.execute(
            select(ReviewSource)
            .filter(ReviewSource.is_active == True)
            .order_by(ReviewSource.name)
        )
        return list(result.scalars().all())

    @staticmethod
    async def list_by_type(
        db: AsyncSession,
        source_type: SourceTypeEnum
    ) -> List[ReviewSource]:
        """List review sources by type."""
        result = await db.execute(
            select(ReviewSource)
            .filter(ReviewSource.source_type == source_type, ReviewSource.is_active == True)
            .order_by(ReviewSource.name)
        )
        return list(result.scalars().all())

    @staticmethod
    async def update(
        db: AsyncSession,
        source_id: str,
        **kwargs
    ) -> Optional[ReviewSource]:
        """Update review source."""
        source = await ReviewSourceRepository.get_by_id(db, source_id)
        if not source:
            return None

        for key, value in kwargs.items():
            if hasattr(source, key) and value is not None:
                setattr(source, key, value)

        await db.flush()
        await db.refresh(source)
        return source

