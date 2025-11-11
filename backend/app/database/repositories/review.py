"""
Review repository for managing collected reviews.
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import and_, desc, func, text
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
        content: str,
        platform: Optional[str] = None,
        source_id: Optional[str] = None,
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
            content=content,
            platform=platform,
            source_id=source_id,
            scraping_job_id=scraping_job_id,
            author=author,
            url=url,
            sentiment_score=sentiment_score,
            extra_metadata=metadata or {},
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

    @staticmethod
    async def update_embedding(
        db: AsyncSession,
        review_id: str,
        embedding: List[float]
    ) -> Optional[Review]:
        """Update review embedding vector."""
        review = await ReviewRepository.get_by_id(db, review_id)
        if not review:
            return None

        review.embedding = embedding
        await db.flush()
        await db.refresh(review)
        logger.info(f"Updated embedding for review {review_id}")
        return review

    @staticmethod
    async def bulk_update_embeddings(
        db: AsyncSession,
        review_embeddings: List[tuple[str, List[float]]]
    ) -> int:
        """
        Bulk update embeddings for multiple reviews.
        
        Args:
            db: Database session
            review_embeddings: List of tuples (review_id, embedding_vector)
            
        Returns:
            Number of reviews updated
        """
        updated_count = 0
        for review_id, embedding in review_embeddings:
            review = await ReviewRepository.get_by_id(db, review_id)
            if review:
                review.embedding = embedding
                updated_count += 1
        
        await db.flush()
        logger.info(f"Bulk updated {updated_count} review embeddings")
        return updated_count

    @staticmethod
    async def get_reviews_without_embeddings(
        db: AsyncSession,
        limit: int = 100,
        company_id: Optional[str] = None
    ) -> List[Review]:
        """Get reviews that don't have embeddings yet."""
        query = select(Review).filter(Review.embedding.is_(None))
        
        if company_id:
            query = query.filter(Review.company_id == company_id)
        
        query = query.order_by(Review.scraped_at).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def similarity_search(
        db: AsyncSession,
        query_embedding: List[float],
        company_id: Optional[str] = None,
        limit: int = 10,
        similarity_threshold: float = 0.7
    ) -> List[tuple[Review, float]]:
        """
        Find reviews similar to the query embedding using cosine similarity.
        
        Args:
            db: Database session
            query_embedding: Query embedding vector
            company_id: Optional company ID to filter results
            limit: Maximum number of results
            similarity_threshold: Minimum similarity score (0-1)
            
        Returns:
            List of tuples (Review, similarity_score)
        """
        # Convert embedding to string format for SQL
        embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'
        
        # Build the query with similarity calculation
        # Using cosine distance (1 - cosine similarity)
        # Lower distance = higher similarity
        base_query = """
            SELECT 
                reviews.*,
                1 - (reviews.embedding <=> :query_embedding::vector) as similarity
            FROM reviews
            WHERE reviews.embedding IS NOT NULL
        """
        
        if company_id:
            base_query += " AND reviews.company_id = :company_id"
        
        base_query += """
            AND 1 - (reviews.embedding <=> :query_embedding::vector) >= :threshold
            ORDER BY reviews.embedding <=> :query_embedding::vector
            LIMIT :limit
        """
        
        params = {
            'query_embedding': embedding_str,
            'threshold': similarity_threshold,
            'limit': limit
        }
        
        if company_id:
            params['company_id'] = company_id
        
        result = await db.execute(text(base_query), params)
        rows = result.fetchall()
        
        # Convert rows to Review objects with similarity scores
        reviews_with_scores = []
        for row in rows:
            # Reconstruct Review object from row
            review = await ReviewRepository.get_by_id(db, row.id)
            if review:
                reviews_with_scores.append((review, float(row.similarity)))
        
        return reviews_with_scores

