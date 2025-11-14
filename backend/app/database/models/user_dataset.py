"""
UserDataset model for user-uploaded CSV datasets.
"""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

from ..base import Base


class UserDataset(Base):
    """User-uploaded dataset metadata."""
    __tablename__ = "user_datasets"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # User reference
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Dataset metadata
    origin = Column(String(500), nullable=False)  # File path or URL
    description = Column(Text, nullable=True)  # LLM-generated summary
    row_count = Column(Integer, nullable=False, default=0)
    table_name = Column(String(255), nullable=False)  # Actual table name in database (format: __user_{user_id}_{name})
    
    # EDA results (stored as JSON)
    field_metadata = Column(JSON, nullable=True)  # List[FieldMetadata] as JSON
    column_stats = Column(JSON, nullable=True)  # Column statistics
    sample_data = Column(JSON, nullable=True)  # First 5 rows
    vector_store_columns = Column(JSON, nullable=True)  # Columns suitable for vector indexing
    
    # Legacy/additional metadata
    meta = Column(JSON, nullable=True)  # Additional metadata
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="user_datasets")
    
    # Indexes
    __table_args__ = (
        Index('idx_user_datasets_user_created', 'user_id', 'created_at'),
        Index('idx_user_datasets_table_name', 'table_name'),
        Index('idx_user_datasets_user_table', 'user_id', 'table_name'),
    )
    
    def __repr__(self):
        return f"<UserDataset(id={self.id}, user_id={self.user_id}, table_name={self.table_name}, rows={self.row_count})>"

