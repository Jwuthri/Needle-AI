"""
Database-backed chat service for NeedleAi.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from app.config import Settings
from app.core.llm.base import BaseLLMClient
from app.database.models import ChatMessage, ChatSession, MessageRoleEnum
from app.database.repositories import (
    ChatMessageRepository,
    ChatSessionRepository,
    UserRepository,
)
from app.exceptions import LLMError, ValidationError
from app.models.chat import ChatResponse
from app.utils.logging import get_logger
from sqlalchemy.orm import Session

logger = get_logger("database_chat_service")


class DatabaseChatService:
    """Database-backed service for handling chat operations."""

    def __init__(
        self,
        db: Session,
        llm_service: BaseLLMClient,
        settings: Settings
    ):
        self.db = db
        self.llm = llm_service
        self.settings = settings
        self.session_repo = ChatSessionRepository()
        self.message_repo = ChatMessageRepository()
        self.user_repo = UserRepository()

    async def process_message(
        self,
        message: str,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        model_name: Optional[str] = None
    ) -> ChatResponse:
        """
        Process a chat message and generate an AI response using database storage.

        Args:
            message: User's message
            session_id: Optional session ID
            user_id: Optional user ID
            context: Optional context data
            model_name: Optional model name override

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
        max_length = getattr(self.settings, 'max_message_length', 2000)
        if len(message) > max_length:
            raise ValidationError(f"Message too long (max {max_length} characters)")

        # Get or create session
        session = await self._get_or_create_session(session_id, user_id, model_name)

        try:
            # Store user message first
            user_message = self.message_repo.create(
                db=self.db,
                session_id=session.id,
                content=message,
                role=MessageRoleEnum.USER,
                metadata=context or {}
            )

            # Get conversation history for context
            conversation_history = self._get_conversation_history(session.id, limit=20)

            # Generate AI response
            ai_response_content, response_metadata = await self._generate_ai_response(
                message, conversation_history, context, model_name or session.model_name
            )

            # Store AI message
            ai_message = self.message_repo.create(
                db=self.db,
                session_id=session.id,
                content=ai_response_content,
                role=MessageRoleEnum.ASSISTANT,
                model_name=model_name or session.model_name,
                token_count=response_metadata.get('token_count', 0),
                processing_time_ms=response_metadata.get('processing_time_ms'),
                metadata=response_metadata
            )

            # Update session metadata
            self.session_repo.update(
                db=self.db,
                session_id=session.id,
                last_message_at=datetime.utcnow()
            )

            # Update user usage if user exists
            if user_id:
                self.user_repo.increment_usage(
                    db=self.db,
                    user_id=user_id,
                    requests=1,
                    tokens=response_metadata.get('token_count', 0)
                )

            logger.info(f"Processed message in session {session.id}")

            return ChatResponse(
                message=ai_response_content,
                session_id=session.id,
                message_id=ai_message.id,
                timestamp=ai_message.created_at,
                metadata=response_metadata
            )

        except Exception as e:
            logger.error(f"Error processing message in session {session.id}: {str(e)}")
            raise LLMError(f"Failed to process message: {str(e)}")

    async def get_session_history(
        self,
        session_id: str,
        user_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[ChatMessage]:
        """Get chat history for a session."""
        # Verify session exists and user has access
        session = self.session_repo.get_by_id(self.db, session_id)
        if not session:
            raise ValidationError("Session not found")

        if user_id and session.user_id != user_id:
            raise ValidationError("Access denied to this session")

        messages = self.message_repo.get_session_messages(
            db=self.db,
            session_id=session_id,
            limit=limit,
            offset=offset
        )

        return messages

    async def create_session(
        self,
        user_id: Optional[str] = None,
        title: Optional[str] = None,
        system_prompt: Optional[str] = None,
        model_name: Optional[str] = None,
        settings: Optional[Dict[str, Any]] = None
    ) -> ChatSession:
        """Create a new chat session."""
        session = self.session_repo.create(
            db=self.db,
            user_id=user_id,
            title=title or "New Conversation",
            system_prompt=system_prompt,
            model_name=model_name or self.settings.default_model,
            settings=settings or {}
        )

        logger.info(f"Created new chat session: {session.id}")
        return session

    async def get_user_sessions(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
        active_only: bool = True
    ) -> List[ChatSession]:
        """Get user's chat sessions."""
        return self.session_repo.get_user_sessions(
            db=self.db,
            user_id=user_id,
            limit=limit,
            offset=offset,
            active_only=active_only
        )

    async def delete_session(self, session_id: str, user_id: Optional[str] = None) -> bool:
        """Delete/deactivate a chat session."""
        session = self.session_repo.get_by_id(self.db, session_id)
        if not session:
            return False

        if user_id and session.user_id != user_id:
            raise ValidationError("Access denied to this session")

        return self.session_repo.deactivate(self.db, session_id)

    def _get_conversation_history(
        self,
        session_id: str,
        limit: int = 20
    ) -> List[Dict[str, str]]:
        """Get recent conversation history for context."""
        messages = self.message_repo.get_recent_messages(
            db=self.db,
            session_id=session_id,
            limit=limit
        )

        # Convert to format expected by LLM service
        history = []
        for msg in reversed(messages):  # Reverse to get chronological order
            history.append({
                "role": msg.role.value,
                "content": msg.content
            })

        return history

    async def _get_or_create_session(
        self,
        session_id: Optional[str],
        user_id: Optional[str],
        model_name: Optional[str] = None
    ) -> ChatSession:
        """Get existing session or create new one."""
        if session_id:
            session = self.session_repo.get_by_id(self.db, session_id)
            if session:
                # Verify user has access
                if user_id and session.user_id != user_id:
                    raise ValidationError("Access denied to this session")
                return session

        # Create new session
        return self.session_repo.create(
            db=self.db,
            user_id=user_id,
            title="New Conversation",
            model_name=model_name or self.settings.default_model,
            settings={
                "temperature": getattr(self.settings, 'temperature', 0.7),
                "max_tokens": getattr(self.settings, 'max_tokens', 1000)
            }
        )

    async def _generate_ai_response(
        self,
        message: str,
        conversation_history: List[Dict[str, str]],
        context: Optional[Dict[str, Any]] = None,
        model_name: Optional[str] = None
    ) -> tuple[str, Dict[str, Any]]:
        """Generate AI response using the LLM service."""
        start_time = datetime.utcnow()

        try:
            # Prepare messages for LLM
            messages = conversation_history.copy()
            messages.append({"role": "user", "content": message})

            # Generate response
            response = await self.llm.generate_chat_completion(
                messages=messages,
                model=model_name,
                max_tokens=getattr(self.settings, 'max_tokens', 1000),
                temperature=getattr(self.settings, 'temperature', 0.7)
            )

            # Calculate metrics
            end_time = datetime.utcnow()
            processing_time_ms = int((end_time - start_time).total_seconds() * 1000)

            # Extract response content and metadata
            if isinstance(response, dict):
                content = response.get('content', str(response))
                token_count = response.get('usage', {}).get('total_tokens', 0)
            else:
                content = str(response)
                token_count = len(content.split()) * 1.3  # Rough estimate

            metadata = {
                "model": model_name or self.settings.default_model,
                "processing_time_ms": processing_time_ms,
                "token_count": int(token_count),
                "context": context or {}
            }

            return content, metadata

        except Exception as e:
            logger.error(f"AI response generation failed: {str(e)}")
            raise LLMError(f"Failed to generate AI response: {str(e)}")

    async def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """Get statistics for a session."""
        session = self.session_repo.get_by_id(self.db, session_id)
        if not session:
            raise ValidationError("Session not found")

        message_count = self.message_repo.count_session_messages(self.db, session_id)

        return {
            "session_id": session_id,
            "title": session.title,
            "created_at": session.created_at,
            "updated_at": session.updated_at,
            "message_count": message_count,
            "total_tokens": session.total_tokens,
            "is_active": session.is_active,
            "model_name": session.model_name
        }
