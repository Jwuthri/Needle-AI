"""
Conversation service for NeedleAi.
"""

from typing import List, Optional

from app.config import Settings
from app.core.memory.base import MemoryInterface
from app.models.chat import ChatMessage, ChatSession

from ..utils.logging import get_logger

logger = get_logger("conversation_service")


class ConversationService:
    """Service for managing conversations and sessions."""

    def __init__(self, memory_store: MemoryInterface, settings: Settings):
        self.memory = memory_store
        self.settings = settings

    async def get_session(
        self,
        session_id: str,
        user_id: Optional[str] = None
    ) -> Optional[ChatSession]:
        """Get a chat session by ID."""
        try:
            return await self.memory.get_session(session_id, user_id)
        except Exception as e:
            logger.error(f"Error getting session {session_id}: {e}")
            return None

    async def list_sessions(
        self,
        user_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[ChatSession]:
        """List chat sessions."""
        try:
            return await self.memory.list_sessions(user_id, limit, offset)
        except Exception as e:
            logger.error(f"Error listing sessions: {e}")
            return []

    async def delete_session(
        self,
        session_id: str,
        user_id: Optional[str] = None
    ) -> bool:
        """Delete a chat session."""
        try:
            success = await self.memory.delete_session(session_id, user_id)
            if success:
                logger.info(f"Deleted session {session_id}")
            return success
        except Exception as e:
            logger.error(f"Error deleting session {session_id}: {e}")
            return False

    async def get_session_messages(
        self,
        session_id: str,
        user_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[ChatMessage]:
        """Get messages from a session."""
        try:
            return await self.memory.get_messages(session_id, limit, offset, user_id)
        except Exception as e:
            logger.error(f"Error getting messages for session {session_id}: {e}")
            return []

    async def clear_session_messages(
        self,
        session_id: str,
        user_id: Optional[str] = None
    ) -> bool:
        """Clear all messages from a session."""
        try:
            success = await self.memory.clear_session_messages(session_id, user_id)
            if success:
                logger.info(f"Cleared messages for session {session_id}")
            return success
        except Exception as e:
            logger.error(f"Error clearing messages for session {session_id}: {e}")
            return False
