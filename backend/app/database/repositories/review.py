"""
Review repository for managing collected reviews.
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import and_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database.models.review import Review
from app.utils.logging import get_logger

logger = get_logger("review_repository")


class ReviewRepository:
    """Repository for Review model operations."""

    @staticmethod
    async def create(
        db: AsyncSession,
        company_id: str,
        source_id: str,
        content: str,
        scraping_job_id: Optional[str] = None,
        author: Optional[str] = None,
        url: Optional[str] = None,
        sentiment_score: Optional[float] = None,
        metadata: Optional[dict] = None,
        review_date: Optional[datetime] = None
    ) -> Review:
        """Create a new review."""
        review = Review(
            company_id=company_id,
            source_id=source_id,
            content=content,
            scraping_job_id=scraping_job_id,
            author=author,
            url=url,
            sentiment_score=sentiment_score,
            metadata=metadata or {},
            review_date=review_date
        )
        db.add(review)
        await db.flush()
        await db.refresh(review)
        return review

    @staticmethod
    async def bulk_create(
        db: AsyncSession,
        reviews: List[dict]
    ) -> List[Review]:
        """Bulk create reviews."""
        review_objects = [Review(**review_data) for review_data in reviews]
        db.add_all(review_objects)
        await db.flush()
        logger.info(f"Bulk created {len(review_objects)} reviews")
        return review_objects

    @staticmethod
    async def get_by_id(db: AsyncSession, review_id: str) -> Optional[Review]:
        """Get review by ID."""
        result = await db.execute(select(Review).filter(Review.id == review_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def list_company_reviews(
        db: AsyncSession,
        company_id: str,
        source_id: Optional[str] = None,
        min_sentiment: Optional[float] = None,
        max_sentiment: Optional[float] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Review]:
        """List reviews for a company with filters."""
        query = select(Review).filter(Review.company_id == company_id)

        if source_id:
            query = query.filter(Review.source_id == source_id)

        if min_sentiment is not None:
            query = query.filter(Review.sentiment_score >= min_sentiment)

        if max_sentiment is not None:
            query = query.filter(Review.sentiment_score <= max_sentiment)

        query = query.order_by(desc(Review.scraped_at)).limit(limit).offset(offset)
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def list_job_reviews(
        db: AsyncSession,
        scraping_job_id: str
    ) -> List[Review]:
        """List reviews from a specific scraping job."""
        result = await db.execute(
            select(Review)
            .filter(Review.scraping_job_id == scraping_job_id)
            .order_by(desc(Review.scraped_at))
        )
        return list(result.scalars().all())

    @staticmethod
    async def update_sentiment(
        db: AsyncSession,
        review_id: str,
        sentiment_score: float
    ) -> Optional[Review]:
        """Update review sentiment score."""
        review = await ReviewRepository.get_by_id(db, review_id)
        if not review:
            return None

        review.sentiment_score = sentiment_score
        review.processed_at = datetime.utcnow()

        await db.flush()
        await db.refresh(review)
        return review

    @staticmethod
    async def set_vector_id(
        db: AsyncSession,
        review_id: str,
        vector_id: str
    ) -> Optional[Review]:
        """Set Pinecone vector ID."""
        review = await ReviewRepository.get_by_id(db, review_id)
        if not review:
            return None

        review.vector_id = vector_id
        await db.flush()
        await db.refresh(review)
        return review

    @staticmethod
    async def count_company_reviews(
        db: AsyncSession,
        company_id: str,
        source_id: Optional[str] = None
    ) -> int:
        """Count reviews for a company."""
        query = select(func.count(Review.id)).filter(Review.company_id == company_id)

        if source_id:
            query = query.filter(Review.source_id == source_id)

        result = await db.execute(query)
        return result.scalar_one()

    @staticmethod
    async def get_sentiment_stats(
        db: AsyncSession,
        company_id: str
    ) -> dict:
        """Get sentiment statistics for a company."""
        result = await db.execute(
            select(
                func.count(Review.id).label('total'),
                func.avg(Review.sentiment_score).label('avg_sentiment'),
                func.sum(func.case((Review.sentiment_score > 0.33, 1), else_=0)).label('positive'),
                func.sum(func.case((and_(Review.sentiment_score >= -0.33, Review.sentiment_score <= 0.33), 1), else_=0)).label('neutral'),
                func.sum(func.case((Review.sentiment_score < -0.33, 1), else_=0)).label('negative')
            )
            .filter(Review.company_id == company_id, Review.sentiment_score.isnot(None))
        )
        row = result.one()
        return {
            'total': row.total or 0,
            'avg_sentiment': float(row.avg_sentiment) if row.avg_sentiment else 0.0,
            'positive': row.positive or 0,
            'neutral': row.neutral or 0,
            'negative': row.negative or 0
        }

    @staticmethod
    async def search_reviews(
        db: AsyncSession,
        company_id: str,
        search_term: str,
        limit: int = 50
    ) -> List[Review]:
        """Search reviews by content."""
        result = await db.execute(
            select(Review)
            .filter(
                Review.company_id == company_id,
                Review.content.ilike(f'%{search_term}%')
            )
            .order_by(desc(Review.scraped_at))
            .limit(limit)
        )
        return list(result.scalars().all())

