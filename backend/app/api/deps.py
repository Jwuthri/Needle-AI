"""
API-specific dependencies for NeedleAi.
"""

from typing import AsyncGenerator, Optional

from app.config import Settings, get_settings
from app.core.security.rate_limit import RateLimiter
from app.database.session import get_async_db_session
from app.dependencies import (
    get_chat_service,
    get_conversation_service,
    get_redis_client,
    get_llm_client,  # noqa: F401
)
from app.services.conversation_service import ConversationService
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession


# Use DI container services directly
async def get_chat_service_dep(
    chat_service = Depends(get_chat_service)
):
    """Get chat service instance from DI container."""
    return chat_service


async def get_conversation_service_dep(
    conversation_service: ConversationService = Depends(get_conversation_service)
) -> ConversationService:
    """Get conversation service instance from DI container."""
    return conversation_service


async def get_rate_limiter(
    settings: Settings = Depends(get_settings),
    redis_client = Depends(get_redis_client)
) -> RateLimiter:
    """Get rate limiter instance."""
    return RateLimiter(
        redis_client=redis_client,
        requests_per_minute=settings.rate_limit_requests,
        window_seconds=settings.rate_limit_window
    )


def get_user_id_from_header(
    x_user_id: Optional[str] = Header(None, alias="X-User-ID")
) -> Optional[str]:
    """Extract user ID from headers."""
    return x_user_id


def get_client_ip(
    x_forwarded_for: Optional[str] = Header(None, alias="X-Forwarded-For"),
    x_real_ip: Optional[str] = Header(None, alias="X-Real-IP")
) -> str:
    """Get client IP address from headers."""
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    if x_real_ip:
        return x_real_ip
    return "unknown"


async def verify_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    settings: Settings = Depends(get_settings)
) -> Optional[str]:
    """Verify API key if provided (optional authentication)."""
    if not x_api_key:
        return None

    # In production, verify against a database or service
    # For now, just check against a setting
    valid_api_keys = getattr(settings, "api_keys", [])

    if valid_api_keys and x_api_key not in valid_api_keys:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )

    return x_api_key


async def check_rate_limit(
    client_ip: str = Depends(get_client_ip),
    rate_limiter: RateLimiter = Depends(get_rate_limiter)
) -> None:
    """Check rate limit for the client."""
    if not await rate_limiter.check_rate_limit(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={"Retry-After": "60"}
        )


def validate_session_id(session_id: str) -> str:
    """Validate session ID format."""
    if not session_id or len(session_id) < 8 or len(session_id) > 128:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session ID format"
        )

    # Basic format validation (alphanumeric + hyphens/underscores)
    if not all(c.isalnum() or c in "-_" for c in session_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session ID contains invalid characters"
        )

    return session_id


# Database session dependency (async)
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Get async database session for dependency injection.
    
    This is the recommended way to get database sessions in FastAPI endpoints.
    
    Yields:
        AsyncSession: Async SQLAlchemy database session
    """
    async for session in get_async_db_session():
        yield session
