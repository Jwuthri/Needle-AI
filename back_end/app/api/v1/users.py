"""User endpoints for managing users."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query

from back_end.app.api.deps import get_user_service, get_current_user
from back_end.app.services.user_service import UserService
from back_end.app.models.user import (
    UserCreate,
    UserUpdate,
    UserResponse,
)

router = APIRouter(prefix="/users", tags=["users"])


@router.post(
    "/",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create user",
    description="Create a new user account. This is typically called during user registration.",
)
async def create_user(
    user_data: UserCreate,
    user_service: UserService = Depends(get_user_service),
) -> UserResponse:
    """
    Create a new user account.
    
    This endpoint is typically called during the registration process
    after a user has been created in Clerk.
    
    Args:
        user_data: User creation data including clerk_user_id and email
        user_service: User service for business logic
        
    Returns:
        Created user response
        
    Raises:
        HTTPException: If user with clerk_user_id or email already exists
    """
    try:
        user = await user_service.create_user(user_data)
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {str(e)}",
        )


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current user",
    description="Get the currently authenticated user's profile.",
)
async def get_current_user_profile(
    current_user: UserResponse = Depends(get_current_user),
) -> UserResponse:
    """
    Get the currently authenticated user's profile.
    
    Args:
        current_user: Authenticated user from JWT token
        
    Returns:
        Current user response
    """
    return current_user


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get user by ID",
    description="Retrieve a specific user by their ID.",
)
async def get_user(
    user_id: UUID,
    user_service: UserService = Depends(get_user_service),
    current_user: UserResponse = Depends(get_current_user),
) -> UserResponse:
    """
    Get a specific user by ID.
    
    Users can only view their own profile unless they have admin privileges.
    
    Args:
        user_id: User identifier
        user_service: User service for business logic
        current_user: Authenticated user from JWT token
        
    Returns:
        User response
        
    Raises:
        HTTPException: If user not found or access denied
    """
    # Users can only view their own profile
    if user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view this user",
        )
    
    try:
        user = await user_service.get_user(user_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found",
            )
        return user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve user: {str(e)}",
        )


@router.get(
    "/",
    response_model=List[UserResponse],
    status_code=status.HTTP_200_OK,
    summary="Get all users",
    description="Retrieve all users with pagination. Admin access required.",
)
async def get_all_users(
    skip: int = Query(0, ge=0, description="Number of users to skip"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of users to return"),
    user_service: UserService = Depends(get_user_service),
    current_user: UserResponse = Depends(get_current_user),
) -> List[UserResponse]:
    """
    Get all users with pagination.
    
    This endpoint is typically restricted to admin users.
    For now, it's available to all authenticated users.
    
    Args:
        skip: Number of users to skip for pagination
        limit: Maximum number of users to return (1-500)
        user_service: User service for business logic
        current_user: Authenticated user from JWT token
        
    Returns:
        List of user responses
    """
    try:
        users = await user_service.get_all_users(skip=skip, limit=limit)
        return users
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve users: {str(e)}",
        )


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Update user",
    description="Update user profile information.",
)
async def update_user(
    user_id: UUID,
    user_data: UserUpdate,
    user_service: UserService = Depends(get_user_service),
    current_user: UserResponse = Depends(get_current_user),
) -> UserResponse:
    """
    Update user profile information.
    
    Users can only update their own profile.
    
    Args:
        user_id: User identifier
        user_data: User update data
        user_service: User service for business logic
        current_user: Authenticated user from JWT token
        
    Returns:
        Updated user response
        
    Raises:
        HTTPException: If user not found or access denied
    """
    # Users can only update their own profile
    if user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to update this user",
        )
    
    try:
        updated_user = await user_service.update_user(user_id, user_data)
        if updated_user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found",
            )
        return updated_user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update user: {str(e)}",
        )


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete user",
    description="Delete a user account and all associated data.",
)
async def delete_user(
    user_id: UUID,
    user_service: UserService = Depends(get_user_service),
    current_user: UserResponse = Depends(get_current_user),
) -> None:
    """
    Delete a user account and all associated data.
    
    This operation is permanent and cannot be undone.
    Users can only delete their own account.
    
    Args:
        user_id: User identifier
        user_service: User service for business logic
        current_user: Authenticated user from JWT token
        
    Raises:
        HTTPException: If user not found or access denied
    """
    # Users can only delete their own account
    if user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this user",
        )
    
    try:
        result = await user_service.delete_user(user_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found",
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete user: {str(e)}",
        )


@router.post(
    "/sync",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Sync user from Clerk",
    description="Get or create user from Clerk authentication. Used during login flow.",
)
async def sync_user(
    user_data: UserCreate,
    user_service: UserService = Depends(get_user_service),
) -> UserResponse:
    """
    Get or create user from Clerk authentication.
    
    This endpoint is called during the login flow to ensure the user
    exists in our database. If the user doesn't exist, it creates them.
    
    Args:
        user_data: User data from Clerk
        user_service: User service for business logic
        
    Returns:
        Existing or newly created user response
    """
    try:
        user = await user_service.get_or_create_user(user_data)
        return user
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync user: {str(e)}",
        )
