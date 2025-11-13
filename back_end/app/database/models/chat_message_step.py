"""ChatMessageStep database model."""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship

from app.database.base import Base


class ChatMessageStep(Base):
    """ChatMessageStep model representing sub-steps within a chat message."""

    __tablename__ = "chat_message_steps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id = Column(
        UUID(as_uuid=True),
        ForeignKey("chat_messages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    step_type = Column(
        String, nullable=False
    )  # 'thinking', 'tool_call', 'retrieval', etc.
    content = Column(String, nullable=True)
    metadata_ = Column("metadata", JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    message = relationship("ChatMessage", back_populates="steps")

    def __repr__(self) -> str:
        return f"<ChatMessageStep(id={self.id}, step_type={self.step_type})>"
