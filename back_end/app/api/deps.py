"""API dependency injection functions."""

from typing import AsyncGenerator, Optional
from uuid import UUID

from fastapi import Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession

from back_end.app.database.session import get_db
from back_end.app.database.repositories.user import UserRepository
from back_end.app.database.repositories.company import CompanyRepository
from back_end.app.database.repositories.chat_session import ChatSessionRepository
from back_end.app.database.repositories.chat_message import ChatMessageRepository
from back_end.app.database.repositories.chat_message_step import ChatMessageStepRepository
from back_end.app.database.repositories.llm_call import LLMCallRepository
from back_end.app.database.repositories.user_dataset import UserDatasetRepository
from back_end.app.services.user_service import UserService
from back_end.app.services.company_service import CompanyService
from back_end.app.services.chat_service import ChatService
from back_end.app.services.user_dataset_service import UserDatasetService
from back_end.app.models.user import UserResponse
from back_end.app.core.config.settings import get_settings

settings = get_settings()


# Repository Dependencies
async def get_user_repository(
    db: AsyncSession = Depends(get_db),
) -> UserRepository:
    """Get user repository instance."""
    return UserRepository(model=None, session=db)


async def get_company_repository(
    db: AsyncSession = Depends(get_db),
) -> CompanyRepository:
    """Get company repository instance."""
    return CompanyRepository(model=None, session=db)


async def get_chat_session_repository(
    db: AsyncSession = Depends(get_db),
) -> ChatSessionRepository:
    """Get chat session repository instance."""
    return ChatSessionRepository(model=None, session=db)


async def get_chat_message_repository(
    db: AsyncSession = Depends(get_db),
) -> ChatMessageRepository:
    """Get chat message repository instance."""
    return ChatMessageRepository(model=None, session=db)


async def get_chat_message_step_repository(
    db: AsyncSession = Depends(get_db),
) -> ChatMessageStepRepository:
    """Get chat message step repository instance."""
    return ChatMessageStepRepository(model=None, session=db)


async def get_llm_call_repository(
    db: AsyncSession = Depends(get_db),
) -> LLMCallRepository:
    """Get LLM call repository instance."""
    return LLMCallRepository(model=None, session=db)


async def get_user_dataset_repository(
    db: AsyncSession = Depends(get_db),
) -> UserDatasetRepository:
    """Get user dataset repository instance."""
    return UserDatasetRepository(model=None, session=db)


# Service Dependencies
async def get_user_service(
    db: AsyncSession = Depends(get_db),
    user_repo: UserRepository = Depends(get_user_repository),
) -> UserService:
    """Get user service instance."""
    return UserService(session=db, user_repo=user_repo)


async def get_company_service(
    db: AsyncSession = Depends(get_db),
    company_repo: CompanyRepository = Depends(get_company_repository),
) -> CompanyService:
    """Get company service instance."""
    return CompanyService(session=db, company_repo=company_repo)


async def get_chat_service(
    db: AsyncSession = Depends(get_db),
    chat_session_repo: ChatSessionRepository = Depends(get_chat_session_repository),
    chat_message_repo: ChatMessageRepository = Depends(get_chat_message_repository),
    chat_message_step_repo: ChatMessageStepRepository = Depends(
        get_chat_message_step_repository
    ),
) -> ChatService:
    """Get chat service instance."""
    return ChatService(
        session=db,
        chat_session_repo=chat_session_repo,
        chat_message_repo=chat_message_repo,
        chat_message_step_repo=chat_message_step_repo,
    )


async def get_user_dataset_service(
    db: AsyncSession = Depends(get_db),
    user_dataset_repo: UserDatasetRepository = Depends(get_user_dataset_repository),
    user_repo: UserRepository = Depends(get_user_repository),
) -> UserDatasetService:
    """Get user dataset service instance."""
    return UserDatasetService(
        session=db, user_dataset_repo=user_dataset_repo, user_repo=user_repo
    )


# Authentication Dependencies
async def get_current_user(
    authorization: Optional[str] = Header(None),
    user_service: UserService = Depends(get_user_service),
) -> UserResponse:
    """
    Get current authenticated user from Clerk JWT token.
    
    This is a simplified implementation. In production, you would:
    1. Validate the Clerk JWT token
    2. Extract the clerk_user_id from the token
    3. Look up or create the user in the database
    
    Args:
        authorization: Authorization header with Bearer token
        user_service: User service for database operations
        
    Returns:
        UserResponse: Current authenticated user
        
    Raises:
        HTTPException: If authentication fails
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # TODO: Implement actual Clerk JWT validation
    # For now, this is a placeholder that extracts a mock clerk_user_id
    # In production, use the Clerk SDK to validate the token
    token = authorization.replace("Bearer ", "")
    
    # Placeholder: In production, decode and validate the JWT
    # from clerk_backend_api import Clerk
    # clerk = Clerk(bearer_auth=settings.clerk_secret_key)
    # session = clerk.sessions.verify_token(token)
    # clerk_user_id = session.user_id
    
    # For development, accept a mock clerk_user_id in the token
    # This should be replaced with actual JWT validation
    clerk_user_id = token  # Placeholder
    
    # Get or create user
    user = await user_service.get_user_by_clerk_id(clerk_user_id)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="User not found. Please sign up first.",
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="User account is inactive",
        )
    
    return user


async def get_optional_user(
    authorization: Optional[str] = Header(None),
    user_service: UserService = Depends(get_user_service),
) -> Optional[UserResponse]:
    """
    Get current authenticated user if token is provided, otherwise return None.
    
    This is useful for endpoints that work with or without authentication.
    
    Args:
        authorization: Authorization header with Bearer token
        user_service: User service for database operations
        
    Returns:
        UserResponse or None: Current authenticated user or None
    """
    if not authorization:
        return None
    
    try:
        return await get_current_user(authorization, user_service)
    except HTTPException:
        return None
