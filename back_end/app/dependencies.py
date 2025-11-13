"""Global application dependencies for dependency injection."""

from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config.settings import get_settings


# Security scheme for Bearer token authentication
security = HTTPBearer(auto_error=False)

# Get settings instance
settings = get_settings()


async def verify_clerk_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[str]:
    """
    Verify Clerk JWT token from Authorization header.
    
    This is a placeholder implementation. In production, you would:
    1. Extract the JWT token from credentials
    2. Verify the token signature using Clerk's public key
    3. Validate token claims (expiration, issuer, etc.)
    4. Return the user ID from the token
    
    Args:
        credentials: HTTP Authorization credentials with Bearer token
        
    Returns:
        Optional[str]: Clerk user ID if token is valid, None otherwise
        
    Raises:
        HTTPException: If token is invalid or expired
        
    Example:
        @router.get("/protected")
        async def protected_route(user_id: str = Depends(verify_clerk_token)):
            return {"user_id": user_id}
    """
    if credentials is None:
        return None
    
    token = credentials.credentials
    
    # TODO: Implement actual Clerk token verification
    # For now, this is a placeholder that accepts any token
    # In production, use the clerk-sdk-python or verify JWT manually
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Placeholder: Return a mock user ID
    # In production, extract this from the verified JWT token
    return "clerk_user_placeholder"


async def get_current_user_id(
    user_id: Optional[str] = Depends(verify_clerk_token),
) -> str:
    """
    Get the current authenticated user ID.
    
    This dependency requires authentication and will raise an exception
    if no valid token is provided.
    
    Args:
        user_id: User ID from token verification
        
    Returns:
        str: Authenticated user's Clerk ID
        
    Raises:
        HTTPException: If user is not authenticated
        
    Example:
        @router.get("/me")
        async def get_me(user_id: str = Depends(get_current_user_id)):
            return {"user_id": user_id}
    """
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user_id


def get_optional_user_id(
    user_id: Optional[str] = Depends(verify_clerk_token),
) -> Optional[str]:
    """
    Get the current user ID if authenticated, None otherwise.
    
    This dependency allows both authenticated and unauthenticated access.
    Useful for endpoints that have different behavior for authenticated users
    but don't require authentication.
    
    Args:
        user_id: User ID from token verification
        
    Returns:
        Optional[str]: User ID if authenticated, None otherwise
        
    Example:
        @router.get("/public")
        async def public_route(user_id: Optional[str] = Depends(get_optional_user_id)):
            if user_id:
                return {"message": "Hello authenticated user", "user_id": user_id}
            return {"message": "Hello guest"}
    """
    return user_id
