"""
Model converter utilities for NeedleAi.
"""

from typing import List

from ...models import chat as pydantic_models
from ..models.chat_message import ChatMessage
from ..models.chat_session import ChatSession


class ModelConverter:
    """Convert between database models and Pydantic models."""

    @staticmethod
    def db_session_to_pydantic(db_session: ChatSession) -> pydantic_models.ChatSession:
        """Convert database ChatSession to Pydantic model."""
        messages = [
            pydantic_models.ChatMessage(
                id=msg.id,
                content=msg.content,
                role=pydantic_models.MessageRole(msg.role.value),
                timestamp=msg.created_at,
                metadata=msg.metadata or {}
            )
            for msg in db_session.messages
        ]

        return pydantic_models.ChatSession(
            session_id=db_session.id,
            messages=messages,
            created_at=db_session.created_at,
            updated_at=db_session.updated_at,
            metadata=db_session.extra_metadata or {}
        )

    @staticmethod
    def db_message_to_pydantic(db_message: ChatMessage) -> pydantic_models.ChatMessage:
        """Convert database ChatMessage to Pydantic model."""
        return pydantic_models.ChatMessage(
            id=db_message.id,
            content=db_message.content,
            role=pydantic_models.MessageRole(db_message.role.value),
            timestamp=db_message.created_at,
            metadata=db_message.extra_metadata or {}
        )

    @staticmethod
    def db_messages_to_pydantic(db_messages: List[ChatMessage]) -> List[pydantic_models.ChatMessage]:
        """Convert list of database ChatMessages to Pydantic models."""
        return [
            ModelConverter.db_message_to_pydantic(msg)
            for msg in db_messages
        ]
