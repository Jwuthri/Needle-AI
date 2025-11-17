"""
Experimental Chat endpoints using simple_workflow multi-agent system.

This provides streaming chat with detailed agent execution visibility:
- Tool calls and results in real-time
- Agent transitions
- Content streaming
"""

import json
import uuid
from typing import Optional

from app.api.deps import check_rate_limit, get_db
from app.core.security.clerk_auth import ClerkUser, get_current_user
from app.database.repositories.chat_message import ChatMessageRepository
from app.database.repositories.chat_session import ChatSessionRepository
from app.database.models.chat_message import MessageRoleEnum
from app.models.chat import ChatRequest
from app.services.simple_workflow_service import SimpleWorkflowService
from app.utils.logging import get_logger
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

logger = get_logger("chat_experimental_api")

router = APIRouter()


@router.post("/stream")
async def send_message_stream_experimental(
    request: ChatRequest,
    current_user: Optional[ClerkUser] = Depends(get_current_user),
    _rate_limit_check=Depends(check_rate_limit),
):
    """
    Send a message to the experimental chat and get streaming AI responses with workflow visibility.

    Returns Server-Sent Events (SSE) stream with:
    - agent: Agent transitions
    - tool_call: When a tool is being called
    - tool_result: When a tool returns results
    - content: Streaming response text chunks
    - status: Status updates
    - complete: Final response with metadata
    - error: If something goes wrong

    Each event is JSON with {type, data} structure.
    """
    try:
        user_id = current_user.id if current_user else None

        # Create our own DB session for setup, then close it before streaming
        from app.database.session import get_async_session
        
        async with get_async_session() as db:
            # Ensure session exists in database
            session_id = request.session_id or str(uuid.uuid4())
            db_session = await ChatSessionRepository.get_by_id(db, session_id)
            if not db_session:
                # Create session with company_id in metadata
                db_session = await ChatSessionRepository.create(
                    db,
                    user_id=user_id,
                    id=session_id,
                    extra_metadata=(
                        {"company_id": request.company_id, "workflow_type": "simple_workflow"}
                        if request.company_id
                        else {"workflow_type": "simple_workflow"}
                    ),
                )
                await db.commit()
                logger.info(f"Created experimental session {session_id}")
            
            # Fetch recent conversation history (last 10 messages = 5 exchanges)
            messages = await ChatMessageRepository.get_recent_messages(db, session_id, limit=10)
            conversation_history = [
                {"role": msg.role.value, "content": msg.content}
                for msg in reversed(messages)  # Reverse to get chronological order
            ]
            
            # Get the last assistant message ID for parent_message_id
            last_assistant_message_id = None
            if messages:
                # Find the most recent assistant message
                for msg in messages:
                    if msg.role == MessageRoleEnum.ASSISTANT:
                        last_assistant_message_id = msg.id
                        break
            
            # Add conversation history to request
            if conversation_history:
                request.conversation_history = conversation_history
                logger.info(f"Added {len(conversation_history)} messages to conversation history")

            # Save user message to database with parent_message_id
            user_message = await ChatMessageRepository.create(
                db=db, 
                session_id=session_id, 
                content=request.message, 
                role=MessageRoleEnum.USER,
                parent_message_id=last_assistant_message_id  # Link to previous assistant message
            )
            await db.commit()
            logger.info(f"Saved user message {user_message.id} to database (parent: {last_assistant_message_id})")
            
            # Create assistant message placeholder with parent_message_id
            assistant_message = await ChatMessageRepository.create(
                db=db,
                session_id=session_id,
                content="",
                role=MessageRoleEnum.ASSISTANT,
                parent_message_id=user_message.id  # Link to user message
            )
            await db.commit()
            assistant_message_id = assistant_message.id
            logger.info(f"[CHAT EXPERIMENTAL] Created assistant message {assistant_message_id} (parent: {user_message.id})")
        
        # DB session is now closed before we start streaming

        # Stream processing function
        async def event_stream():
            from datetime import date, datetime
            import asyncio

            def make_json_serializable(obj):
                """Recursively convert any object to be JSON serializable."""
                if obj is None:
                    return None
                elif isinstance(obj, (datetime, date)):
                    return obj.isoformat()
                elif hasattr(obj, "model_dump"):
                    # Pydantic model
                    return obj.model_dump(mode="json")
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
                # Initialize workflow service
                workflow_service = SimpleWorkflowService()

                # Process stream - workflow creates its own database sessions
                async for update in workflow_service.process_message_stream(
                    request=request, 
                    user_id=user_id, 
                    assistant_message_id=assistant_message_id, 
                    db=None  # Service will create its own sessions
                ):
                    update_count += 1

                    if update["type"] == "content":
                        accumulated_content += update["data"]["content"]
                        logger.debug(
                            f"Streaming content update #{update_count}: {len(update['data']['content'])} chars"
                        )

                    serializable_update = make_json_serializable(update)
                    sse_data = f"data: {json.dumps(serializable_update)}\n\n"
                    yield sse_data

                    if update["type"] == "content":
                        await asyncio.sleep(0.001)

                logger.info(
                    f"Stream completed: {update_count} updates sent, {len(accumulated_content)} chars total"
                )

            except Exception as e:
                logger.error(f"Stream error: {e}", exc_info=True)
                error_event = {"type": "error", "data": {"error": str(e)}}
                yield f"data: {json.dumps(error_event)}\n\n"

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
            },
        )

    except Exception as e:
        logger.error(f"Chat experimental stream error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Stream failed: {str(e)}"
        )

