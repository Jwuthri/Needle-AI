"""
Completion model for NeedleAi.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from ..base import Base


class Completion(Base):
    """LLM completion request and response storage."""
    __tablename__ = "completions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=True)  # Allow anonymous completions

    # Request data
    prompt = Column(Text, nullable=False)
    model_name = Column(String(100), nullable=False)
    system_message = Column(Text, nullable=True)

    # Generation parameters
    max_tokens = Column(Integer, default=100)
    temperature = Column(Float, default=0.7)
    top_p = Column(Float, default=1.0)
    stop_sequences = Column(JSON, default=[])

    # Response data
    completion_text = Column(Text, nullable=True)  # Null if generation failed

    # Usage and performance metrics
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    processing_time_ms = Column(Integer, nullable=True)

    # Status and error tracking
    status = Column(String(50), default="pending")  # pending, completed, failed, cancelled
    error_message = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    # Additional metadata
    extra_metadata = Column(JSON, default={})

    # Relationships
    user = relationship("User", back_populates="completions")

    # Indexes for performance
    __table_args__ = (
        Index('idx_completions_user_created', 'user_id', 'created_at'),
        Index('idx_completions_status', 'status', 'created_at'),
        Index('idx_completions_model', 'model_name', 'created_at'),
    )

    def __repr__(self):
        return f"<Completion(id={self.id}, user_id={self.user_id}, model={self.model_name}, status={self.status})>"
