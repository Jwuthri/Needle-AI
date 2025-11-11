"""
Scraping job model for background review collection tasks.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import relationship

from ..base import Base


class JobStatusEnum(str, enum.Enum):
    """Scraping job statuses."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ScrapingJob(Base):
    """Background scraping job for collecting reviews."""
    __tablename__ = "scraping_jobs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # References
    company_id = Column(String, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    source_id = Column(String, ForeignKey("review_sources.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Job details
    status = Column(SQLEnum(JobStatusEnum), default=JobStatusEnum.PENDING, nullable=False, index=True)
    progress_percentage = Column(Float, default=0.0, nullable=False)  # 0.0 to 100.0

    # Targets and results
    total_reviews_target = Column(Integer, nullable=False)
    reviews_fetched = Column(Integer, default=0, nullable=False)

    # Cost tracking
    cost = Column(Float, default=0.0, nullable=False)  # Total cost in credits

    # Celery task tracking
    celery_task_id = Column(String, nullable=True, index=True)

    # Error handling
    error_message = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    company = relationship("Company", back_populates="scraping_jobs")
    source = relationship("ReviewSource", back_populates="scraping_jobs")
    user = relationship("User", back_populates="scraping_jobs")
    reviews = relationship("Review", back_populates="scraping_job", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index('idx_jobs_status_created', 'status', 'created_at'),
        Index('idx_jobs_user_created', 'user_id', 'created_at'),
        Index('idx_jobs_company', 'company_id', 'created_at'),
        Index('idx_jobs_celery_task', 'celery_task_id'),
    )

    def __repr__(self):
        return f"<ScrapingJob(id={self.id}, company_id={self.company_id}, status={self.status}, progress={self.progress_percentage}%)>"

