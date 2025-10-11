"""
API key model for NeedleAi.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.orm import relationship

from ..base import Base


class ApiKey(Base):
    """API key management for external access."""
    __tablename__ = "api_keys"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)

    # Key details
    name = Column(String(255), nullable=False)  # Human-readable name
    key_hash = Column(String(255), nullable=False, unique=True)  # Hashed API key
    prefix = Column(String(20), nullable=False)  # First few chars for identification

    # Permissions and limits
    is_active = Column(Boolean, default=True)
    permissions = Column(JSON, default=["chat", "completions"])  # Allowed endpoints
    rate_limit_requests = Column(Integer, default=100)  # Requests per minute
    rate_limit_tokens = Column(Integer, default=10000)  # Tokens per day

    # Usage tracking
    total_requests = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    last_used_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True)

    # Metadata
    extra_metadata = Column(JSON, default={})

    # Relationships
    user = relationship("User")

    # Indexes
    __table_args__ = (
        Index('idx_api_keys_user', 'user_id', 'is_active'),
        Index('idx_api_keys_prefix', 'prefix'),
    )

    def __repr__(self):
        return f"<ApiKey(id={self.id}, name={self.name}, user_id={self.user_id}, active={self.is_active})>"
