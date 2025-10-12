"""
Chat service for NeedleAi.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from app.config import Settings
from app.core.llm.base import BaseLLMClient
from app.core.memory.base import MemoryInterface
from app.exceptions import LLMError, ValidationError
from app.models.chat import ChatMessage, ChatResponse

from ..utils.logging import get_logger

logger = get_logger("chat_service")


class ChatService:
    """Service for handling chat operations."""

    def __init__(
        self,
        memory_store: MemoryInterface,
        llm_service: BaseLLMClient,
        settings: Settings
    ):
        self.memory = memory_store
        self.llm = llm_service
        self.settings = settings

    async def process_message(
        self,
        message: str,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> ChatResponse:
        """
        Process a chat message and generate an AI response.

        Args:
            message: User's message
            session_id: Optional session ID
            user_id: Optional user ID
            context: Optional context data

        Returns:
            ChatResponse with AI-generated response

        Raises:
            ValidationError: If message is invalid
            LLMError: If AI generation fails
        """
        # Validate message
        if not message or not message.strip():
            raise ValidationError("Message cannot be empty")

        message = message.strip()
        if len(message) > 2000:  # Configurable limit
            raise ValidationError("Message too long")

        # Generate session ID if not provided
        if not session_id:
            session_id = str(uuid.uuid4())

        try:
            # Get conversation history
            conversation_history = await self._get_conversation_history(session_id, user_id)

            # Create user message
            user_message = ChatMessage(
                id=str(uuid.uuid4()),
                content=message,
                role="user",
                timestamp=datetime.now().isoformat(),
                metadata=context
            )

            # Generate AI response
            ai_response_content = await self._generate_ai_response(
                message, conversation_history, context
            )

            # Create AI message
            ai_message = ChatMessage(
                id=str(uuid.uuid4()),
                content=ai_response_content,
                role="assistant",
                timestamp=datetime.now().isoformat()
            )

            # Store messages in memory
            await self._store_messages(session_id, [user_message, ai_message], user_id)

            # Publish events (if needed)
            await self._publish_chat_events(session_id, user_message, ai_message, user_id)

            return ChatResponse(
                message=ai_response_content,
                session_id=session_id,
                message_id=ai_message.id,
                timestamp=ai_message.timestamp
            )

        except LLMError:
            # Re-raise LLM errors
            raise
        except Exception as e:
            logger.error(f"Error processing chat message: {e}")
            raise LLMError(f"Failed to process message: {str(e)}")

    async def _get_conversation_history(
        self,
        session_id: str,
        user_id: Optional[str] = None
    ) -> list[ChatMessage]:
        """Get conversation history for context."""
        try:
            session = await self.memory.get_session(session_id, user_id)
            if session:
                # Return last 10 messages for context
                return session.messages[-10:]
            return []
        except Exception as e:
            logger.warning(f"Failed to get conversation history: {e}")
            return []

    async def _generate_ai_response(
        self,
        message: str,
        conversation_history: list[ChatMessage],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate AI response using the LLM."""
        try:
            # Prepare system prompt if needed
            system_prompt = self._get_system_prompt(context)

            response = await self.llm.generate_response(
                message=message,
                conversation_history=conversation_history,
                system_prompt=system_prompt
            )

            return response

        except Exception as e:
            logger.error(f"LLM generation error: {e}")
            raise LLMError(f"Failed to generate AI response: {str(e)}")

    async def _store_messages(
        self,
        session_id: str,
        messages: list[ChatMessage],
        user_id: Optional[str] = None
    ):
        """Store messages in memory."""
        try:
            # Get existing session
            session = await self.memory.get_session(session_id, user_id)

            if session:
                # Add new messages to existing session
                for message in messages:
                    await self.memory.add_message(session_id, message, user_id)
            else:
                # Create new session with messages
                await self.memory.store_session(
                    session_id, messages, user_id=user_id
                )

        except Exception as e:
            logger.error(f"Failed to store messages: {e}")
            # Don't raise - this shouldn't block the response

    async def _publish_chat_events(
        self,
        session_id: str,
        user_message: ChatMessage,
        ai_message: ChatMessage,
        user_id: Optional[str] = None
    ):
        """Publish chat events for analytics/monitoring."""
        try:
            # This uses Celery tasks for async processing
            # For now, just log the events
            logger.info(
                "Chat event",
                extra={
                    "session_id": session_id,
                    "user_id": user_id,
                    "user_message_length": len(user_message.content),
                    "ai_message_length": len(ai_message.content),
                    "timestamp": datetime.now().isoformat()
                }
            )
        except Exception as e:
            logger.warning(f"Failed to publish chat events: {e}")
            # Don't raise - this shouldn't block the response

    def _get_system_prompt(self, context: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """Get system prompt based on context."""
        base_prompt = "You are a helpful AI assistant. Provide clear, concise, and helpful responses."

        if not context:
            return base_prompt

        # Customize prompt based on context
        if context.get("domain"):
            base_prompt += f" You are specialized in {context['domain']}."

        if context.get("language"):
            base_prompt += f" Respond in {context['language']}."

        if context.get("tone"):
            base_prompt += f" Use a {context['tone']} tone."

        return base_prompt
