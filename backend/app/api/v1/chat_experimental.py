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
            seen_agents = set()  # Track which agents we've already created boxes for
            
            try:
                # Initialize workflow with optional focused dataset
                app = create_workflow(user_id, dataset_table_name=request.dataset_table_name)
                
                # Prepare input with conversation history
                # Convert history to LangChain message format
                history_messages = []
                for msg in conversation_history:
                    if msg["role"] == "user":
                        history_messages.append(HumanMessage(content=msg["content"]))
                    elif msg["role"] == "assistant":
                        history_messages.append(AIMessage(content=msg["content"]))
                
                # Add current message
                history_messages.append(HumanMessage(content=request.message))
                
                inputs = {
                    "messages": history_messages
                }
                
                # Config for checkpointing (optional, but good for history)
                config = {"configurable": {"thread_id": session_id}}

                # Stream events using v2 for better event capture
                async for event in app.astream_events(inputs, config=config, version="v2", recursion_limit=50):
                    kind = event.get("event")
                    name = event.get("name", "")
                    
                    # Track agent transitions - NEVER create duplicate boxes for same agent
                    if kind == "on_chain_start":
                        if name in ["DataLibrarian", "DataAnalyst", "Researcher", "Visualizer", "Reporter"]:
                            # Only emit agent event if we haven't seen this agent yet
                            if name not in seen_agents:
                                seen_agents.add(name)
                                current_agent = name
                                # Add to agent_steps for persistence
                                agent_steps.append({
                                    "step_id": f"step_{len(agent_steps)}",
                                    "agent_name": name,
                                    "status": "active",
                                    "content": "",
                                    "is_structured": False,
                                    "timestamp": datetime.utcnow().isoformat()
                                })
                                yield f"data: {json.dumps({'type': 'agent', 'data': {'agent_name': name, 'status': 'started'}})}\n\n"
                            else:
                                # Just update current tracking without emitting new event
                                current_agent = name
                    
                    # Stream content chunks from LLM
                    elif kind == "on_chat_model_stream":
                        chunk = event.get("data", {}).get("chunk")
                        if chunk and hasattr(chunk, 'content') and chunk.content:
                            content = chunk.content
                            
                            # Filter out routing decisions
                            import re
                            content = re.sub(r'\{\s*["\']next["\']\s*:\s*["\'][^"\']*["\']\s*\}', '', content)
                            
                            if content:
                                accumulated_content += content
                                # Update the current agent's step content
                                for step in reversed(agent_steps):
                                    if step.get("agent_name") == current_agent and not step.get("is_structured"):
                                        if isinstance(step.get("content"), str):
                                            step["content"] += content
                                        break
                                
                                yield f"data: {json.dumps({'type': 'content', 'data': {'content': content}})}\n\n"
                    
                    # Tool execution tracking
                    elif kind == "on_tool_start":
                        tool_name = event.get("name", "")
                        tool_input = event.get("data", {}).get("input", {})
                        
                        # Serialize tool input properly
                        serializable_input = make_json_serializable(tool_input)
                        
                        # Add a structured step for the tool call
                        agent_steps.append({
                            "step_id": f"step_{len(agent_steps)}",
                            "agent_name": current_agent or "workflow",
                            "status": "active",
                            "content": {"tool_name": tool_name, "tool_kwargs": serializable_input},
                            "is_structured": True,
                            "timestamp": datetime.utcnow().isoformat()
                        })
                        
                        yield f"data: {json.dumps({'type': 'tool_call', 'data': {'tool': tool_name, 'input': serializable_input}})}\n\n"
                        
                    elif kind == "on_tool_end":
                        tool_name = event.get("name", "")
                        tool_output = event.get("data", {}).get("output")
                        output_str = str(tool_output) if tool_output else ""
                        
                        # Find and update the matching tool step
                        for step in reversed(agent_steps):
                            if step.get("is_structured") and step.get("status") == "active":
                                if step.get("content", {}).get("tool_name") == tool_name:
                                    step["raw_output"] = output_str
                                    step["status"] = "completed"
                                    break
                        
                        yield f"data: {json.dumps({'type': 'tool_result', 'data': {'tool': tool_name, 'output': output_str}})}\n\n"

                import re
                
                # Mark all steps as completed and clean up content
                for step in agent_steps:
                    if step.get("status") in ("started", "active"):
                        step["status"] = "completed"
                    
                    # Clean routing JSON from text content
                    if step.get("content") and isinstance(step.get("content"), str):
                        step["content"] = re.sub(r'\{\s*["\']next["\']\s*:\s*["\'][^"\']*["\']\s*\}', '', step["content"]).strip()
                
                # Get Reporter's content as the final answer (prioritize Reporter)
                final_content = ""
                reporter_step = None
                for step in reversed(agent_steps):
                    if step.get("agent_name", "").upper() == "REPORTER":
                        content = step.get("content")
                        if content and isinstance(content, str) and content.strip():
                            final_content = content
                            reporter_step = step
                            break
                
                # Fallback to last text content if no Reporter
                if not final_content:
                    for step in reversed(agent_steps):
                        content = step.get("content")
                        if content and isinstance(content, str) and content.strip() and not step.get("is_structured"):
                            final_content = content
                            break
                
                # Final fallback to accumulated content
                if not final_content and accumulated_content:
                    final_content = re.sub(r'\{\s*["\']next["\']\s*:\s*["\'][^"\']*["\']\s*\}', '', accumulated_content).strip()

                logger.info(f"Saving {len(agent_steps)} agent steps to message {assistant_message_id}")
                
                # Save final response with agent_steps in extra_metadata
                completed_at = datetime.utcnow()
                async with get_async_session() as db:
                    updated_msg = await ChatMessageRepository.update(
                        db, 
                        assistant_message_id, 
                        content=final_content,
                        completed_at=completed_at,
                        extra_metadata={"agent_steps": agent_steps}
                    )
                    await db.commit()
                    
                    if updated_msg:
                        logger.info(f"Message updated successfully")
                    else:
                        logger.error(f"Failed to update message {assistant_message_id}")

                # Send complete event with full response structure
                yield f"data: {json.dumps({'type': 'complete', 'data': {'message_id': str(assistant_message_id), 'message': final_content, 'timestamp': datetime.utcnow().isoformat(), 'completed_at': completed_at.isoformat(), 'metadata': {'agent_steps': agent_steps}}})}\n\n"

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
