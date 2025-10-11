"""
Base memory interface for NeedleAi.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from app.models.chat import ChatMessage, ChatSession


class MemoryInterface(ABC):
    """Base interface for memory storage implementations."""

    @abstractmethod
    async def store_session(
        self,
        session_id: str,
        messages: List[ChatMessage],
        metadata: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None
    ) -> bool:
        """
        Store a chat session with messages.

        Args:
            session_id: Unique session identifier
            messages: List of chat messages
            metadata: Optional session metadata
            user_id: Optional user identifier

        Returns:
            True if successful, False otherwise
        """

    @abstractmethod
    async def get_session(
        self,
        session_id: str,
        user_id: Optional[str] = None
    ) -> Optional[ChatSession]:
        """
        Retrieve a chat session.

        Args:
            session_id: Session identifier
            user_id: Optional user identifier for access control

        Returns:
            ChatSession if found, None otherwise
        """

    @abstractmethod
    async def delete_session(
        self,
        session_id: str,
        user_id: Optional[str] = None
    ) -> bool:
        """
        Delete a chat session.

        Args:
            session_id: Session identifier
            user_id: Optional user identifier for access control

        Returns:
            True if successful, False otherwise
        """

    @abstractmethod
    async def list_sessions(
        self,
        user_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[ChatSession]:
        """
        List chat sessions.

        Args:
            user_id: Optional user identifier to filter sessions
            limit: Maximum number of sessions to return
            offset: Number of sessions to skip

        Returns:
            List of chat sessions
        """

    @abstractmethod
    async def add_message(
        self,
        session_id: str,
        message: ChatMessage,
        user_id: Optional[str] = None
    ) -> bool:
        """
        Add a message to an existing session.

        Args:
            session_id: Session identifier
            message: Chat message to add
            user_id: Optional user identifier for access control

        Returns:
            True if successful, False otherwise
        """

    @abstractmethod
    async def get_messages(
        self,
        session_id: str,
        limit: int = 100,
        offset: int = 0,
        user_id: Optional[str] = None
    ) -> List[ChatMessage]:
        """
        Get messages from a session.

        Args:
            session_id: Session identifier
            limit: Maximum number of messages to return
            offset: Number of messages to skip
            user_id: Optional user identifier for access control

        Returns:
            List of chat messages
        """

    @abstractmethod
    async def clear_session_messages(
        self,
        session_id: str,
        user_id: Optional[str] = None
    ) -> bool:
        """
        Clear all messages from a session while keeping the session.

        Args:
            session_id: Session identifier
            user_id: Optional user identifier for access control

        Returns:
            True if successful, False otherwise
        """

    @abstractmethod
    async def update_session_metadata(
        self,
        session_id: str,
        metadata: Dict[str, Any],
        user_id: Optional[str] = None
    ) -> bool:
        """
        Update session metadata.

        Args:
            session_id: Session identifier
            metadata: New metadata to set
            user_id: Optional user identifier for access control

        Returns:
            True if successful, False otherwise
        """

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the memory store is healthy.

        Returns:
            True if healthy, False otherwise
        """
