"""Chat endpoints for managing chat sessions and messages."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query

from back_end.app.api.deps import get_chat_service, get_current_user
from back_end.app.services.chat_service import ChatService
from back_end.app.models.user import UserResponse
from back_end.app.models.chat import (
    ChatRequest,
    ChatResponse,
    ChatSessionResponse,
    ChatMessageResponse,
)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post(
    "/",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Send chat message",
    description="Send a message and receive AI response. Creates a new session if session_id is not provided.",
)
async def send_message(
    request: ChatRequest,
    chat_service: ChatService = Depends(get_chat_service),
    current_user: UserResponse = Depends(get_current_user),
) -> ChatResponse:
    """
    Send a chat message and receive AI response.
    
    If session_id is not provided, a new chat session will be created.
    The AI response is generated and both user and assistant messages are saved.
    
    Args:
        request: Chat request with message and optional session_id
        chat_service: Chat service for business logic
        current_user: Authenticated user from JWT token
        
    Returns:
        ChatResponse with AI assistant's response
        
    Raises:
        HTTPException: If session_id is invalid or other errors occur
    """
    try:
        response = await chat_service.send_message(
            user_id=current_user.id,
            message=request.message,
            session_id=request.session_id,
            company_id=request.company_id,
        )
        return response
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process message: {str(e)}",
        )


@router.get(
    "/sessions",
    response_model=List[ChatSessionResponse],
    status_code=status.HTTP_200_OK,
    summary="Get user's chat sessions",
    description="Retrieve all chat sessions for the authenticated user with pagination.",
)
async def get_user_sessions(
    skip: int = Query(0, ge=0, description="Number of sessions to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of sessions to return"),
    chat_service: ChatService = Depends(get_chat_service),
    current_user: UserResponse = Depends(get_current_user),
) -> List[ChatSessionResponse]:
    """
    Get all chat sessions for the authenticated user.
    
    Returns a paginated list of chat sessions ordered by most recent first.
    
    Args:
        skip: Number of sessions to skip for pagination
        limit: Maximum number of sessions to return (1-100)
        chat_service: Chat service for business logic
        current_user: Authenticated user from JWT token
        
    Returns:
        List of chat session responses
    """
    try:
        sessions = await chat_service.get_user_sessions(
            user_id=current_user.id,
            skip=skip,
            limit=limit,
        )
        return sessions
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve sessions: {str(e)}",
        )


@router.get(
    "/sessions/{session_id}",
    response_model=ChatSessionResponse,
    status_code=status.HTTP_200_OK,
    summary="Get chat session",
    description="Retrieve a specific chat session by ID.",
)
async def get_session(
    session_id: UUID,
    chat_service: ChatService = Depends(get_chat_service),
    current_user: UserResponse = Depends(get_current_user),
) -> ChatSessionResponse:
    """
    Get a specific chat session by ID.
    
    Args:
        session_id: Chat session identifier
        chat_service: Chat service for business logic
        current_user: Authenticated user from JWT token
        
    Returns:
        Chat session response
        
    Raises:
        HTTPException: If session not found
    """
    try:
        session = await chat_service.get_session(session_id)
        if session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Chat session {session_id} not found",
            )
        
        # Verify user owns this session
        if session.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this session",
            )
        
        return session
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve session: {str(e)}",
        )


@router.get(
    "/sessions/{session_id}/messages",
    response_model=List[ChatMessageResponse],
    status_code=status.HTTP_200_OK,
    summary="Get session messages",
    description="Retrieve all messages for a specific chat session.",
)
async def get_session_messages(
    session_id: UUID,
    skip: int = Query(0, ge=0, description="Number of messages to skip"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of messages to return"),
    chat_service: ChatService = Depends(get_chat_service),
    current_user: UserResponse = Depends(get_current_user),
) -> List[ChatMessageResponse]:
    """
    Get all messages for a specific chat session.
    
    Returns messages in chronological order (oldest first).
    
    Args:
        session_id: Chat session identifier
        skip: Number of messages to skip for pagination
        limit: Maximum number of messages to return (1-500)
        chat_service: Chat service for business logic
        current_user: Authenticated user from JWT token
        
    Returns:
        List of chat message responses
        
    Raises:
        HTTPException: If session not found or user doesn't have access
    """
    try:
        # Verify session exists and user has access
        session = await chat_service.get_session(session_id)
        if session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Chat session {session_id} not found",
            )
        
        if session.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this session",
            )
        
        # Get messages
        messages = await chat_service.get_session_messages(
            session_id=session_id,
            skip=skip,
            limit=limit,
        )
        return messages
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve messages: {str(e)}",
        )


@router.delete(
    "/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete chat session",
    description="Delete a chat session and all associated messages.",
)
async def delete_session(
    session_id: UUID,
    chat_service: ChatService = Depends(get_chat_service),
    current_user: UserResponse = Depends(get_current_user),
) -> None:
    """
    Delete a chat session and all associated messages.
    
    This operation is permanent and cannot be undone.
    
    Args:
        session_id: Chat session identifier
        chat_service: Chat service for business logic
        current_user: Authenticated user from JWT token
        
    Raises:
        HTTPException: If session not found or user doesn't have access
    """
    try:
        # Verify session exists and user has access
        session = await chat_service.get_session(session_id)
        if session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Chat session {session_id} not found",
            )
        
        if session.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to delete this session",
            )
        
        # Delete session
        await chat_service.delete_session(session_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete session: {str(e)}",
        )
