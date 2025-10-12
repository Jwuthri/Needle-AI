"""
Chat endpoints for NeedleAi.
"""

from typing import List, Optional

from app.api.deps import (
    check_rate_limit,
    get_chat_service_dep,
    get_conversation_service_dep,
    get_db,
    validate_session_id,
)
from app.core.security.clerk_auth import ClerkUser, get_current_user
from app.dependencies import get_orchestrator_service
from app.exceptions import NotFoundError, ValidationError
from app.models.chat import ChatRequest, ChatResponse, ChatSession, MessageHistory
from app.models.feedback import ChatFeedback, FeedbackResponse, FeedbackType
from app.services.conversation_service import ConversationService
from app.services.llm_logger import LLMLogger
from app.database.models.llm_call import LLMCallTypeEnum
from fastapi import APIRouter, Depends, HTTPException, status
from app.utils.logging import get_logger

logger = get_logger("chat_api")

router = APIRouter()


@router.post("/", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    orchestrator = Depends(get_orchestrator_service),
    current_user: Optional[ClerkUser] = Depends(get_current_user),
    _rate_limit_check = Depends(check_rate_limit),
    db = Depends(get_db)
) -> ChatResponse:
    """
    Send a message to the chat and get an AI response.

    Uses the orchestrator to dynamically:
    - Analyze query intent and determine optimal response format
    - Retrieve data from RAG (reviews) and/or web search as needed
    - Process data with analytics and NLP
    - Generate visualizations when appropriate
    - Provide proper source citations
    - Track execution steps for UI visualization
    """
    try:
        from app.database.repositories.chat_session import ChatSessionRepository
        from app.database.repositories.chat_message import ChatMessageRepository
        from app.database.models.chat_message import MessageRoleEnum
        import uuid
        
        user_id = current_user.id if current_user else None
        
        # Ensure session exists in database
        session_id = request.session_id or str(uuid.uuid4())
        db_session = await ChatSessionRepository.get_by_id(db, session_id)
        is_new_session = db_session is None
        
        if not db_session:
            # Create session with company_id in metadata
            db_session = await ChatSessionRepository.create(
                db, 
                user_id=user_id, 
                id=session_id,
                extra_metadata={"company_id": request.company_id} if request.company_id else {}
            )
            await db.commit()
            logger.info(f"Created database session {session_id}")
        
        # Save user message to database
        user_message = await ChatMessageRepository.create(
            db=db,
            session_id=session_id,
            content=request.message,
            role=MessageRoleEnum.USER
        )
        await db.commit()
        logger.info(f"Saved user message {user_message.id} to database")
        
        # Process message using orchestrator
        response = await orchestrator.process_message(
            request=request,
            user_id=user_id,
            db=db
        )
        
        # Save assistant response to database
        assistant_message = await ChatMessageRepository.create(
            db=db,
            session_id=session_id,
            content=response.message,
            role=MessageRoleEnum.ASSISTANT,
            metadata=response.metadata
        )
        await db.commit()
        logger.info(f"Saved assistant message {assistant_message.id} to database")
        
        # Generate title for new sessions with first message
        if is_new_session:
            try:
                import httpx
                from app.core.config import get_settings
                
                settings = get_settings()
                openrouter_key = settings.openrouter_api_key
                
                if openrouter_key:
                    # Log title generation LLM call
                    log_id = await LLMLogger.start(
                        call_type=LLMCallTypeEnum.SYSTEM,
                        provider="openrouter",
                        model="openai/gpt-5-nano",
                        messages=[
                            {
                                "role": "system",
                                "content": "Generate a short, descriptive title (max 50 characters) for this conversation. Return only the title, no quotes or extra text."
                            },
                            {
                                "role": "user",
                                "content": request.message
                            }
                        ],
                        user_id=user_id,
                        session_id=session_id,
                        extra_metadata={"purpose": "title_generation"},
                        db=db
                    )
                    
                    try:
                        # Generate title using GPT-5 nano
                        async with httpx.AsyncClient() as client:
                            title_response = await client.post(
                                "https://openrouter.ai/api/v1/chat/completions",
                                headers={
                                    "Authorization": f"Bearer {openrouter_key}",
                                    "Content-Type": "application/json",
                                },
                                json={
                                    "model": "openai/gpt-5-nano",
                                    "messages": [
                                        {
                                            "role": "system",
                                            "content": "Generate a short, descriptive title (max 100 characters) for this conversation. Return only the title, no quotes or extra text."
                                        },
                                        {
                                            "role": "user",
                                            "content": request.message
                                        }
                                    ],
                                    "max_tokens": 25,
                                    "temperature": 0.5,
                                },
                                timeout=10.0
                            )
                            
                            if title_response.status_code == 200:
                                title_data = title_response.json()
                                title = title_data["choices"][0]["message"]["content"].strip()
                                usage = title_data.get("usage", {})
                                
                                # Log completion
                                await LLMLogger.complete(
                                    log_id=log_id,
                                    response_message={"role": "assistant", "content": title},
                                    tokens={
                                        "prompt_tokens": usage.get("prompt_tokens"),
                                        "completion_tokens": usage.get("completion_tokens"),
                                        "total_tokens": usage.get("total_tokens")
                                    },
                                    finish_reason="stop",
                                    db=db
                                )
                                
                                # Update session with title
                                await ChatSessionRepository.update(db, session_id, title=title[:500])
                                await db.commit()
                                logger.info(f"Generated title for session {session_id}: {title}")
                            else:
                                await LLMLogger.fail(log_id, f"HTTP {title_response.status_code}", db=db)
                    except Exception as title_error:
                        await LLMLogger.fail(log_id, str(title_error), db=db)
                        logger.error(f"Failed to generate title: {title_error}")
                        # Don't fail the request if title generation fails
            except Exception as e:
                logger.error(f"Error in title generation section: {e}")
                # Don't fail the request if title generation fails
        
        # Update response with session_id
        response.session_id = session_id
        return response

    except ValidationError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message
        )
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in send_message: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process message: {str(e)}"
        )


@router.post("/sessions", response_model=ChatSession)
async def create_session(
    current_user: Optional[ClerkUser] = Depends(get_current_user),
    db = Depends(get_db)
) -> ChatSession:
    """
    Create a new chat session in database.
    
    Creates a new empty session that can be used for subsequent chat messages.
    """
    try:
        from app.database.repositories.chat_session import ChatSessionRepository
        import uuid
        from datetime import datetime
        
        user_id = current_user.id if current_user else None
        session_id = str(uuid.uuid4())
        
        # Create session in database
        db_session = await ChatSessionRepository.create(
            db=db,
            user_id=user_id,
            id=session_id
        )
        await db.commit()
        
        # Create session response
        session = ChatSession(
            session_id=session_id,
            messages=[],
            created_at=db_session.created_at,
            updated_at=db_session.updated_at,
            metadata={"user_id": user_id} if user_id else {}
        )
        
        logger.info(f"Created new session {session_id} for user {user_id}")
        return session
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to create session: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create session: {str(e)}"
        )


@router.get("/sessions", response_model=List[ChatSession])
async def list_sessions(
    current_user: Optional[ClerkUser] = Depends(get_current_user),
    db = Depends(get_db),
    limit: int = 50,
    offset: int = 0
) -> List[ChatSession]:
    """
    List chat sessions from database.

    Returns a paginated list of chat sessions for the current user.
    """
    try:
        from app.database.repositories.chat_session import ChatSessionRepository
        from datetime import datetime
        
        user_id = current_user.id if current_user else None
        if not user_id:
            return []
        
        # Fetch sessions from database with messages
        db_sessions = await ChatSessionRepository.get_user_sessions(
            db=db,
            user_id=user_id,
            limit=limit,
            offset=offset,
            include_messages=True
        )
        
        # Convert to API model
        sessions = []
        for db_session in db_sessions:
            from app.models.chat import ChatMessage as ApiMessage
            from app.models.chat import MessageRole
            messages = [
                ApiMessage(
                    id=str(msg.id),
                    content=msg.content,
                    role=MessageRole(msg.role.value),
                    timestamp=msg.created_at if msg.created_at else datetime.utcnow(),
                    metadata=msg.metadata if isinstance(msg.metadata, dict) else {}
                )
                for msg in db_session.messages
            ]
            
            # Include title and company_id in metadata
            metadata = db_session.extra_metadata or {}
            if db_session.title:
                metadata["title"] = db_session.title
            
            sessions.append(ChatSession(
                session_id=str(db_session.id),
                messages=messages,
                created_at=db_session.created_at,
                updated_at=db_session.updated_at,
                metadata=metadata
            ))
        
        return sessions

    except Exception as e:
        logger.error(f"Error listing sessions: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list sessions: {str(e)}"
        )


@router.get("/sessions/{session_id}", response_model=ChatSession)
async def get_session(
    session_id: str = Depends(validate_session_id),
    current_user: Optional[ClerkUser] = Depends(get_current_user),
    db = Depends(get_db)
) -> ChatSession:
    """
    Get a specific chat session with full message history from database.
    """
    try:
        from app.database.repositories.chat_session import ChatSessionRepository
        from datetime import datetime
        
        user_id = current_user.id if current_user else None
        
        # Fetch from database
        db_session = await ChatSessionRepository.get_by_id(
            db=db,
            session_id=session_id,
            include_messages=True
        )

        if not db_session:
            raise NotFoundError(f"Session {session_id} not found")
        
        # Check ownership
        if user_id and db_session.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this session"
            )
        
        # Convert to API model
        from app.models.chat import ChatMessage as ApiMessage
        from app.models.chat import MessageRole
        messages = [
            ApiMessage(
                id=str(msg.id),
                content=msg.content,
                role=MessageRole(msg.role.value),
                timestamp=msg.created_at if msg.created_at else datetime.utcnow(),
                metadata=msg.metadata if isinstance(msg.metadata, dict) else {}
            )
            for msg in db_session.messages
        ]
        
        # Include title and company_id in metadata
        metadata = db_session.extra_metadata or {}
        if db_session.title:
            metadata["title"] = db_session.title
        
        return ChatSession(
            session_id=str(db_session.id),
            messages=messages,
            created_at=db_session.created_at,
            updated_at=db_session.updated_at,
            metadata=metadata
        )

    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get session: {str(e)}"
        )


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str = Depends(validate_session_id),
    current_user: Optional[ClerkUser] = Depends(get_current_user),
    db = Depends(get_db)
) -> dict:
    """
    Delete a chat session and all its messages from database.
    """
    try:
        from app.database.repositories.chat_session import ChatSessionRepository
        
        user_id = current_user.id if current_user else None
        
        # Get session to check ownership
        db_session = await ChatSessionRepository.get_by_id(db, session_id)
        if not db_session:
            raise NotFoundError(f"Session {session_id} not found")
        
        # Check ownership
        if user_id and db_session.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this session"
            )
        
        # Delete session (cascades to messages)
        success = await ChatSessionRepository.delete(db, session_id)
        await db.commit()

        if not success:
            raise NotFoundError(f"Session {session_id} not found")

        return {"message": f"Session {session_id} deleted successfully"}

    except NotFoundError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message
        )
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error deleting session: {e}", exc_info=True)
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
