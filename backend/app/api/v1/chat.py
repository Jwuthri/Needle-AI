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
from fastapi.responses import StreamingResponse
import json
from app.utils.logging import get_logger

logger = get_logger("chat_api")

router = APIRouter()


@router.post("/stream")
async def send_message_stream(
    request: ChatRequest,
    orchestrator = Depends(get_orchestrator_service),
    current_user: Optional[ClerkUser] = Depends(get_current_user),
    _rate_limit_check = Depends(check_rate_limit),
    db = Depends(get_db)
):
    """
    Send a message to the chat and get streaming AI responses.
    
    Returns Server-Sent Events (SSE) stream with:
    - status updates (analyzing, retrieving data, etc.)
    - content chunks (streaming response text)
    - complete (final response with metadata)
    - error (if something goes wrong)
    
    Each event is JSON with {type, data} structure.
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
        
        # Stream processing function - doesn't use DB for streaming, only for final save
        async def event_stream():
            from app.database.session import get_async_session
            from datetime import datetime, date
            import asyncio
            
            def make_json_serializable(obj):
                """Recursively convert any object to be JSON serializable."""
                if obj is None:
                    return None
                elif isinstance(obj, (datetime, date)):
                    return obj.isoformat()
                elif hasattr(obj, "model_dump"):
                    # Pydantic model
                    return obj.model_dump(mode='json')
                elif isinstance(obj, dict):
                    return {k: make_json_serializable(v) for k, v in obj.items()}
                elif isinstance(obj, (list, tuple)):
                    return [make_json_serializable(item) for item in obj]
                elif isinstance(obj, (str, int, float, bool)):
                    return obj
                else:
                    # For any other type, try str() as fallback
                    return str(obj)
            
            accumulated_content = ""
            update_count = 0
            assistant_message_id = None
            
            try:
                # Create assistant message BEFORE starting the workflow
                try:
                    async with get_async_session() as save_db:
                        assistant_message = await ChatMessageRepository.create(
                            db=save_db,
                            session_id=session_id,
                            content="",
                            role=MessageRoleEnum.ASSISTANT
                        )
                        await save_db.commit()
                        assistant_message_id = assistant_message.id
                        logger.info(f"[CHAT API] Created assistant message {assistant_message_id} BEFORE workflow starts")
                except Exception as db_error:
                    logger.error(f"Failed to create assistant message: {db_error}")
                    raise
                
                # Process stream - workflow handles ALL database operations (steps + final answer)
                # Pass db session for retrieving conversation history
                async for update in orchestrator.process_message_stream(
                    request=request,
                    user_id=user_id,
                    assistant_message_id=assistant_message_id,
                    db=db
                ):
                    update_count += 1
                    
                    if update["type"] == "content":
                        accumulated_content += update["data"]["content"]
                        logger.debug(f"Streaming content update #{update_count}: {len(update['data']['content'])} chars")
                    
                    serializable_update = make_json_serializable(update)
                    sse_data = f"data: {json.dumps(serializable_update)}\n\n"
                    yield sse_data
                    
                    if update["type"] == "content":
                        await asyncio.sleep(0.001)
                
                logger.info(f"Stream completed: {update_count} updates sent, {len(accumulated_content)} chars total")
                
            except Exception as e:
                logger.error(f"Stream error: {e}", exc_info=True)
                error_event = {
                    "type": "error",
                    "data": {"error": str(e)}
                }
                yield f"data: {json.dumps(error_event)}\n\n"
        
        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"  # Disable nginx buffering
            }
        )
        
    except Exception as e:
        logger.error(f"Chat stream error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Stream failed: {str(e)}"
        )


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
            from app.database.repositories.chat_message_step import ChatMessageStepRepository
            
            messages = []
            for msg in db_session.messages:
                # Fetch agent steps for this message
                agent_steps = await ChatMessageStepRepository.get_by_message_id(db, str(msg.id))
                
                # Format steps for frontend
                formatted_steps = []
                for step in agent_steps:
                    # Determine content based on available fields
                    content = None
                    if step.structured_output:
                        content = step.structured_output
                    elif step.tool_call:
                        content = step.tool_call
                    elif step.prediction:
                        content = step.prediction
                    
                    formatted_steps.append({
                        "step_id": str(step.id),
                        "agent_name": step.agent_name,
                        "content": content,
                        "is_structured": step.structured_output is not None or step.tool_call is not None,
                        "timestamp": step.created_at.isoformat() if step.created_at else None,
                        "status": "completed",
                        "step_order": step.step_order
                    })
                
                # Add steps to metadata
                metadata = msg.metadata if isinstance(msg.metadata, dict) else {}
                if formatted_steps:
                    metadata['agent_steps'] = formatted_steps
                
                messages.append(ApiMessage(
                    id=str(msg.id),
                    content=msg.content,
                    role=MessageRole(msg.role.value),
                    timestamp=msg.created_at if msg.created_at else datetime.utcnow(),
                    metadata=metadata
                ))
            
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
        from app.database.repositories.chat_message_step import ChatMessageStepRepository
        
        messages = []
        for msg in db_session.messages:
            # Fetch agent steps for this message
            agent_steps = await ChatMessageStepRepository.get_by_message_id(db, str(msg.id))
            
            # Format steps for frontend
            formatted_steps = []
            for step in agent_steps:
                # Determine content based on available fields
                content = None
                if step.structured_output:
                    content = step.structured_output
                elif step.tool_call:
                    content = step.tool_call
                elif step.prediction:
                    content = step.prediction
                
                formatted_steps.append({
                    "step_id": str(step.id),
                    "agent_name": step.agent_name,
                    "content": content,
                    "is_structured": step.structured_output is not None or step.tool_call is not None,
                    "timestamp": step.created_at.isoformat() if step.created_at else None,
                    "status": "completed",
                    "step_order": step.step_order
                })
            
            # Add steps to metadata
            metadata = msg.metadata if isinstance(msg.metadata, dict) else {}
            if formatted_steps:
                metadata['agent_steps'] = formatted_steps
            
            messages.append(ApiMessage(
                id=str(msg.id),
                content=msg.content,
                role=MessageRole(msg.role.value),
                timestamp=msg.created_at if msg.created_at else datetime.utcnow(),
                completed_at=msg.completed_at,  # ADD THIS LINE
                metadata=metadata
            ))
        
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


@router.post("/analyze")
async def analyze_reviews(
    request: ChatRequest,
    current_user: Optional[ClerkUser] = Depends(get_current_user),
    _rate_limit_check = Depends(check_rate_limit),
    db = Depends(get_db)
):
    """
    Analyze product reviews using the Product Review Analysis Workflow.
    
    This endpoint uses the advanced multi-agent workflow with:
    - Intelligent query routing via Coordinator Agent
    - Adaptive planning with ReAct pattern via Planner Agent
    - Parallel agent execution via Orchestrator
    - Comprehensive execution tracking via Chat Message Steps
    - Conversational context management for follow-up queries
    
    Authentication & Authorization:
    - Requires valid Clerk authentication token
    - Verifies user owns the session
    - Checks user has access to requested datasets
    - Rate limiting applied per client IP
    
    Returns Server-Sent Events (SSE) stream with:
    - agent_step_start: When an agent begins execution
    - agent_step_complete: When an agent completes with results
    - tool_call: When a tool is invoked
    - tool_call_complete: When a tool call finishes
    - content: Streaming response text chunks
    - complete: Final response with metadata
    - error: If something goes wrong
    
    Requirements: 7.1, 7.5, 7.6, 13.1, 13.2, 13.3
    """
    try:
        from app.database.repositories.chat_session import ChatSessionRepository
        from app.database.repositories.chat_message import ChatMessageRepository
        from app.database.models.chat_message import MessageRoleEnum
        from app.optimal_workflow.product_review_workflow import ProductReviewAnalysisWorkflow
        from llama_index.core.workflow import StartEvent
        import uuid
        
        user_id = current_user.id if current_user else None
        
        # Verify user is authenticated for this endpoint
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required for review analysis"
            )
        
        # Ensure session exists in database
        session_id = request.session_id or str(uuid.uuid4())
        db_session = await ChatSessionRepository.get_by_id(db, session_id)
        
        if db_session:
            # Verify user owns the session
            if db_session.user_id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have access to this session"
                )
            logger.info(f"Using existing session {session_id}")
        else:
            # Create new session for this user
            db_session = await ChatSessionRepository.create(
                db, 
                user_id=user_id, 
                id=session_id,
                extra_metadata={"company_id": request.company_id} if request.company_id else {}
            )
            await db.commit()
            logger.info(f"Created database session {session_id} for user {user_id}")
        
        # Verify user has access to datasets if company_id is specified
        if request.company_id:
            try:
                from app.database.repositories.user_dataset import UserDatasetRepository
                
                # Check if user has access to datasets for this company
                user_datasets = await UserDatasetRepository.get_by_user_id(db, user_id)
                
                # Verify at least one dataset exists for this user
                if not user_datasets:
                    logger.warning(f"User {user_id} has no datasets available")
                    # Don't block - workflow will handle gracefully
                else:
                    logger.info(f"User {user_id} has access to {len(user_datasets)} dataset(s)")
                    
            except Exception as dataset_check_error:
                logger.warning(f"Could not verify dataset access: {dataset_check_error}")
                # Don't block - workflow will handle gracefully
        
        # Save user message to database
        user_message = await ChatMessageRepository.create(
            db=db,
            session_id=session_id,
            content=request.message,
            role=MessageRoleEnum.USER
        )
        await db.commit()
        logger.info(f"Saved user message {user_message.id} to database")
        
        # Create assistant message BEFORE starting the workflow
        assistant_message = await ChatMessageRepository.create(
            db=db,
            session_id=session_id,
            content="",
            role=MessageRoleEnum.ASSISTANT
        )
        await db.commit()
        assistant_message_id = assistant_message.id
        logger.info(f"Created assistant message {assistant_message_id} for workflow tracking")
        
        # Stream processing function
        async def event_stream():
            from app.database.session import get_async_session
            from datetime import datetime, date
            import asyncio
            
            def make_json_serializable(obj):
                """Recursively convert any object to be JSON serializable."""
                if obj is None:
                    return None
                elif isinstance(obj, (datetime, date)):
                    return obj.isoformat()
                elif hasattr(obj, "model_dump"):
                    # Pydantic model
                    return obj.model_dump(mode='json')
                elif isinstance(obj, dict):
                    return {k: make_json_serializable(v) for k, v in obj.items()}
                elif isinstance(obj, (list, tuple)):
                    return [make_json_serializable(item) for item in obj]
                elif isinstance(obj, (str, int, float, bool)):
                    return obj
                else:
                    # For any other type, try str() as fallback
                    return str(obj)
            
            accumulated_content = ""
            update_count = 0
            
            try:
                # Get conversation history for context
                conversation_history = []
                try:
                    async with get_async_session() as history_db:
                        from app.database.repositories.chat_message import ChatMessageRepository
                        messages = await ChatMessageRepository.get_session_messages(
                            history_db,
                            session_id,
                            limit=10
                        )
                        conversation_history = [
                            {
                                "role": msg.role.value,
                                "content": msg.content,
                                "timestamp": msg.created_at.isoformat() if msg.created_at else None
                            }
                            for msg in messages
                        ]
                except Exception as history_error:
                    logger.warning(f"Could not load conversation history: {history_error}")
                
                # Create event queue for streaming
                event_queue = asyncio.Queue()
                
                def stream_callback(event: dict):
                    """Callback to receive events from workflow."""
                    try:
                        event_queue.put_nowait(event)
                    except Exception as e:
                        logger.error(f"Failed to queue event: {e}")
                
                # Initialize workflow with streaming callback
                workflow = ProductReviewAnalysisWorkflow(
                    user_id=user_id,
                    session_id=session_id,
                    assistant_message_id=assistant_message_id,
                    stream_callback=stream_callback,
                    timeout=300.0,  # 5 minute timeout
                    verbose=True
                )
                
                # Start workflow in background task
                workflow_task = asyncio.create_task(
                    workflow.run(
                        query=request.message,
                        conversation_history=conversation_history
                    )
                )
                
                # Stream events as they arrive
                while True:
                    try:
                        # Wait for event with timeout
                        event = await asyncio.wait_for(event_queue.get(), timeout=1.0)
                        update_count += 1
                        
                        if event["type"] == "content":
                            accumulated_content += event["data"]["content"]
                            logger.debug(f"Streaming content update #{update_count}: {len(event['data']['content'])} chars")
                        
                        serializable_event = make_json_serializable(event)
                        sse_data = f"data: {json.dumps(serializable_event)}\n\n"
                        yield sse_data
                        
                        if event["type"] == "content":
                            await asyncio.sleep(0.001)
                        
                        # Check if workflow completed
                        if event["type"] == "complete":
                            logger.info(f"Workflow completed: {update_count} updates sent")
                            break
                            
                    except asyncio.TimeoutError:
                        # Check if workflow task is done
                        if workflow_task.done():
                            # Get result or exception
                            try:
                                result = workflow_task.result()
                                logger.info(f"Workflow finished successfully")
                                break
                            except Exception as workflow_error:
                                logger.error(f"Workflow failed: {workflow_error}", exc_info=True)
                                error_event = {
                                    "type": "error",
                                    "data": {"error": str(workflow_error)}
                                }
                                yield f"data: {json.dumps(error_event)}\n\n"
                                break
                        # Continue waiting for events
                        continue
                
                logger.info(f"Stream completed: {update_count} updates sent, {len(accumulated_content)} chars total")
                
            except Exception as e:
                logger.error(f"Stream error: {e}", exc_info=True)
                error_event = {
                    "type": "error",
                    "data": {"error": str(e)}
                }
                yield f"data: {json.dumps(error_event)}\n\n"
        
        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"  # Disable nginx buffering
            }
        )
        
    except Exception as e:
        logger.error(f"Chat analyze error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}"
        )


@router.get("/steps/{message_id}")
async def get_message_steps(
    message_id: str,
    current_user: Optional[ClerkUser] = Depends(get_current_user),
    db = Depends(get_db)
) -> dict:
    """
    Get all execution steps for a specific chat message.
    
    Returns detailed information about each agent step including:
    - Agent name and execution order
    - Thoughts (reasoning traces)
    - Actions (tool calls, structured outputs, predictions)
    - Results and timestamps
    
    This enables the frontend to visualize the workflow execution process.
    
    Requirements: 4.6
    """
    try:
        from app.database.repositories.chat_message import ChatMessageRepository
        from app.database.repositories.chat_message_step import ChatMessageStepRepository
        
        user_id = current_user.id if current_user else None
        
        # Get the message to verify ownership
        message = await ChatMessageRepository.get_by_id(db, message_id)
        if not message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Message {message_id} not found"
            )
        
        # Get session to check ownership
        from app.database.repositories.chat_session import ChatSessionRepository
        session = await ChatSessionRepository.get_by_id(db, message.session_id)
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session not found for message {message_id}"
            )
        
        # Check ownership
        if user_id and session.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this message"
            )
        
        # Get all steps for this message in chronological order
        steps = await ChatMessageStepRepository.get_by_message_id(
            db,
            message_id,
            order_by_step=True
        )
        
        # Format steps for response
        formatted_steps = []
        for step in steps:
            step_data = {
                "step_id": str(step.id),
                "agent_name": step.agent_name,
                "step_order": step.step_order,
                "thought": step.thought,
                "created_at": step.created_at.isoformat() if step.created_at else None
            }
            
            # Add content based on what's available
            if step.tool_call:
                step_data["type"] = "tool_call"
                step_data["content"] = step.tool_call
            elif step.structured_output:
                step_data["type"] = "structured_output"
                step_data["content"] = step.structured_output
            elif step.prediction:
                step_data["type"] = "prediction"
                step_data["content"] = step.prediction
            else:
                step_data["type"] = "thought_only"
                step_data["content"] = None
            
            formatted_steps.append(step_data)
        
        logger.info(f"Retrieved {len(formatted_steps)} steps for message {message_id}")
        
        return {
            "message_id": message_id,
            "step_count": len(formatted_steps),
            "steps": formatted_steps
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving message steps: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve message steps: {str(e)}"
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
