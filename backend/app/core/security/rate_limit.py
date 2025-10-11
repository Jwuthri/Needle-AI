"""
Rate limiting implementation for NeedleAi.
"""

import time

from app.services.redis_client import RedisClient


class RateLimiter:
    """Redis-based rate limiter."""

    def __init__(
        self,
        redis_client: RedisClient,
        requests_per_minute: int = 60,
        window_seconds: int = 60
    ):
        self.redis = redis_client
        self.requests_per_minute = requests_per_minute
        self.window_seconds = window_seconds

    async def check_rate_limit(self, identifier: str) -> bool:
        """
        Check if the request is within rate limits.

        Args:
            identifier: Unique identifier (IP, user ID, etc.)

        Returns:
            True if request is allowed, False if rate limited
        """
        try:
            key = f"rate_limit:{identifier}"
            current_time = int(time.time())
            window_start = current_time - self.window_seconds

            # Use Redis sorted set with timestamps as scores
            pipe = self.redis.redis.pipeline()

            # Remove old entries
            pipe.zremrangebyscore(key, 0, window_start)

            # Count current requests
            pipe.zcard(key)

            # Add current request
            pipe.zadd(key, {str(current_time): current_time})

            # Set expiration
            pipe.expire(key, self.window_seconds * 2)

            results = await pipe.execute()
            current_count = results[1]  # Count after removing old entries

            return current_count < self.requests_per_minute

        except Exception:
            # If Redis fails, allow the request (fail open)
            return True

    async def get_rate_limit_info(self, identifier: str) -> dict:
        """
        Get rate limit information for an identifier.

        Args:
            identifier: Unique identifier

        Returns:
            Dictionary with rate limit info
        """
        try:
            key = f"rate_limit:{identifier}"
            current_time = int(time.time())
            window_start = current_time - self.window_seconds

            # Clean old entries and count current
            await self.redis.redis.zremrangebyscore(key, 0, window_start)
            current_count = await self.redis.redis.zcard(key)

            remaining = max(0, self.requests_per_minute - current_count)

            return {
                "limit": self.requests_per_minute,
                "remaining": remaining,
                "used": current_count,
                "window_seconds": self.window_seconds,
                "reset_time": current_time + self.window_seconds
            }

        except Exception:
            return {
                "limit": self.requests_per_minute,
                "remaining": self.requests_per_minute,
                "used": 0,
                "window_seconds": self.window_seconds,
                "reset_time": int(time.time()) + self.window_seconds
            }


class InMemoryRateLimiter:
    """In-memory rate limiter for fallback."""

    def __init__(
        self,
        requests_per_minute: int = 60,
        window_seconds: int = 60
    ):
        self.requests_per_minute = requests_per_minute
        self.window_seconds = window_seconds
        self.requests = {}  # identifier -> list of timestamps

    async def check_rate_limit(self, identifier: str) -> bool:
        """Check rate limit using in-memory storage."""
        current_time = time.time()
        window_start = current_time - self.window_seconds

        # Clean old entries
        if identifier in self.requests:
            self.requests[identifier] = [
                timestamp for timestamp in self.requests[identifier]
                if timestamp > window_start
            ]
        else:
            self.requests[identifier] = []

        # Check limit
        if len(self.requests[identifier]) >= self.requests_per_minute:
            return False

        # Add current request
        self.requests[identifier].append(current_time)
        return True

    async def get_rate_limit_info(self, identifier: str) -> dict:
        """Get rate limit info from in-memory storage."""
        current_time = time.time()
        window_start = current_time - self.window_seconds

        # Clean and count
        if identifier in self.requests:
            self.requests[identifier] = [
                timestamp for timestamp in self.requests[identifier]
                if timestamp > window_start
            ]
            current_count = len(self.requests[identifier])
        else:
            current_count = 0

        remaining = max(0, self.requests_per_minute - current_count)

        return {
            "limit": self.requests_per_minute,
            "remaining": remaining,
            "used": current_count,
            "window_seconds": self.window_seconds,
            "reset_time": current_time + self.window_seconds
        }
