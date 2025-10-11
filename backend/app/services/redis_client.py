"""
Redis client for caching and session management.
"""

import json
import os
from typing import Any, Dict, Optional

from redis import Redis
from redis.asyncio import Redis as AsyncRedis

from ..utils.logging import get_logger

logger = get_logger("redis_client")


class RedisClient:
    """Redis client for caching, session storage, and pub/sub."""

    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.redis: Optional[AsyncRedis] = None
        self.sync_redis: Optional[Redis] = None
        self._initialized = False
        self._available = False  # Track if Redis is actually available

    def _check_availability(self, operation: str) -> bool:
        """Check if Redis is available for the given operation."""
        if not self._available:
            logger.debug(f"Redis not available, skipping {operation}")
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
        """Initialize Redis connection."""
        try:
            self.redis = AsyncRedis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                health_check_interval=30
            )

            # Test connection
            await self.redis.ping()
            logger.info(f"Connected to Redis at {self.redis_url}")

            # Initialize sync client for non-async operations
            self.sync_redis = Redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            
            self._available = True

        except Exception as e:
            logger.warning(f"Redis not available at {self.redis_url}: {e}")
            logger.info("Running without Redis - caching and session features will be disabled")
            self._available = False
            # Don't raise the exception - allow the app to continue without Redis

    async def disconnect(self):
        """Close Redis connections."""
        if self.redis:
            await self.redis.aclose()
        if self.sync_redis:
            self.sync_redis.close()
        logger.info("Disconnected from Redis")

    async def set(self, key: str, value: Any, expire: Optional[int] = None) -> bool:
        """Set a key-value pair with optional expiration."""
        if not self._check_availability(f"SET {key}"):
            return False
            
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value)

            result = await self.redis.set(key, value, ex=expire)
            return bool(result)
        except Exception as e:
            logger.error(f"Redis SET error for key {key}: {e}")
            return False

    async def get(self, key: str) -> Optional[Any]:
        """Get a value by key."""
        if not self._check_availability(f"GET {key}"):
            return None
            
        try:
            value = await self.redis.get(key)
            if value is None:
                return None

            # Try to parse as JSON, fallback to string
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        except Exception as e:
            logger.error(f"Redis GET error for key {key}: {e}")
            return None

    async def delete(self, key: str) -> bool:
        """Delete a key."""
        if not self._check_availability(f"DELETE {key}"):
            return False
            
        try:
            result = await self.redis.delete(key)
            return result > 0
        except Exception as e:
            logger.error(f"Redis DELETE error for key {key}: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """Check if a key exists."""
        if not self._check_availability(f"EXISTS {key}"):
            return False
            
        try:
            return bool(await self.redis.exists(key))
        except Exception as e:
            logger.error(f"Redis EXISTS error for key {key}: {e}")
            return False

    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment a numeric value."""
        if not self._check_availability(f"INCR {key}"):
            return None
            
        try:
            return await self.redis.incrby(key, amount)
        except Exception as e:
            logger.error(f"Redis INCR error for key {key}: {e}")
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

            result = await self.redis.hset(key, mapping=processed_mapping)
            return result is not None
        except Exception as e:
            logger.error(f"Redis HSET error for key {key}: {e}")
            return False

    async def get_hash(self, key: str) -> Optional[Dict[str, Any]]:
        """Get all fields from a hash."""
        if not self._check_availability(f"HGETALL {key}"):
            return None
            
        try:
            result = await self.redis.hgetall(key)
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
            logger.error(f"Redis HGETALL error for key {key}: {e}")
            return None

    async def publish(self, channel: str, message: Any) -> int:
        """Publish a message to a Redis channel."""
        if not self._check_availability(f"PUBLISH {channel}"):
            return 0
            
        try:
            if isinstance(message, (dict, list)):
                message = json.dumps(message)

            result = await self.redis.publish(channel, message)
            return result
        except Exception as e:
            logger.error(f"Redis PUBLISH error for channel {channel}: {e}")
            return 0

    async def subscribe(self, channels: list[str]):
        """Subscribe to Redis channels."""
        if not self._check_availability(f"SUBSCRIBE {channels}"):
            return None
            
        try:
            pubsub = self.redis.pubsub()
            await pubsub.subscribe(*channels)
            return pubsub
        except Exception as e:
            logger.error(f"Redis SUBSCRIBE error for channels {channels}: {e}")
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
        """Check Redis health."""
        if not self._available:
            return False
            
        try:
            await self.redis.ping()
            return True
        except Exception:
            return False
