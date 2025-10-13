"""
Chat Message Step model for tracking agent execution steps.
"""

import uuid
from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from ..base import Base


class ChatMessageStep(Base):
    """
    Individual step in agent execution for a chat message.
    
    Tracks intermediate agent outputs during message processing.
    Each step represents one agent's contribution to the final response.
    """
    __tablename__ = "chat_message_steps"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Link to the assistant's chat message
    message_id = Column(String, ForeignKey("chat_messages.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Agent information
    agent_name = Column(String(255), nullable=False)
    
    # Step ordering (0-indexed)
    step_order = Column(Integer, nullable=False)
    
    # Content storage - one of these will be populated
    tool_call = Column(JSON, nullable=True)  # For structured outputs (BaseModel)
    prediction = Column(Text, nullable=True)  # For text outputs
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    message = relationship("ChatMessage", back_populates="steps")

    def __repr__(self):
        return f"<ChatMessageStep(id={self.id}, message_id={self.message_id}, agent={self.agent_name}, order={self.step_order})>"

