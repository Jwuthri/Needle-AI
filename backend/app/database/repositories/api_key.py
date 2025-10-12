"""
API key repository for NeedleAi.
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import desc, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ...utils.logging import get_logger
from ..models.api_key import ApiKey

logger = get_logger("api_key_repository")


class ApiKeyRepository:
    """Repository for ApiKey model operations."""

    @staticmethod
    async def create(
        db: AsyncSession,
        user_id: str,
        name: str,
        key_hash: str,
        prefix: str,
        **kwargs
    ) -> ApiKey:
        """Create a new API key."""
        api_key = ApiKey(
            user_id=user_id,
            name=name,
            key_hash=key_hash,
            prefix=prefix,
            **kwargs
        )
        db.add(api_key)
        await db.flush()
        await db.refresh(api_key)
        logger.info(f"Created API key: {api_key.id} for user: {user_id}")
        return api_key

    @staticmethod
    async def get_by_id(db: AsyncSession, api_key_id: str) -> Optional[ApiKey]:
        """Get API key by ID."""
        result = await db.execute(select(ApiKey).filter(ApiKey.id == api_key_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_key_hash(db: AsyncSession, key_hash: str) -> Optional[ApiKey]:
        """Get API key by hash."""
        result = await db.execute(select(ApiKey).filter(ApiKey.key_hash == key_hash))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_prefix(db: AsyncSession, prefix: str) -> List[ApiKey]:
        """Get API keys by prefix."""
        result = await db.execute(select(ApiKey).filter(ApiKey.prefix == prefix))
        return list(result.scalars().all())

    @staticmethod
    async def get_user_api_keys(
        db: AsyncSession,
        user_id: str,
        active_only: bool = True,
        skip: int = 0,
        limit: int = 50
    ) -> List[ApiKey]:
        """Get user's API keys."""
        query = select(ApiKey).filter(ApiKey.user_id == user_id)

        if active_only:
            query = query.filter(ApiKey.is_active == True)

        query = query.order_by(desc(ApiKey.created_at)).offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_all(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        active_only: bool = False
    ) -> List[ApiKey]:
        """Get all API keys with pagination."""
        query = select(ApiKey)

        if active_only:
            query = query.filter(ApiKey.is_active == True)

        query = query.order_by(desc(ApiKey.created_at)).offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def update(db: AsyncSession, api_key_id: str, **kwargs) -> Optional[ApiKey]:
        """Update API key."""
        api_key = await ApiKeyRepository.get_by_id(db, api_key_id)
        if not api_key:
            return None

        for key, value in kwargs.items():
            if hasattr(api_key, key):
                setattr(api_key, key, value)

        await db.flush()
        await db.refresh(api_key)
        return api_key

    @staticmethod
    async def deactivate(db: AsyncSession, api_key_id: str) -> bool:
        """Deactivate an API key."""
        api_key = await ApiKeyRepository.get_by_id(db, api_key_id)
        if api_key:
            api_key.is_active = False
            await db.flush()
            logger.info(f"Deactivated API key: {api_key_id}")
            return True
        return False

    @staticmethod
    async def delete(db: AsyncSession, api_key_id: str) -> bool:
        """Hard delete an API key."""
        api_key = await ApiKeyRepository.get_by_id(db, api_key_id)
        if api_key:
            await db.delete(api_key)
            await db.flush()
            logger.info(f"Deleted API key: {api_key_id}")
            return True
        return False

    @staticmethod
    async def increment_usage(
        db: AsyncSession,
        api_key_id: str,
        requests: int = 1,
        tokens: int = 0
    ) -> Optional[ApiKey]:
        """Increment API key usage counters."""
        api_key = await ApiKeyRepository.get_by_id(db, api_key_id)
        if api_key:
            api_key.total_requests += requests
            api_key.total_tokens += tokens
            api_key.last_used_at = datetime.utcnow()
            await db.flush()
            await db.refresh(api_key)
        return api_key

    @staticmethod
    async def check_rate_limit(db: AsyncSession, api_key_id: str) -> dict:
        """Check if API key is within rate limits."""
        api_key = await ApiKeyRepository.get_by_id(db, api_key_id)
        if not api_key or not api_key.is_active:
            return {"allowed": False, "reason": "Invalid or inactive API key"}

        # Check if expired
        if api_key.expires_at and api_key.expires_at < datetime.utcnow():
            return {"allowed": False, "reason": "API key expired"}

        # Here you would implement actual rate limiting logic
        # For now, just return allowed
        return {
            "allowed": True,
            "rate_limit_requests": api_key.rate_limit_requests,
            "rate_limit_tokens": api_key.rate_limit_tokens,
            "current_requests": api_key.total_requests,
            "current_tokens": api_key.total_tokens
        }

    @staticmethod
    async def search_api_keys(
        db: AsyncSession,
        search_term: str = None,
        user_id: str = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[ApiKey]:
        """Search API keys by name or prefix."""
        query = select(ApiKey)

        if user_id:
            query = query.filter(ApiKey.user_id == user_id)

        if search_term:
            query = query.filter(
                or_(
                    ApiKey.name.ilike(f"%{search_term}%"),
                    ApiKey.prefix.ilike(f"%{search_term}%")
                )
            )

        query = query.order_by(desc(ApiKey.created_at)).offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())
