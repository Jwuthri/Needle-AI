"""
Clerk authentication integration for NeedleAi.
"""

from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Dict, Optional, Tuple

import httpx
import jwt
from app.config import Settings, get_settings
from app.exceptions import UnauthorizedError, ValidationError
from app.utils.logging import get_logger
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger("clerk_auth")

# HTTP Bearer token security scheme
security = HTTPBearer(auto_error=False)


class ClerkUser:
    """Represents a Clerk user with essential information."""

    def __init__(self, user_data: Dict[str, Any]):
        self.id: str = user_data.get("sub", "")
        self.email: str = user_data.get("email", "")
        self.username: str = user_data.get("username", "")
        self.first_name: str = user_data.get("given_name", "")
        self.last_name: str = user_data.get("family_name", "")
        self.full_name: str = f"{self.first_name} {self.last_name}".strip()
        self.image_url: str = user_data.get("picture", "")
        self.created_at: Optional[datetime] = None
        self.updated_at: Optional[datetime] = None
        self.metadata: Dict[str, Any] = user_data.get("public_metadata", {})
        self.raw_data: Dict[str, Any] = user_data

        # Parse timestamps if available
        if "iat" in user_data:
            self.created_at = datetime.fromtimestamp(user_data["iat"])
        if "exp" in user_data:
            self.updated_at = datetime.fromtimestamp(user_data["exp"])

    def to_dict(self) -> Dict[str, Any]:
        """Convert user to dictionary representation."""
        return {
            "id": self.id,
            "email": self.email,
            "username": self.username,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.full_name,
            "image_url": self.image_url,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "metadata": self.metadata
        }


class ClerkAuthProvider:
    """Clerk authentication provider for JWT verification."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.jwks_cache: Optional[Dict[str, Any]] = None
        self.jwks_cache_expiry: Optional[datetime] = None
        
        # Construct JWKS URL based on configuration
        if settings.clerk_frontend_api_url:
            # Use Frontend API URL + /.well-known/jwks.json
            self.jwks_url = f"{settings.clerk_frontend_api_url.rstrip('/')}/.well-known/jwks.json"
            logger.info(f"Using Clerk Frontend API for JWKS: {self.jwks_url}")
        else:
            # Fall back to Backend API endpoint (works for all instances)
            self.jwks_url = "https://api.clerk.com/v1/jwks"
            logger.info("Using Clerk Backend API for JWKS (no frontend API URL configured)")

    async def get_jwks(self) -> Dict[str, Any]:
        """Get JWKS (JSON Web Key Set) from Clerk, with caching."""
        now = datetime.utcnow()

        # Return cached JWKS if still valid (cache for 1 hour)
        if (self.jwks_cache and
            self.jwks_cache_expiry and
            now < self.jwks_cache_expiry):
            return self.jwks_cache

        try:
            # Prepare headers - Backend API requires authentication
            headers = {}
            if "api.clerk.com" in self.jwks_url and self.settings.clerk_secret_key:
                headers["Authorization"] = f"Bearer {self.settings.clerk_secret_key}"
            
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(self.jwks_url, headers=headers, timeout=10.0)
                response.raise_for_status()

                self.jwks_cache = response.json()
                self.jwks_cache_expiry = now + timedelta(hours=1)

                logger.info("Successfully fetched JWKS from Clerk")
                return self.jwks_cache

        except Exception as e:
            logger.error(f"Failed to fetch JWKS from Clerk: {e}")
            # If we have a cached version, use it even if expired
            if self.jwks_cache:
                logger.warning("Using expired JWKS cache due to fetch failure")
                return self.jwks_cache
            raise UnauthorizedError("Unable to verify authentication token")

    async def verify_token(self, token: str) -> ClerkUser:
        """Verify JWT token and return user information."""
        try:
            # Decode token header to get kid (key ID)
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")

            if not kid:
                raise UnauthorizedError("Token missing key ID")

            # Get JWKS from Clerk
            jwks = await self.get_jwks()

            # Find the key with matching kid
            signing_key = None
            for key in jwks.get("keys", []):
                if key.get("kid") == kid:
                    signing_key = jwt.algorithms.RSAAlgorithm.from_jwk(key)
                    break

            if not signing_key:
                raise UnauthorizedError("Unable to find signing key")

            # Verify and decode the token
            decoded_token = jwt.decode(
                token,
                signing_key,
                algorithms=["RS256"],
                options={"verify_aud": False}  # Clerk doesn't use standard aud claim
            )

            # Debug: Log what fields we got from Clerk
            logger.debug(f"Clerk JWT fields: {list(decoded_token.keys())}")
            logger.debug(f"Clerk JWT data: {decoded_token}")

            # Create ClerkUser from JWT
            user = ClerkUser(decoded_token)
            
            # If email is missing, fetch full user details from Clerk API
            if not user.email or not user.full_name:
                logger.info(f"JWT missing user details, fetching from Clerk API for user: {user.id}")
                try:
                    full_user_data = await self.get_user_by_id(user.id)
                    if full_user_data:
                        # Merge API data with JWT data
                        decoded_token.update({
                            "email": full_user_data.get("email_addresses", [{}])[0].get("email_address", ""),
                            "username": full_user_data.get("username", ""),
                            "given_name": full_user_data.get("first_name", ""),
                            "family_name": full_user_data.get("last_name", ""),
                            "picture": full_user_data.get("image_url", ""),
                        })
                        user = ClerkUser(decoded_token)
                        logger.info(f"Fetched full user details from Clerk API")
                except Exception as e:
                    logger.warning(f"Failed to fetch full user details: {e}")
            
            logger.info(f"Successfully verified token for user: {user.id} (email: {user.email})")

            return user

        except ExpiredSignatureError:
            raise UnauthorizedError("Token has expired")
        except InvalidTokenError as e:
            raise UnauthorizedError(f"Invalid token: {str(e)}")
        except Exception as e:
            logger.error(f"Token verification error: {e}")
            raise UnauthorizedError("Token verification failed")

    async def get_user_by_id(self, user_id: str) -> Optional[ClerkUser]:
        """Get user information from Clerk API by user ID."""
        if not self.settings.clerk_secret_key:
            raise ValidationError("Clerk secret key not configured")

        try:
            headers = {
                "Authorization": f"Bearer {self.settings.clerk_secret_key}",
                "Content-Type": "application/json"
            }

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://api.clerk.com/v1/users/{user_id}",
                    headers=headers,
                    timeout=10.0
                )

                if response.status_code == 404:
                    return None

                response.raise_for_status()
                user_data = response.json()

                # Convert Clerk API response to JWT-like format
                jwt_like_data = {
                    "sub": user_data.get("id"),
                    "email": user_data.get("email_addresses", [{}])[0].get("email_address", ""),
                    "username": user_data.get("username", ""),
                    "given_name": user_data.get("first_name", ""),
                    "family_name": user_data.get("last_name", ""),
                    "picture": user_data.get("image_url", ""),
                    "public_metadata": user_data.get("public_metadata", {}),
                    "iat": int(datetime.fromisoformat(user_data.get("created_at", "1970-01-01T00:00:00Z").replace("Z", "+00:00")).timestamp()) if user_data.get("created_at") else None,
                }

                return ClerkUser(jwt_like_data)

        except Exception as e:
            logger.error(f"Failed to get user from Clerk API: {e}")
            return None


# Global Clerk auth provider instance
_clerk_provider: Optional[ClerkAuthProvider] = None

def get_clerk_provider(settings: Settings = Depends(get_settings)) -> ClerkAuthProvider:
    """Get Clerk authentication provider instance."""
    global _clerk_provider
    if _clerk_provider is None:
        _clerk_provider = ClerkAuthProvider(settings)
    return _clerk_provider


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    clerk_provider: ClerkAuthProvider = Depends(get_clerk_provider)
) -> Optional[ClerkUser]:
    """
    Get current authenticated user from JWT token.
    Returns None if no token provided (for optional authentication).
    """
    if not credentials:
        return None

    try:
        user = await clerk_provider.verify_token(credentials.credentials)
        return user
    except UnauthorizedError:
        return None


async def require_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    clerk_provider: ClerkAuthProvider = Depends(get_clerk_provider)
) -> ClerkUser:
    """
    Get current authenticated user from JWT token.
    Raises HTTPException if no valid token provided.
    """
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )

    try:
        user = await clerk_provider.verify_token(credentials.credentials)
        return user
    except UnauthorizedError as e:
        raise HTTPException(
            status_code=401,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"}
        )


async def _get_db_session():
    """Internal helper to get database session."""
    from app.database.session import get_async_db_session
    async for session in get_async_db_session():
        yield session


async def get_current_db_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    clerk_provider: ClerkAuthProvider = Depends(get_clerk_provider),
    db: AsyncSession = Depends(_get_db_session)
) -> Optional[Tuple[ClerkUser, Optional["User"]]]:
    """
    Get current authenticated user and sync to database.
    Returns tuple of (ClerkUser, database User) or None if not authenticated.
    
    Note: This automatically creates/updates the user in the database on every auth.
    
    Args:
        credentials: HTTP Bearer token credentials
        clerk_provider: Clerk authentication provider
        db: Database session (injected automatically)
    
    Returns:
        Tuple of (ClerkUser, User) or None if no auth
    """
    if not credentials:
        return None

    try:
        from app.database.models.user import User
        from app.services.user_sync_service import UserSyncService
        
        # Verify Clerk token
        clerk_user = await clerk_provider.verify_token(credentials.credentials)
        
        # Sync to database
        db_user = None
        try:
            db_user = await UserSyncService.sync_clerk_user(db, clerk_user, commit=False)
            await db.commit()  # Explicitly commit the transaction
            logger.debug(f"Synced user {clerk_user.id} to database")
        except Exception as e:
            logger.error(f"Failed to sync user {clerk_user.id} to database: {e}")
            await db.rollback()
            # Don't fail auth if DB sync fails - graceful degradation
        
        return (clerk_user, db_user)
    except UnauthorizedError:
        return None


async def require_current_db_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    clerk_provider: ClerkAuthProvider = Depends(get_clerk_provider),
    db: AsyncSession = Depends(_get_db_session)
) -> Tuple[ClerkUser, "User"]:
    """
    Get current authenticated user and sync to database (required).
    Raises HTTPException if no valid token provided.
    
    Note: This automatically creates/updates the user in the database on every auth.
    
    Args:
        credentials: HTTP Bearer token credentials
        clerk_provider: Clerk authentication provider
        db: Database session (injected automatically)
    
    Returns:
        Tuple of (ClerkUser, database User)
    
    Raises:
        HTTPException: If authentication fails or database sync fails
    """
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )

    try:
        from app.database.models.user import User
        from app.services.user_sync_service import UserSyncService
        
        # Verify Clerk token
        clerk_user = await clerk_provider.verify_token(credentials.credentials)
        
        # Sync to database (required)
        try:
            db_user = await UserSyncService.sync_clerk_user(db, clerk_user, commit=False)
            await db.commit()  # Explicitly commit the transaction
            logger.info(f"Synced user {clerk_user.id} ({clerk_user.email}) to database")
        except Exception as e:
            logger.error(f"Failed to sync user {clerk_user.id} to database: {e}", exc_info=True)
            await db.rollback()
            raise HTTPException(
                status_code=500,
                detail="Failed to sync user to database"
            )
        
        return (clerk_user, db_user)
    except UnauthorizedError as e:
        raise HTTPException(
            status_code=401,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"}
        )


def require_auth(func):
    """
    Decorator to require authentication for a function.

    Usage:
        @router.get("/protected")
        @require_auth
        async def protected_endpoint(user: ClerkUser = Depends(require_current_user)):
            return {"user_id": user.id}
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # The authentication is handled by the require_current_user dependency
        return await func(*args, **kwargs)
    return wrapper


async def validate_clerk_config(settings: Settings) -> bool:
    """Validate Clerk configuration."""
    if not settings.clerk_publishable_key:
        logger.warning("Clerk publishable key not configured")
        return False

    if not settings.clerk_secret_key:
        logger.warning("Clerk secret key not configured")
        return False

    if not settings.clerk_publishable_key.startswith("pk_"):
        logger.error("Invalid Clerk publishable key format (should start with pk_)")
        return False

    if not settings.clerk_secret_key.startswith("sk_"):
        logger.error("Invalid Clerk secret key format (should start with sk_)")
        return False

    # Test connection to Clerk JWKS endpoint
    try:
        provider = ClerkAuthProvider(settings)
        await provider.get_jwks()
        logger.info("Clerk configuration validated successfully")
        return True
    except Exception as e:
        logger.error(f"Clerk configuration validation failed: {e}")
        return False


# Middleware function for request-level authentication
async def clerk_auth_middleware(request: Request, call_next):
    """Middleware to add Clerk user to request state if authenticated."""
    # Extract token from Authorization header
    auth_header = request.headers.get("Authorization")

    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]

        try:
            settings = get_settings()
            provider = get_clerk_provider(settings)
            user = await provider.verify_token(token)

            # Add user to request state
            request.state.user = user
            request.state.user_id = user.id

        except Exception as e:
            logger.debug(f"Token verification failed in middleware: {e}")
            # Don't raise error in middleware, let individual endpoints handle auth

    response = await call_next(request)
    return response


# Export main components
__all__ = [
    "ClerkUser",
    "ClerkAuthProvider",
    "get_clerk_provider",
    "get_current_user",
    "require_current_user",
    "get_current_db_user",
    "require_current_db_user",
    "require_auth",
    "validate_clerk_config",
    "clerk_auth_middleware"
]
