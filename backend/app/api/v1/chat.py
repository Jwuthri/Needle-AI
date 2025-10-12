"""
Chat endpoints for NeedleAi.
"""

from typing import List, Optional

from app.api.deps import (
    check_rate_limit,
    get_chat_service_dep,
    get_conversation_service_dep,
    validate_session_id,
)
from app.core.security.clerk_auth import ClerkUser, get_current_user
from app.exceptions import NotFoundError, ValidationError
from app.models.chat import ChatRequest, ChatResponse, ChatSession, MessageHistory
from app.models.feedback import ChatFeedback, FeedbackResponse, FeedbackType
from app.services.conversation_service import ConversationService
from fastapi import APIRouter, Depends, HTTPException, status
from app.utils.logging import get_logger

logger = get_logger("chat_api")

router = APIRouter()


@router.post("/", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    chat_service = Depends(get_chat_service_dep),
    current_user: Optional[ClerkUser] = Depends(get_current_user),
    _rate_limit_check = Depends(check_rate_limit)
) -> ChatResponse:
    """
    Send a message to the chat and get an AI response.

    **Enhanced RAG Mode** (when company_ids provided):
    - Retrieves relevant reviews from vector database
    - Provides source attribution
    - Shows pipeline visualization (Weaviate-style)
    - Generates related questions
    - Classifies query intent
    
    **Standard Mode** (no company_ids):
    - Uses regular Agno chat service
    - General conversation without review context
    """
    try:
        user_id = current_user.id if current_user else None
        
        # Use RAG service if company_ids provided
        if request.company_ids:
            from app.services.rag_chat_service import RAGChatService
            
            rag_service = RAGChatService()
            await rag_service.initialize()
            
            response = await rag_service.process_message(
                request=request,
                user_id=user_id,
                company_ids=request.company_ids
            )
            
            await rag_service.cleanup()
            
        else:
            # Standard chat (backward compatible)
            response = await chat_service.process_message(
                message=request.message,
                session_id=request.session_id,
                user_id=user_id,
                context=request.context
            )
        
        return response

    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process message: {str(e)}"
        )


@router.get("/sessions", response_model=List[ChatSession])
async def list_sessions(
    conversation_service: ConversationService = Depends(get_conversation_service_dep),
    current_user: Optional[ClerkUser] = Depends(get_current_user),
    limit: int = 50,
    offset: int = 0
) -> List[ChatSession]:
    """
    List chat sessions.

    Returns a paginated list of chat sessions. If user_id is provided,
    only returns sessions for that user.
    """
    try:
        user_id = current_user.id if current_user else None
        sessions = await conversation_service.list_sessions(
            user_id=user_id,
            limit=limit,
            offset=offset
        )
        return sessions

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list sessions: {str(e)}"
        )


@router.get("/sessions/{session_id}", response_model=ChatSession)
async def get_session(
    session_id: str = Depends(validate_session_id),
    conversation_service: ConversationService = Depends(get_conversation_service_dep),
    current_user: Optional[ClerkUser] = Depends(get_current_user)
) -> ChatSession:
    """
    Get a specific chat session with full message history.
    """
    try:
        user_id = current_user.id if current_user else None
        session = await conversation_service.get_session(
            session_id=session_id,
            user_id=user_id
        )

        if not session:
            raise NotFoundError(f"Session {session_id} not found")

        return session

    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get session: {str(e)}"
        )


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str = Depends(validate_session_id),
    conversation_service: ConversationService = Depends(get_conversation_service_dep),
    current_user: Optional[ClerkUser] = Depends(get_current_user)
) -> dict:
    """
    Delete a chat session and all its messages.
    """
    try:
        user_id = current_user.id if current_user else None
        success = await conversation_service.delete_session(
            session_id=session_id,
            user_id=user_id
        )

        if not success:
            raise NotFoundError(f"Session {session_id} not found")

        return {"message": f"Session {session_id} deleted successfully"}

    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete session: {str(e)}"
        )


@router.get("/sessions/{session_id}/messages", response_model=MessageHistory)
async def get_session_messages(
    session_id: str = Depends(validate_session_id),
    conversation_service: ConversationService = Depends(get_conversation_service_dep),
    current_user: Optional[ClerkUser] = Depends(get_current_user),
    limit: int = 100,
    offset: int = 0
) -> MessageHistory:
    """
    Get paginated message history for a session.
    """
    try:
        user_id = current_user.id if current_user else None
        messages = await conversation_service.get_session_messages(
            session_id=session_id,
            user_id=user_id,
            limit=limit,
            offset=offset
        )

        return MessageHistory(
            session_id=session_id,
            messages=messages,
            total=len(messages),
            limit=limit,
            offset=offset
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get session messages: {str(e)}"
        )


@router.post("/sessions/{session_id}/clear")
async def clear_session(
    session_id: str = Depends(validate_session_id),
    conversation_service: ConversationService = Depends(get_conversation_service_dep),
    current_user: Optional[ClerkUser] = Depends(get_current_user)
) -> dict:
    """
    Clear all messages from a session while keeping the session.
    """
    try:
        user_id = current_user.id if current_user else None
        success = await conversation_service.clear_session_messages(
            session_id=session_id,
            user_id=user_id
        )

        if not success:
            raise NotFoundError(f"Session {session_id} not found")

        return {"message": f"Session {session_id} cleared successfully"}

    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear session: {str(e)}"
        )


@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    feedback: ChatFeedback,
    current_user: Optional[ClerkUser] = Depends(get_current_user)
) -> FeedbackResponse:
    """
    Submit feedback for a chat response (like, dislike, copy).
    
    Tracks user interactions to improve response quality.
    """
    try:
        # Log feedback for analytics
        user_id = current_user.id if current_user else "anonymous"
        logger.info(
            f"Feedback received - User: {user_id}, Message: {feedback.message_id}, "
            f"Type: {feedback.feedback_type.value}"
        )
        
        # TODO: Store feedback in database for analytics
        # Could create a feedback table or add to message metadata
        
        return FeedbackResponse(
            success=True,
            message=f"Thank you for your {feedback.feedback_type.value} feedback!"
        )
        
    except Exception as e:
        logger.error(f"Error submitting feedback: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit feedback: {str(e)}"
        )
