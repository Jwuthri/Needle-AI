"""
ScrapingJob repository for managing review collection tasks.
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database.models.scraping_job import JobStatusEnum, ScrapingJob
from app.utils.logging import get_logger

logger = get_logger("scraping_job_repository")


class ScrapingJobRepository:
    """Repository for ScrapingJob model operations."""

    @staticmethod
    async def create(
        db: AsyncSession,
        company_id: str,
        source_id: str,
        user_id: str,
        total_reviews_target: int,
        cost: float
    ) -> ScrapingJob:
        """Create a new scraping job."""
        job = ScrapingJob(
            company_id=company_id,
            source_id=source_id,
            user_id=user_id,
            total_reviews_target=total_reviews_target,
            cost=cost
        )
        db.add(job)
        await db.flush()
        await db.refresh(job)
        logger.info(f"Created scraping job: {job.id}")
        return job

    @staticmethod
    async def get_by_id(db: AsyncSession, job_id: str) -> Optional[ScrapingJob]:
        """Get scraping job by ID."""
        result = await db.execute(select(ScrapingJob).filter(ScrapingJob.id == job_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_celery_task_id(db: AsyncSession, task_id: str) -> Optional[ScrapingJob]:
        """Get scraping job by Celery task ID."""
        result = await db.execute(
            select(ScrapingJob).filter(ScrapingJob.celery_task_id == task_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_user_jobs(
        db: AsyncSession,
        user_id: str,
        status: Optional[JobStatusEnum] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[ScrapingJob]:
        """List user's scraping jobs."""
        query = select(ScrapingJob).filter(ScrapingJob.user_id == user_id)

        if status:
            query = query.filter(ScrapingJob.status == status)

        query = query.order_by(desc(ScrapingJob.created_at)).limit(limit).offset(offset)
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def list_company_jobs(
        db: AsyncSession,
        company_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[ScrapingJob]:
        """List scraping jobs for a company."""
        result = await db.execute(
            select(ScrapingJob)
            .filter(ScrapingJob.company_id == company_id)
            .order_by(desc(ScrapingJob.created_at))
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    @staticmethod
    async def update_status(
        db: AsyncSession,
        job_id: str,
        status: JobStatusEnum,
        error_message: Optional[str] = None
    ) -> Optional[ScrapingJob]:
        """Update job status."""
        job = await ScrapingJobRepository.get_by_id(db, job_id)
        if not job:
            return None

        job.status = status
        if error_message:
            job.error_message = error_message

        if status == JobStatusEnum.RUNNING and not job.started_at:
            job.started_at = datetime.utcnow()
        elif status in [JobStatusEnum.COMPLETED, JobStatusEnum.FAILED, JobStatusEnum.CANCELLED]:
            job.completed_at = datetime.utcnow()

        await db.flush()
        await db.refresh(job)
        return job

    @staticmethod
    async def update_progress(
        db: AsyncSession,
        job_id: str,
        progress_percentage: float,
        reviews_fetched: int
    ) -> Optional[ScrapingJob]:
        """Update job progress."""
        job = await ScrapingJobRepository.get_by_id(db, job_id)
        if not job:
            return None

        job.progress_percentage = progress_percentage
        job.reviews_fetched = reviews_fetched

        await db.flush()
        await db.refresh(job)
        return job

    @staticmethod
    async def set_celery_task_id(
        db: AsyncSession,
        job_id: str,
        celery_task_id: str
    ) -> Optional[ScrapingJob]:
        """Set Celery task ID."""
        job = await ScrapingJobRepository.get_by_id(db, job_id)
        if not job:
            return None

        job.celery_task_id = celery_task_id
        await db.flush()
        await db.refresh(job)
        return job

