"""
In-memory storage implementation for NeedleAi.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from app.core.memory.base import MemoryInterface
from app.models.chat import ChatMessage, ChatSession


class InMemoryStore(MemoryInterface):
    """In-memory storage implementation (for development/fallback)."""

    def __init__(self):
        self.sessions: Dict[str, ChatSession] = {}
        self.user_sessions: Dict[str, set] = {}

    async def store_session(
        self,
        session_id: str,
        messages: List[ChatMessage],
        metadata: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None
    ) -> bool:
        """Store a chat session in memory."""
        try:
            session = ChatSession(
                session_id=session_id,
                messages=messages,
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
                metadata=metadata or {}
            )

            self.sessions[session_id] = session

            # Track user sessions
            if user_id:
                if user_id not in self.user_sessions:
                    self.user_sessions[user_id] = set()
                self.user_sessions[user_id].add(session_id)

            return True

        except Exception:
            return False

    async def get_session(
        self,
        session_id: str,
        user_id: Optional[str] = None
    ) -> Optional[ChatSession]:
        """Retrieve a chat session from memory."""
        # Check user access if user_id provided
        if user_id:
            user_session_ids = self.user_sessions.get(user_id, set())
            if session_id not in user_session_ids:
                return None

        return self.sessions.get(session_id)

    async def delete_session(
        self,
        session_id: str,
        user_id: Optional[str] = None
    ) -> bool:
        """Delete a chat session from memory."""
        # Check user access if user_id provided
        if user_id:
            user_session_ids = self.user_sessions.get(user_id, set())
            if session_id not in user_session_ids:
                return False

            # Remove from user sessions
            user_session_ids.discard(session_id)

        # Delete session
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True

        return False

    async def list_sessions(
        self,
        user_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[ChatSession]:
        """List chat sessions from memory."""
        sessions = []

        if user_id:
            # Get sessions for specific user
            user_session_ids = self.user_sessions.get(user_id, set())
            for session_id in user_session_ids:
                if session_id in self.sessions:
                    sessions.append(self.sessions[session_id])
        else:
            # Get all sessions
            sessions = list(self.sessions.values())

        # Sort by updated_at (most recent first)
        sessions.sort(key=lambda x: x.updated_at, reverse=True)

        # Apply pagination
        return sessions[offset:offset + limit]

    async def add_message(
        self,
        session_id: str,
        message: ChatMessage,
        user_id: Optional[str] = None
    ) -> bool:
        """Add a message to an existing session."""
        session = await self.get_session(session_id, user_id)
        if not session:
            return False

        session.messages.append(message)
        session.updated_at = datetime.now().isoformat()

        return True

    async def get_messages(
        self,
        session_id: str,
        limit: int = 100,
        offset: int = 0,
        user_id: Optional[str] = None
    ) -> List[ChatMessage]:
        """Get messages from a session."""
        session = await self.get_session(session_id, user_id)
        if not session:
            return []

        # Apply pagination
        messages = session.messages[offset:offset + limit]
        return messages

    async def clear_session_messages(
        self,
        session_id: str,
        user_id: Optional[str] = None
    ) -> bool:
        """Clear all messages from a session."""
        session = await self.get_session(session_id, user_id)
        if not session:
            return False

        session.messages = []
        session.updated_at = datetime.now().isoformat()

        return True

    async def update_session_metadata(
        self,
        session_id: str,
        metadata: Dict[str, Any],
        user_id: Optional[str] = None
    ) -> bool:
        """Update session metadata."""
        session = await self.get_session(session_id, user_id)
        if not session:
            return False

        session.metadata.update(metadata)
        session.updated_at = datetime.now().isoformat()

        return True

    async def health_check(self) -> bool:
        """In-memory store is always healthy."""
        return True
