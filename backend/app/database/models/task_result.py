"""
Task result model for NeedleAi.
"""

from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import relationship

from ..base import Base


class TaskResult(Base):
    """Store Celery task results with additional metadata."""
    __tablename__ = "task_results"

    id = Column(String, primary_key=True)  # Use Celery task ID
    user_id = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Task metadata
    task_name = Column(String(255), nullable=False)
    task_args = Column(JSON, default=[])
    task_kwargs = Column(JSON, default={})

    # Task status and results
    status = Column(String(50), default="PENDING")  # PENDING, STARTED, SUCCESS, FAILURE, RETRY, REVOKED
    result = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    traceback = Column(Text, nullable=True)

    # Timing information
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Additional metadata
    extra_metadata = Column(JSON, default={})

    # Relationships
    user = relationship("User")

    # Indexes
    __table_args__ = (
        # Composite indexes for common query patterns
        Index('idx_task_results_user_created', 'user_id', 'created_at'),
        Index('idx_task_results_status_created', 'status', 'created_at'),
        Index('idx_task_results_task_name_created', 'task_name', 'created_at'),
        # Single column indexes (optional - composite indexes above cover most cases)
        # Index('idx_task_results_created_at', 'created_at'),  # Only if you query by date alone frequently
    )

    def __repr__(self):
        return f"<TaskResult(id={self.id}, task_name={self.task_name}, status={self.status})>"
