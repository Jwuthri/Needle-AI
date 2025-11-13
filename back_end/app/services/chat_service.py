"""Chat service for business logic."""

from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from back_end.app.database.repositories.chat_session import ChatSessionRepository
from back_end.app.database.repositories.chat_message import ChatMessageRepository
from back_end.app.database.repositories.chat_message_step import ChatMessageStepRepository
from back_end.app.models.chat import (
    ChatRequest,
    ChatResponse,
    ChatSessionResponse,
    ChatMessageResponse,
)


class ChatService:
    """Service for managing chat sessions and messages."""

    def __init__(
        self,
        session: AsyncSession,
        chat_session_repo: ChatSessionRepository,
        chat_message_repo: ChatMessageRepository,
        chat_message_step_repo: ChatMessageStepRepository,
    ):
        """
        Initialize chat service.

        Args:
            session: Database session for transactions
            chat_session_repo: Repository for chat sessions
            chat_message_repo: Repository for chat messages
            chat_message_step_repo: Repository for chat message steps
        """
        self.session = session
        self.chat_session_repo = chat_session_repo
        self.chat_message_repo = chat_message_repo
        self.chat_message_step_repo = chat_message_step_repo

    async def send_message(
        self,
        user_id: UUID,
        message: str,
        session_id: Optional[UUID] = None,
        company_id: Optional[UUID] = None,
    ) -> ChatResponse:
        """
        Send a chat message and receive AI response.

        Args:
            user_id: User identifier
            message: User's message content
            session_id: Existing session identifier (creates new if not provided)
            company_id: Company context for the chat

        Returns:
            ChatResponse with AI assistant's response

        Raises:
            ValueError: If session_id is provided but doesn't exist
        """
        # Create or get session
        if session_id is None:
            session = await self.chat_session_repo.create(
                user_id=user_id,
                company_id=company_id,
                title=message[:50] if len(message) > 50 else message,
            )
            session_id = session.id
        else:
            # Verify session exists
            existing_session = await self.chat_session_repo.get_by_id(session_id)
            if existing_session is None:
                raise ValueError(f"Chat session {session_id} not found")

        # Save user message
        user_message = await self.chat_message_repo.create(
            session_id=session_id,
            role="user",
            content=message,
            metadata={"source": "api"},
        )

        # TODO: Integrate with LLM service for actual AI response
        # For now, return a placeholder response
        ai_response_content = self._generate_placeholder_response(message)

        # Save AI message
        ai_message = await self.chat_message_repo.create(
            session_id=session_id,
            role="assistant",
            content=ai_response_content,
            metadata={
                "model": "placeholder",
                "tokens_used": 0,
                "processing_time_ms": 0,
            },
        )

        # Commit transaction
        await self.session.commit()

        return ChatResponse(
            message=ai_response_content,
            session_id=session_id,
            message_id=ai_message.id,
            metadata_={
                "model": "placeholder",
                "tokens_used": 0,
                "processing_time_ms": 0,
            },
        )

    def _generate_placeholder_response(self, user_message: str) -> str:
        """
        Generate a placeholder AI response.

        This is a temporary implementation until LLM integration is complete.

        Args:
            user_message: User's message

        Returns:
            Placeholder response string
        """
        return (
            f"Thank you for your message. This is a placeholder response. "
            f"LLM integration will be implemented in a future update. "
            f"Your message was: '{user_message[:50]}...'"
        )

    async def get_session(self, session_id: UUID) -> Optional[ChatSessionResponse]:
        """
        Get a chat session by ID.

        Args:
            session_id: Session identifier

        Returns:
            ChatSessionResponse or None if not found
        """
        session = await self.chat_session_repo.get_by_id(session_id)
        if session is None:
            return None
        return ChatSessionResponse.model_validate(session)

    async def get_session_messages(
        self, session_id: UUID, skip: int = 0, limit: int = 100
    ) -> list[ChatMessageResponse]:
        """
        Get all messages for a chat session.

        Args:
            session_id: Session identifier
            skip: Number of messages to skip
            limit: Maximum number of messages to return

        Returns:
            List of chat messages
        """
        messages = await self.chat_message_repo.get_by_session_id(
            session_id, skip=skip, limit=limit
        )
        return [ChatMessageResponse.model_validate(msg) for msg in messages]

    async def get_user_sessions(
        self, user_id: UUID, skip: int = 0, limit: int = 50
    ) -> list[ChatSessionResponse]:
        """
        Get all chat sessions for a user.

        Args:
            user_id: User identifier
            skip: Number of sessions to skip
            limit: Maximum number of sessions to return

        Returns:
            List of chat sessions
        """
        sessions = await self.chat_session_repo.get_by_user_id(
            user_id, skip=skip, limit=limit
        )
        return [ChatSessionResponse.model_validate(session) for session in sessions]

    async def delete_session(self, session_id: UUID) -> bool:
        """
        Delete a chat session and all associated messages.

        Args:
            session_id: Session identifier

        Returns:
            True if deleted, False if not found
        """
        result = await self.chat_session_repo.delete(session_id)
        if result:
            await self.session.commit()
        return result
