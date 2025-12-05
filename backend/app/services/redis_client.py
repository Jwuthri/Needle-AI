"""
Valkey client for caching and session management.
"""

import json
from typing import Any, Dict, Optional

import valkey
from valkey.asyncio import Valkey as AsyncValkey

from ..config import get_settings
from ..utils.logging import get_logger

logger = get_logger("valkey_client")


class ValkeyClient:
    """Valkey client for caching, session storage, and pub/sub."""

    def __init__(self):
        settings = get_settings()
        self.valkey_url = settings.redis_url  # Still using redis_url setting for backward compatibility
        self.valkey: Optional[AsyncValkey] = None
        self.sync_valkey: Optional[valkey.Valkey] = None
        self._initialized = False
        self._available = False  # Track if Valkey is actually available

    def _check_availability(self, operation: str) -> bool:
        """Check if Valkey is available for the given operation."""
        if not self._available:
            logger.debug(f"Valkey not available, skipping {operation}")
            return False
        return True

    async def initialize(self):
        """Initialize the Redis client (called by DI container)."""
        if not self._initialized:
            await self.connect()
            self._initialized = True

    async def cleanup(self):
        """Cleanup resources (called by DI container)."""
        await self.disconnect()
        self._initialized = False

    async def connect(self):
        """Initialize Valkey connection."""
        try:
            # Valkey connection uses valkeys:// protocol
            self.valkey = AsyncValkey.from_url(
                self.valkey_url,
                encoding="utf-8",
                decode_responses=True,
                health_check_interval=30,
            )

            # Test connection
            await self.valkey.ping()
            logger.info(f"Connected to Valkey at {self.valkey_url.split('@')[-1]}")  # Don't log password

            # Initialize sync client for non-async operations
            self.sync_valkey = valkey.Valkey.from_url(
                self.valkey_url,
                encoding="utf-8",
                decode_responses=True,
            )
            
            self._available = True

        except Exception as e:
            logger.warning(f"Valkey not available: {e}")
            logger.info("Running without Valkey - caching and session features will be disabled")
            self._available = False
            # Don't raise the exception - allow the app to continue without Valkey

    async def disconnect(self):
        """Close Valkey connections."""
        if self.valkey:
            await self.valkey.aclose()
        if self.sync_valkey:
            self.sync_valkey.close()
        logger.info("Disconnected from Valkey")

    async def set(self, key: str, value: Any, expire: Optional[int] = None) -> bool:
        """Set a key-value pair with optional expiration."""
        if not self._check_availability(f"SET {key}"):
            return False
            
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value)

            result = await self.valkey.set(key, value, ex=expire)
            return bool(result)
        except Exception as e:
            logger.error(f"Valkey SET error for key {key}: {e}")
            return False

    async def get(self, key: str) -> Optional[Any]:
        """Get a value by key."""
        if not self._check_availability(f"GET {key}"):
            return None
            
        try:
            value = await self.valkey.get(key)
            if value is None:
                return None

            # Try to parse as JSON, fallback to string
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        except Exception as e:
            logger.error(f"Valkey GET error for key {key}: {e}")
            return None

    async def delete(self, key: str) -> bool:
        """Delete a key."""
        if not self._check_availability(f"DELETE {key}"):
            return False
            
        try:
            result = await self.valkey.delete(key)
            return result > 0
        except Exception as e:
            logger.error(f"Valkey DELETE error for key {key}: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """Check if a key exists."""
        if not self._check_availability(f"EXISTS {key}"):
            return False
            
        try:
            return bool(await self.valkey.exists(key))
        except Exception as e:
            logger.error(f"Valkey EXISTS error for key {key}: {e}")
            return False

    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment a numeric value."""
        if not self._check_availability(f"INCR {key}"):
            return None
            
        try:
            return await self.valkey.incrby(key, amount)
        except Exception as e:
            logger.error(f"Valkey INCR error for key {key}: {e}")
            return None

    async def set_hash(self, key: str, mapping: Dict[str, Any]) -> bool:
        """Set multiple fields in a hash."""
        if not self._check_availability(f"HSET {key}"):
            return False
            
        try:
            # Convert values to strings, JSON-encode complex types
            processed_mapping = {}
            for field, value in mapping.items():
                if isinstance(value, (dict, list)):
                    processed_mapping[field] = json.dumps(value)
                else:
                    processed_mapping[field] = str(value)

            result = await self.valkey.hset(key, mapping=processed_mapping)
            return result is not None
        except Exception as e:
            logger.error(f"Valkey HSET error for key {key}: {e}")
            return False

    async def get_hash(self, key: str) -> Optional[Dict[str, Any]]:
        """Get all fields from a hash."""
        if not self._check_availability(f"HGETALL {key}"):
            return None
            
        try:
            result = await self.valkey.hgetall(key)
            if not result:
                return None

            # Try to parse JSON values
            processed_result = {}
            for field, value in result.items():
                try:
                    processed_result[field] = json.loads(value)
                except json.JSONDecodeError:
                    processed_result[field] = value

            return processed_result
        except Exception as e:
            logger.error(f"Valkey HGETALL error for key {key}: {e}")
            return None

    async def publish(self, channel: str, message: Any) -> int:
        """Publish a message to a Valkey channel."""
        if not self._check_availability(f"PUBLISH {channel}"):
            return 0
            
        try:
            if isinstance(message, (dict, list)):
                message = json.dumps(message)

            result = await self.valkey.publish(channel, message)
            return result
        except Exception as e:
            logger.error(f"Valkey PUBLISH error for channel {channel}: {e}")
            return 0

    async def subscribe(self, channels: list[str]):
        """Subscribe to Valkey channels."""
        if not self._check_availability(f"SUBSCRIBE {channels}"):
            return None
            
        try:
            pubsub = self.valkey.pubsub()
            await pubsub.subscribe(*channels)
            return pubsub
        except Exception as e:
            logger.error(f"Valkey SUBSCRIBE error for channels {channels}: {e}")
            return None

    # Session management methods
    async def store_session(self, session_id: str, session_data: Dict[str, Any], expire: int = 86400) -> bool:
        """Store chat session data."""
        return await self.set(f"session:{session_id}", session_data, expire)

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve chat session data."""
        return await self.get(f"session:{session_id}")

    async def delete_session(self, session_id: str) -> bool:
        """Delete a chat session."""
        return await self.delete(f"session:{session_id}")

    # Cache management methods
    async def cache_response(self, cache_key: str, response: Any, expire: int = 3600) -> bool:
        """Cache an AI response."""
        return await self.set(f"cache:{cache_key}", response, expire)

    async def get_cached_response(self, cache_key: str) -> Optional[Any]:
        """Get a cached AI response."""
        return await self.get(f"cache:{cache_key}")

    async def health_check(self) -> bool:
        """Check Valkey health."""
        if not self._available:
            return False
            
        try:
            await self.valkey.ping()
            return True
        except Exception:
            return False


# Backward compatibility alias
RedisClient = ValkeyClient
