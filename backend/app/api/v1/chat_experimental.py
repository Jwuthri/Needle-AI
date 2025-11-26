"""
Experimental Chat endpoints using LangGraph multi-agent system.

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
from app.utils.logging import get_logger
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage, AIMessage

from app.core.llm.lg_workflow.graph import create_workflow

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
                        {"company_id": request.company_id, "workflow_type": "lg_workflow"}
                        if request.company_id
                        else {"workflow_type": "lg_workflow"}
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
            
            # Save user message to database
            user_message = await ChatMessageRepository.create(
                db=db, 
                session_id=session_id, 
                content=request.message, 
                role=MessageRoleEnum.USER,
            )
            await db.commit()
            logger.info(f"Saved user message {user_message.id} to database")
            
            # Create assistant message placeholder
            assistant_message = await ChatMessageRepository.create(
                db=db,
                session_id=session_id,
                content="",
                role=MessageRoleEnum.ASSISTANT,
            )
            await db.commit()
            assistant_message_id = assistant_message.id
            logger.info(f"[CHAT EXPERIMENTAL] Created assistant message {assistant_message_id}")
        
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
            current_agent = None
            agent_steps = []  # Track agent execution steps
            
            try:
                # Initialize workflow
                app = create_workflow(user_id)
                
                # Prepare input
                inputs = {
                    "messages": [HumanMessage(content=request.message)]
                }
                
                # Config for checkpointing (optional, but good for history)
                config = {"configurable": {"thread_id": session_id}}

                # Stream events using v2 for better event capture
                async for event in app.astream_events(inputs, config=config, version="v2"):
                    kind = event.get("event")
                    name = event.get("name", "")
                    
                    # Track agent transitions
                    if kind == "on_chain_start":
                        if name in ["DataLibrarian", "DataAnalyst", "Researcher", "Visualizer", "Reporter"]:
                            if current_agent != name:
                                current_agent = name
                                # Add to agent_steps
                                agent_steps.append({
                                    "step_id": f"step_{len(agent_steps)}",
                                    "agent_name": name,
                                    "status": "started",
                                    "content": "",
                                    "timestamp": datetime.utcnow().isoformat()
                                })
                                yield f"data: {json.dumps({'type': 'agent', 'data': {'agent_name': name, 'status': 'started'}})}\n\n"
                    
                    # Stream content chunks from LLM
                    elif kind == "on_chat_model_stream":
                        chunk = event.get("data", {}).get("chunk")
                        if chunk and hasattr(chunk, 'content') and chunk.content:
                            content = chunk.content
                            
                            # Filter out routing decisions - be precise to avoid removing spaces/formatting
                            import re
                            # Only match exact JSON patterns: {"next":"AgentName"} or {'next':'AgentName'}
                            content = re.sub(r'\{\s*["\']next["\']\s*:\s*["\'][^"\']*["\']\s*\}', '', content)
                            
                            if content:  # Only send if there's content after filtering
                                accumulated_content += content
                                # Add to current agent step content
                                if agent_steps and agent_steps[-1].get("agent_name") == current_agent:
                                    if isinstance(agent_steps[-1].get("content"), str):
                                        agent_steps[-1]["content"] += content
                                    else:
                                        # Last step was structured (tool), but we got text.
                                        # Create a new text step for the same agent.
                                        agent_steps.append({
                                            "step_id": f"step_{len(agent_steps)}",
                                            "agent_name": current_agent,
                                            "status": "active",
                                            "content": content,
                                            "timestamp": datetime.utcnow().isoformat()
                                        })
                                yield f"data: {json.dumps({'type': 'content', 'data': {'content': content}})}\n\n"
                    
                    # Tool execution tracking
                    elif kind == "on_tool_start":
                        tool_name = event.get("name", "")
                        tool_input = event.get("data", {}).get("input", {})
                        
                        # Add a structured step for the tool call
                        agent_steps.append({
                            "step_id": f"step_{len(agent_steps)}",
                            "agent_name": current_agent or tool_name, # Use current agent context
                            "status": "active",
                            "content": {"tool_name": tool_name, "tool_kwargs": tool_input},
                            "is_structured": True,
                            "timestamp": datetime.utcnow().isoformat()
                        })
                        
                        yield f"data: {json.dumps({'type': 'tool_call', 'data': {'tool': tool_name, 'input': tool_input}})}\n\n"
                        
                    elif kind == "on_tool_end":
                        tool_name = event.get("name", "")
                        tool_output = event.get("data", {}).get("output")
                        
                        # Update the last step (which should be the tool call)
                        if agent_steps and agent_steps[-1].get("is_structured"):
                            agent_steps[-1]["raw_output"] = str(tool_output)
                            agent_steps[-1]["status"] = "completed"
                        
                        yield f"data: {json.dumps({'type': 'tool_result', 'data': {'tool': tool_name, 'output': str(tool_output)}})}\n\n"

                # Mark all steps as completed
                for step in agent_steps:
                    if step.get("status") == "started" or step.get("status") == "active":
                        step["status"] = "completed"
                    
                    # CLEANUP: Remove routing JSON from step content that might have been missed during streaming
                    if step.get("content") and isinstance(step.get("content"), str):
                        import re
                        step["content"] = re.sub(r'\{\s*["\']next["\']\s*:\s*["\'][^"\']*["\']\s*\}', '', step["content"])
                
                # Use only the last agent's content as the main message content to avoid duplication of history
                # because accumulated_content contains everything
                final_content = ""
                if agent_steps:
                    # Find the last agent that actually produced content (and is text, not structured)
                    for step in reversed(agent_steps):
                        content = step.get("content")
                        if content and isinstance(content, str) and content.strip():
                            final_content = content
                            break
                    
                    # Clean up routing JSON from final content too just in case
                    import re
                    final_content = re.sub(r'\{\s*["\']next["\']\s*:\s*["\'][^"\']*["\']\s*\}', '', final_content).strip()
                
                # Fallback to accumulated if steps failed for some reason
                if not final_content and accumulated_content:
                     final_content = re.sub(r'\{\s*["\']next["\']\s*:\s*["\'][^"\']*["\']\s*\}', '', accumulated_content).strip()

                logger.info(f"Saving {len(agent_steps)} agent steps to message {assistant_message_id}")
                logger.debug(f"Agent steps data: {agent_steps}")
                
                # Save final response with agent_steps in extra_metadata
                async with get_async_session() as db:
                    updated_msg = await ChatMessageRepository.update(
                        db, 
                        assistant_message_id, 
                        content=final_content,
                        completed_at=datetime.utcnow(),
                        extra_metadata={"agent_steps": agent_steps}
                    )
                    await db.commit()
                    
                    # Verify it was saved
                    if updated_msg:
                        logger.info(f"Message updated. extra_metadata: {updated_msg.extra_metadata}")
                    else:
                        logger.error(f"Failed to update message {assistant_message_id}")

                yield f"data: {json.dumps({'type': 'complete', 'data': {'content': final_content}})}\n\n"

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
