"""
Chat message model for NeedleAi.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship

from ..base import Base


class MessageRoleEnum(str, enum.Enum):
    """Message roles in a conversation."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatMessage(Base):
    """Individual chat message model."""
    __tablename__ = "chat_messages"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("chat_sessions.id"), nullable=False)

    # Message content
    content = Column(Text, nullable=False)
    role = Column(SQLEnum(MessageRoleEnum), nullable=False)

    # Message metadata
    model_name = Column(String(100), nullable=True)  # Model that generated this message (for assistant messages)
    token_count = Column(Integer, default=0)
    processing_time_ms = Column(Integer, nullable=True)  # Time to generate response

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Additional metadata
    extra_metadata = Column(JSON, default={})  # Context, parameters, etc.

    # Parent message for threading (if implemented later)
    parent_message_id = Column(String, ForeignKey("chat_messages.id"), nullable=True)

    # Relationships
    session = relationship("ChatSession", back_populates="messages")
    parent_message = relationship("ChatMessage", remote_side=[id])

    # Essential indexes only (avoid index bloat!)
    __table_args__ = (
        # Most critical: messages in session by time (for chat history)
        Index('ix_chat_message_session_created', 'session_id', 'created_at'),
        # Foreign key index
        Index('ix_chat_message_session_id', 'session_id'),
    )

    def __repr__(self):
        return f"<ChatMessage(id={self.id}, session_id={self.session_id}, role={self.role})>"
