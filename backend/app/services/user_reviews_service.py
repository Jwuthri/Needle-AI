"""
Service for managing user-specific aggregated reviews table.

This service creates and maintains the __user_{id}_reviews table which aggregates
all reviews accessible to a user from their companies and datasets.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database.models.company import Company
from app.database.models.review import Review
from app.database.models.scraping_job import ScrapingJob
from app.database.repositories.user_dataset import UserDatasetRepository
from app.utils.dynamic_tables import sanitize_table_name
from app.utils.logging import get_logger

logger = get_logger(__name__)


class UserReviewsService:
    """Service for managing user-specific aggregated reviews tables."""

    def __init__(self, db: AsyncSession):
        """Initialize user reviews service."""
        self.db = db

    def _log_prefix(self, user_id: Optional[str] = None) -> str:
        """Generate log prefix."""
        parts = ["[UserReviewsService]"]
        if user_id:
            parts.append(f"[user={user_id}]")
        return " | ".join(parts)

    def get_user_reviews_table_name(self, user_id: str) -> str:
        """Get the standardized table name for user reviews.
        
        Args:
            user_id: User ID
            
        Returns:
            Table name in format: __user_{user_id}_reviews
        """
        sanitized_user_id = sanitize_table_name(user_id)
        return f"__user_{sanitized_user_id}_reviews"

    async def ensure_user_reviews_table(self, user_id: str) -> bool:
        """Create the __user_{id}_reviews table if it doesn't exist.
        
        Args:
            user_id: User ID
            
        Returns:
            True if table was created, False if it already existed
        """
        table_name = self.get_user_reviews_table_name(user_id)
        
        # Check if table exists
        result = await self.db.execute(
            text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = :table_name
                )
            """),
            {"table_name": table_name}
        )
        table_exists = result.scalar()
        
        if table_exists:
            logger.info(f"{self._log_prefix(user_id)} | Table {table_name} already exists")
            return False
        
        # Create table with standardized schema
        # Based on the EDA example: id, user_id, company_name, category, rating, text, source, date, author, created_at, updated_at
        # Plus __embedding__ column for vector search
        create_table_sql = f"""
            CREATE TABLE "{table_name}" (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                company_name TEXT,
                category TEXT DEFAULT 'review',
                rating INTEGER,
                text TEXT NOT NULL,
                source TEXT,
                date TIMESTAMP,
                author TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                __embedding__ vector(1536)
            )
        """
        
        await self.db.execute(text(create_table_sql))
        
        # Create indexes for performance
        indexes_sql = [
            f'CREATE INDEX IF NOT EXISTS "idx_{table_name}_user_id" ON "{table_name}" (user_id)',
            f'CREATE INDEX IF NOT EXISTS "idx_{table_name}_source" ON "{table_name}" (source)',
            f'CREATE INDEX IF NOT EXISTS "idx_{table_name}_date" ON "{table_name}" (date)',
            f'CREATE INDEX IF NOT EXISTS "idx_{table_name}_rating" ON "{table_name}" (rating)',
            f'CREATE INDEX IF NOT EXISTS "idx_{table_name}_company" ON "{table_name}" (company_name)',
        ]
        
        for index_sql in indexes_sql:
            await self.db.execute(text(index_sql))
        
        await self.db.commit()
        
        logger.info(f"{self._log_prefix(user_id)} | Created table {table_name} with indexes")
        return True

    async def _compute_field_stats(self, user_id: str, row_count: int) -> tuple[list, dict]:
        """Compute actual field statistics from the reviews table.
        
        Args:
            user_id: User ID
            row_count: Total row count
            
        Returns:
            Tuple of (field_metadata, computed_stats)
        """
        table_name = self.get_user_reviews_table_name(user_id)
        
        # Query unique counts and top values for key fields
        stats_queries = {
            "company_name": f'SELECT company_name, COUNT(*) as cnt FROM "{table_name}" GROUP BY company_name ORDER BY cnt DESC LIMIT 10',
            "source": f'SELECT source, COUNT(*) as cnt FROM "{table_name}" GROUP BY source ORDER BY cnt DESC LIMIT 10',
            "author": f'SELECT author, COUNT(*) as cnt FROM "{table_name}" WHERE author IS NOT NULL GROUP BY author ORDER BY cnt DESC LIMIT 10',
            "rating": f'SELECT rating, COUNT(*) as cnt FROM "{table_name}" WHERE rating IS NOT NULL GROUP BY rating ORDER BY cnt DESC LIMIT 10',
            "category": f'SELECT category, COUNT(*) as cnt FROM "{table_name}" GROUP BY category ORDER BY cnt DESC LIMIT 10',
        }
        
        computed_stats = {}
        for field, query in stats_queries.items():
            try:
                result = await self.db.execute(text(query))
                rows = result.fetchall()
                computed_stats[field] = {
                    "unique_count": len(rows),
                    "top_values": [{"value": str(r[0]) if r[0] else "null", "count": r[1]} for r in rows[:5]]
                }
            except Exception as e:
                logger.warning(f"{self._log_prefix(user_id)} | Failed to compute stats for {field}: {e}")
                computed_stats[field] = {"unique_count": None, "top_values": None}
        
        # Get unique counts for other fields
        unique_count_queries = {
            "id": f'SELECT COUNT(DISTINCT id) FROM "{table_name}"',
            "user_id": f'SELECT COUNT(DISTINCT user_id) FROM "{table_name}"',
            "text": f'SELECT COUNT(DISTINCT text) FROM "{table_name}"',
            "date": f'SELECT COUNT(DISTINCT date) FROM "{table_name}"',
        }
        
        for field, query in unique_count_queries.items():
            try:
                result = await self.db.execute(text(query))
                computed_stats[field] = {"unique_count": result.scalar(), "top_values": None}
            except Exception as e:
                logger.warning(f"{self._log_prefix(user_id)} | Failed to count {field}: {e}")
                computed_stats[field] = {"unique_count": None, "top_values": None}
        
        # Build field metadata with computed values
        field_metadata = [
            {
                "field_name": "id",
                "data_type": "text",
                "description": "A unique identifier (UUID) for each review row.",
                "unique_value_count": computed_stats.get("id", {}).get("unique_count", row_count),
                "top_values": None
            },
            {
                "field_name": "user_id",
                "data_type": "text",
                "description": "Identifier for the owning user or tenant.",
                "unique_value_count": computed_stats.get("user_id", {}).get("unique_count", 1),
                "top_values": None
            },
            {
                "field_name": "company_name",
                "data_type": "text",
                "description": "Name of the company being reviewed.",
                "unique_value_count": computed_stats.get("company_name", {}).get("unique_count", 1),
                "top_values": [v["value"] for v in computed_stats.get("company_name", {}).get("top_values", []) or []][:5] or None
            },
            {
                "field_name": "category",
                "data_type": "text",
                "description": "High-level classification of the record (e.g., `review`).",
                "unique_value_count": computed_stats.get("category", {}).get("unique_count", 1),
                "top_values": [v["value"] for v in computed_stats.get("category", {}).get("top_values", []) or []][:5] or ["review"]
            },
            {
                "field_name": "rating",
                "data_type": "int",
                "description": "Numeric rating attached to each review (range: 1–5).",
                "unique_value_count": computed_stats.get("rating", {}).get("unique_count", 5),
                "top_values": [v["value"] for v in computed_stats.get("rating", {}).get("top_values", []) or []][:5] or None
            },
            {
                "field_name": "text",
                "data_type": "text",
                "description": "Full review text or short commentary from the external source.",
                "unique_value_count": computed_stats.get("text", {}).get("unique_count", row_count),
                "top_values": None
            },
            {
                "field_name": "source",
                "data_type": "text",
                "description": "Origin platform for the review (e.g., `reddit`, `twitter/x`, `trustpilot`).",
                "unique_value_count": computed_stats.get("source", {}).get("unique_count"),
                "top_values": [v["value"] for v in computed_stats.get("source", {}).get("top_values", []) or []][:5] or None
            },
            {
                "field_name": "date",
                "data_type": "timestamp",
                "description": "The original timestamp when the review was posted.",
                "unique_value_count": computed_stats.get("date", {}).get("unique_count", row_count),
                "top_values": None
            },
            {
                "field_name": "author",
                "data_type": "text",
                "description": "Handle or username of the person who posted the review.",
                "unique_value_count": computed_stats.get("author", {}).get("unique_count"),
                "top_values": [v["value"] for v in computed_stats.get("author", {}).get("top_values", []) or []][:5] or None
            },
            {
                "field_name": "created_at",
                "data_type": "timestamp",
                "description": "When this record was created in the system.",
                "unique_value_count": row_count,
                "top_values": None
            },
            {
                "field_name": "updated_at",
                "data_type": "timestamp",
                "description": "Last time the record was updated.",
                "unique_value_count": row_count,
                "top_values": None
            }
        ]
        
        return field_metadata, computed_stats

    async def ensure_user_dataset_record(self, user_id: str, row_count: int = 0) -> None:
        """Ensure a user_datasets record exists for the reviews table.
        
        This creates metadata that allows the LLM agents to discover the reviews dataset.
        
        Args:
            user_id: User ID
            row_count: Number of rows in the reviews table
        """
        table_name = self.get_user_reviews_table_name(user_id)
        
        # Check if user_datasets record already exists
        existing = await UserDatasetRepository.get_by_table_name(self.db, table_name, user_id)
        
        if existing:
            logger.info(f"{self._log_prefix(user_id)} | user_datasets record already exists for {table_name}")
            # Compute fresh field stats from actual data
            field_metadata, _ = await self._compute_field_stats(user_id, row_count)
            
            # Update row count and field metadata
            existing.row_count = row_count
            existing.field_metadata = field_metadata
            await self.db.commit()
            logger.info(f"{self._log_prefix(user_id)} | Updated row count to {row_count} and refreshed field metadata")
            return
        
        # Create user_datasets record
        repository = UserDatasetRepository()
        
        # Build field metadata with computed stats from actual data
        field_metadata, _ = await self._compute_field_stats(user_id, row_count)
        
        # Build column stats
        column_stats = {
            "id": {"dtype": "text", "description": "Unique identifier (UUID) for each review"},
            "user_id": {"dtype": "text", "description": "Owning user/tenant identifier"},
            "company_name": {"dtype": "text", "description": "Company being reviewed"},
            "category": {"dtype": "text", "description": "Record classification (review)"},
            "rating": {"dtype": "int", "description": "Numeric rating 1-5"},
            "text": {"dtype": "text", "description": "Full review text content"},
            "source": {"dtype": "text", "description": "Origin platform (reddit, twitter/x, etc.)"},
            "date": {"dtype": "timestamp", "description": "When review was posted"},
            "author": {"dtype": "text", "description": "Reviewer handle/username"},
            "created_at": {"dtype": "timestamp", "description": "Record creation time"},
            "updated_at": {"dtype": "timestamp", "description": "Record last update time"},
        }
        
        # Vector store columns - main column for embeddings
        vector_store_columns = {
            "main_column": "text",
            "alternative_columns": ["author", "company_name", "category"],
            "description": "The `text` field is the primary candidate for embedding because it contains the review content necessary for semantic search and clustering. Concatenating `author`, `company_name`, and `category` with the main text can provide useful context (who wrote it, which company, and that it is a review) to improve relevance in vector-based retrieval."
        }
        
        await repository.create(
            db=self.db,
            user_id=user_id,
            origin="reviews_sync",
            table_name=table_name,
            row_count=row_count,
            description="**Overview 📊** This dataset contains short social reviews and metadata about a single company, with each row representing one external review item. Fields like `text`, `rating`, `source`, and `author` work together to capture *what* was said, *who* said it, *when*, and *where* (platform) — useful for **customer sentiment** and content analysis. The data is stored as relational records (one JSON-like object per row) with mostly non-null values and consistent timestamps. ⚠️ Note: `company_name`, `user_id`, and `category` are constant (single value), while `text` and `id` are unique per row.",
            field_metadata=field_metadata,
            column_stats=column_stats,
            sample_data=[],
            vector_store_columns=vector_store_columns,
            meta={"dataset_type": "reviews", "auto_generated": True}
        )
        await self.db.commit()
        
        logger.info(f"{self._log_prefix(user_id)} | Created user_datasets record for {table_name}")

    async def sync_reviews_to_user_table(
        self,
        user_id: str,
        scraping_job_id: Optional[str] = None
    ) -> int:
        """Sync reviews from scraping jobs to user's aggregated table.
        
        This method:
        1. Finds all reviews from companies owned by the user
        2. If scraping_job_id is provided, only syncs reviews from that job
        3. Inserts/updates reviews in the __user_{id}_reviews table
        
        Args:
            user_id: User ID
            scraping_job_id: Optional scraping job ID to sync only reviews from that job
            
        Returns:
            Number of reviews synced
        """
        table_name = self.get_user_reviews_table_name(user_id)
        
        # Ensure table exists
        await self.ensure_user_reviews_table(user_id)
        
        # Build query to get reviews
        # Get all companies owned by this user
        companies_query = select(Company.id, Company.name).where(Company.created_by == user_id)
        companies_result = await self.db.execute(companies_query)
        companies = companies_result.fetchall()
        
        if not companies:
            logger.info(f"{self._log_prefix(user_id)} | No companies found for user")
            return 0
        
        company_ids = [c.id for c in companies]
        company_names_map = {c.id: c.name for c in companies}
        
        # Build reviews query
        reviews_query = select(Review).where(Review.company_id.in_(company_ids))
        
        if scraping_job_id:
            reviews_query = reviews_query.where(Review.scraping_job_id == scraping_job_id)
        
        reviews_result = await self.db.execute(reviews_query)
        reviews = reviews_result.scalars().all()
        
        if not reviews:
            logger.info(f"{self._log_prefix(user_id)} | No reviews found to sync")
            return 0
        
        # Prepare data for insertion
        synced_count = 0
        for review in reviews:
            try:
                company_name = company_names_map.get(review.company_id, "Unknown")
                
                # Extract rating from extra_metadata if available, or derive from sentiment
                rating = None
                if review.extra_metadata and isinstance(review.extra_metadata, dict):
                    rating = review.extra_metadata.get("rating")
                
                # If no rating in metadata, derive from sentiment_score
                if rating is None and review.sentiment_score is not None:
                    # Map sentiment to 1-5 rating scale
                    # sentiment_score: -1.0 to 1.0
                    # rating: 1 to 5
                    rating = int((review.sentiment_score + 1) * 2.5)  # Maps -1 to 1, 0 to 2.5, 1 to 5
                    rating = max(1, min(5, rating))  # Clamp to 1-5
                
                # Determine source/platform
                source = review.platform or "unknown"
                
                # Use review_date if available, otherwise scraped_at
                review_date = review.review_date or review.scraped_at
                
                # Insert or update review in user table
                # Use ON CONFLICT to handle duplicates (based on review.id)
                insert_sql = f"""
                    INSERT INTO "{table_name}" (
                        id, user_id, company_name, category, rating, text, source, date, author, 
                        created_at, updated_at, __embedding__
                    ) VALUES (
                        :id, :user_id, :company_name, :category, :rating, :text, :source, :date, :author,
                        :created_at, :updated_at, :embedding
                    )
                    ON CONFLICT (id) DO UPDATE SET
                        company_name = EXCLUDED.company_name,
                        rating = EXCLUDED.rating,
                        text = EXCLUDED.text,
                        source = EXCLUDED.source,
                        date = EXCLUDED.date,
                        author = EXCLUDED.author,
                        updated_at = CURRENT_TIMESTAMP,
                        __embedding__ = EXCLUDED.__embedding__
                """
                
                # Convert embedding to string format if present
                embedding_str = None
                if review.embedding is not None:
                    # Embedding is a Vector type, convert to list then string
                    try:
                        embedding_list = list(review.embedding) if hasattr(review.embedding, '__iter__') else None
                        if embedding_list:
                            embedding_str = '[' + ','.join(map(str, embedding_list)) + ']'
                    except Exception as e:
                        logger.warning(f"{self._log_prefix(user_id)} | Failed to convert embedding for review {review.id}: {e}")
                
                await self.db.execute(
                    text(insert_sql),
                    {
                        "id": review.id,
                        "user_id": user_id,
                        "company_name": company_name,
                        "category": "review",
                        "rating": rating,
                        "text": review.content,
                        "source": source,
                        "date": review_date,
                        "author": review.author,
                        "created_at": review.scraped_at or datetime.utcnow(),
                        "updated_at": datetime.utcnow(),
                        "embedding": embedding_str,
                    }
                )
                synced_count += 1
            except Exception as e:
                logger.error(f"{self._log_prefix(user_id)} | Failed to sync review {review.id}: {e}")
                continue
        
        await self.db.commit()
        
        logger.info(f"{self._log_prefix(user_id)} | Synced {synced_count} reviews to {table_name}")
        
        # Get ACTUAL total row count from the table
        count_query = text(f'SELECT COUNT(*) FROM "{table_name}"')
        result = await self.db.execute(count_query)
        total_rows = result.scalar()
        
        # Update user_datasets record with actual row count
        await self.ensure_user_dataset_record(user_id, row_count=total_rows)
        
        return synced_count

