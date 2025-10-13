"""
Data import model for user-uploaded files.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship

from ..base import Base


class ImportTypeEnum(str, enum.Enum):
    """Data import types."""
    CSV = "csv"
    JSON = "json"
    XLSX = "xlsx"


class ImportStatusEnum(str, enum.Enum):
    """Import status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DataImport(Base):
    """User-uploaded data import (CSV, JSON, etc.)."""
    __tablename__ = "data_imports"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # References
    company_id = Column(String, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # File details
    file_path = Column(String(500), nullable=False)  # Path to uploaded file
    original_filename = Column(String(255), nullable=False)
    import_type = Column(SQLEnum(ImportTypeEnum), nullable=False)

    # Import status
    status = Column(SQLEnum(ImportStatusEnum), default=ImportStatusEnum.PENDING, nullable=False, index=True)
    rows_imported = Column(Integer, default=0, nullable=False)
    rows_failed = Column(Integer, default=0, nullable=False)

    # Celery task tracking
    celery_task_id = Column(String, nullable=True, index=True)

    # Error handling
    error_message = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    company = relationship("Company", back_populates="data_imports")
    user = relationship("User", back_populates="data_imports")

    # Indexes
    __table_args__ = (
        Index('idx_imports_status_created', 'status', 'created_at'),
        Index('idx_imports_user_created', 'user_id', 'created_at'),
        Index('idx_imports_company', 'company_id', 'created_at'),
        Index('idx_imports_celery_task', 'celery_task_id'),
    )

    def __repr__(self):
        return f"<DataImport(id={self.id}, company_id={self.company_id}, status={self.status}, rows={self.rows_imported})>"

