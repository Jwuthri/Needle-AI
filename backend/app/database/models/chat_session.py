"""
Chat session model for NeedleAi.
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
    Text,
)
from sqlalchemy.orm import relationship

from ..base import Base


class ChatSession(Base):
    """Chat session model for storing conversations."""
    __tablename__ = "chat_sessions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=True)  # Allow anonymous sessions

    # Session metadata
    title = Column(String(500), nullable=True)  # Auto-generated or user-set title
    system_prompt = Column(Text, nullable=True)  # Custom system prompt for this session
    model_name = Column(String(100), nullable=True)  # LLM model used

    # Session state
    is_active = Column(Boolean, default=True)
    message_count = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_message_at = Column(DateTime, nullable=True)

    # Session settings and metadata
    settings = Column(JSON, default={})  # Temperature, max_tokens, etc.
    extra_metadata = Column(JSON, default={})  # Additional session data

    # Relationships
    user = relationship("User", back_populates="chat_sessions")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan", order_by="ChatMessage.created_at")

    # Essential indexes only (avoid index bloat!)
    __table_args__ = (
        # Most critical: user sessions lookup with sorting
        Index('ix_chat_session_user_updated', 'user_id', 'updated_at'),
        # Foreign key index (automatically created in many DBs but explicit is better)
        Index('ix_chat_session_user_id', 'user_id'),
    )

    def __repr__(self):
        return f"<ChatSession(id={self.id}, user_id={self.user_id}, messages={self.message_count})>"
