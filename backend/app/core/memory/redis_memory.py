"""
Redis memory implementation for NeedleAi.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from app.core.memory.base import MemoryInterface
from app.exceptions import DatabaseError
from app.models.chat import ChatMessage, ChatSession
from app.services.redis_client import RedisClient


class RedisMemory(MemoryInterface):
    """Redis-based memory storage implementation."""

    def __init__(self, redis_client: RedisClient):
        self.redis = redis_client
        self.session_prefix = "session:"
        self.messages_prefix = "messages:"
        self.user_sessions_prefix = "user_sessions:"

    async def store_session(
        self,
        session_id: str,
        messages: List[ChatMessage],
        metadata: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None
    ) -> bool:
        """Store a chat session in Redis."""
        try:
            session = ChatSession(
                session_id=session_id,
                messages=messages,
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
                metadata=metadata or {}
            )

            # Store session
            session_key = f"{self.session_prefix}{session_id}"
            session_data = session.dict()

            success = await self.redis.set_hash(session_key, session_data)
            if not success:
                return False

            # Store user association if user_id provided
            if user_id:
                user_sessions_key = f"{self.user_sessions_prefix}{user_id}"
                await self.redis.redis.sadd(user_sessions_key, session_id)

            # Store messages separately for efficient querying
            messages_key = f"{self.messages_prefix}{session_id}"
            messages_data = [msg.dict() for msg in messages]
            await self.redis.set(messages_key, messages_data, expire=86400 * 7)  # 7 days

            return True

        except Exception as e:
            raise DatabaseError(f"Failed to store session: {str(e)}")

    async def get_session(
        self,
        session_id: str,
        user_id: Optional[str] = None
    ) -> Optional[ChatSession]:
        """Retrieve a chat session from Redis."""
        try:
            # Check user access if user_id provided
            if user_id:
                user_sessions_key = f"{self.user_sessions_prefix}{user_id}"
                is_member = await self.redis.redis.sismember(user_sessions_key, session_id)
                if not is_member:
                    return None

            # Get session data
            session_key = f"{self.session_prefix}{session_id}"
            session_data = await self.redis.get_hash(session_key)

            if not session_data:
                return None

            # Get messages
            messages_key = f"{self.messages_prefix}{session_id}"
            messages_data = await self.redis.get(messages_key)

            if messages_data:
                messages = [ChatMessage(**msg) for msg in messages_data]
            else:
                messages = []

            return ChatSession(
                session_id=session_data["session_id"],
                messages=messages,
                created_at=session_data.get("created_at"),
                updated_at=session_data.get("updated_at"),
                metadata=session_data.get("metadata", {})
            )

        except Exception as e:
            raise DatabaseError(f"Failed to get session: {str(e)}")

    async def delete_session(
        self,
        session_id: str,
        user_id: Optional[str] = None
    ) -> bool:
        """Delete a chat session from Redis."""
        try:
            # Check user access if user_id provided
            if user_id:
                user_sessions_key = f"{self.user_sessions_prefix}{user_id}"
                is_member = await self.redis.redis.sismember(user_sessions_key, session_id)
                if not is_member:
                    return False

                # Remove from user sessions
                await self.redis.redis.srem(user_sessions_key, session_id)

            # Delete session and messages
            session_key = f"{self.session_prefix}{session_id}"
            messages_key = f"{self.messages_prefix}{session_id}"

            session_deleted = await self.redis.delete(session_key)
            await self.redis.delete(messages_key)

            return session_deleted

        except Exception as e:
            raise DatabaseError(f"Failed to delete session: {str(e)}")

    async def list_sessions(
        self,
        user_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[ChatSession]:
        """List chat sessions from Redis."""
        try:
            sessions = []

            if user_id:
                # Get sessions for specific user
                user_sessions_key = f"{self.user_sessions_prefix}{user_id}"
                session_ids = await self.redis.redis.smembers(user_sessions_key)

                # Apply pagination
                session_ids = list(session_ids)[offset:offset + limit]

                for session_id in session_ids:
                    session = await self.get_session(session_id, user_id)
                    if session:
                        sessions.append(session)
            else:
                # Get all sessions (admin view)
                pattern = f"{self.session_prefix}*"
                keys = []
                async for key in self.redis.redis.scan_iter(match=pattern):
                    keys.append(key)

                # Apply pagination
                keys = keys[offset:offset + limit]

                for key in keys:
                    session_id = key.replace(self.session_prefix, "")
                    session = await self.get_session(session_id)
                    if session:
                        sessions.append(session)

            return sessions

        except Exception as e:
            raise DatabaseError(f"Failed to list sessions: {str(e)}")

    async def add_message(
        self,
        session_id: str,
        message: ChatMessage,
        user_id: Optional[str] = None
    ) -> bool:
        """Add a message to an existing session."""
        try:
            # Get current session
            session = await self.get_session(session_id, user_id)
            if not session:
                return False

            # Add message
            session.messages.append(message)
            session.updated_at = datetime.now().isoformat()

            # Store updated session
            return await self.store_session(
                session_id,
                session.messages,
                session.metadata,
                user_id
            )

        except Exception as e:
            raise DatabaseError(f"Failed to add message: {str(e)}")

    async def get_messages(
        self,
        session_id: str,
        limit: int = 100,
        offset: int = 0,
        user_id: Optional[str] = None
    ) -> List[ChatMessage]:
        """Get messages from a session."""
        try:
            session = await self.get_session(session_id, user_id)
            if not session:
                return []

            # Apply pagination
            messages = session.messages[offset:offset + limit]
            return messages

        except Exception as e:
            raise DatabaseError(f"Failed to get messages: {str(e)}")

    async def clear_session_messages(
        self,
        session_id: str,
        user_id: Optional[str] = None
    ) -> bool:
        """Clear all messages from a session."""
        try:
            # Get current session
            session = await self.get_session(session_id, user_id)
            if not session:
                return False

            # Clear messages
            session.messages = []
            session.updated_at = datetime.now().isoformat()

            # Store updated session
            return await self.store_session(
                session_id,
                session.messages,
                session.metadata,
                user_id
            )

        except Exception as e:
            raise DatabaseError(f"Failed to clear session messages: {str(e)}")

    async def update_session_metadata(
        self,
        session_id: str,
        metadata: Dict[str, Any],
        user_id: Optional[str] = None
    ) -> bool:
        """Update session metadata."""
        try:
            # Get current session
            session = await self.get_session(session_id, user_id)
            if not session:
                return False

            # Update metadata
            session.metadata.update(metadata)
            session.updated_at = datetime.now().isoformat()

            # Store updated session
            return await self.store_session(
                session_id,
                session.messages,
                session.metadata,
                user_id
            )

        except Exception as e:
            raise DatabaseError(f"Failed to update session metadata: {str(e)}")

    async def health_check(self) -> bool:
        """Check Redis health."""
        return await self.redis.health_check()
