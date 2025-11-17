"""
Simple Workflow Service for experimental chat with streaming agent execution.
"""

import json
import uuid
from datetime import datetime
from typing import AsyncGenerator, Dict, Optional

from app.core.config.settings import get_settings
from app.core.llm.simple_workflow.workflow import create_product_review_workflow
from app.core.llm.simple_workflow.utils.context_persistence import (
    load_context_from_session,
    save_context_to_session,
)
from app.database.repositories.chat_message_step import ChatMessageStepRepository
from app.models.chat import ChatRequest, ChatResponse
from app.utils.logging import get_logger
from llama_index.core.agent.workflow import ToolCall, ToolCallResult
from llama_index.core.workflow import Context
from llama_index.llms.openai import OpenAI
from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger("simple_workflow_service")


class SimpleWorkflowService:
    """
    Service for handling chat with simple_workflow multi-agent system.
    
    This service:
    - Initializes the workflow with specialized agents
    - Streams all workflow events (ToolCall, ToolCallResult, agent transitions, content)
    - Saves agent steps to database for persistence
    """

    def __init__(self, settings=None):
        self.settings = settings or get_settings()
        self.llm = None
        
    def _initialize_llm(self):
        """Initialize OpenAI LLM if not already initialized."""
        if self.llm is None:
            api_key = self.settings.openai_api_key
            if not api_key:
                raise ValueError("OPENAI_API_KEY not configured")
            
            self.llm = OpenAI(
                model="gpt-5-mini",
                api_key=api_key,
                temperature=0.1,
            )
            logger.info("Initialized OpenAI LLM for workflow")
    
    async def process_message_stream(
        self,
        request: ChatRequest,
        user_id: Optional[str],
        assistant_message_id: str,
        db: Optional[AsyncSession] = None
    ) -> AsyncGenerator[Dict, None]:
        """
        Process a chat message through the simple_workflow and stream all events.
        
        Args:
            request: Chat request with message and session info
            user_id: User ID for tool binding
            assistant_message_id: ID of the assistant message to save steps to
            db: Database session (not used, kept for compatibility)
            
        Yields:
            Event dictionaries with type and data
        """
        try:
            # Initialize LLM
            self._initialize_llm()
            
            # Create workflow with user_id pre-bound to tools
            workflow = create_product_review_workflow(self.llm, user_id or "default_user")
            
            logger.info(f"Starting workflow for message: {request.message[:100]}")
            
            # Yield initial status
            yield {
                "type": "status",
                "data": {"message": "Initializing workflow..."}
            }
            
            # Create Context and load previous state if available
            ctx = Context(workflow)
            await ctx.store.set("user_id", user_id or "default_user")
            
            # Load previous context state from session if available
            if request.session_id:
                from app.database.session import get_async_session
                async with get_async_session() as load_db:
                    context_loaded = await load_context_from_session(
                        request.session_id, ctx, load_db
                    )
                    if context_loaded:
                        logger.info(f"Restored context state from session {request.session_id}")
                        yield {
                            "type": "status",
                            "data": {"message": "Restored previous context..."}
                        }
            
            # Store conversation history in context for agents to access
            if request.conversation_history:
                await ctx.store.set("conversation_history", request.conversation_history)
                logger.info(f"Added {len(request.conversation_history)} messages to context")
            
            # Start workflow execution with proper context and increased max iterations
            handler = workflow.run(
                user_msg=request.message,
                initial_state={"user_id": user_id or "default_user"},
                ctx=ctx,
                max_iterations=50  # Increased from default 20 to handle SQL error retries
            )
            
            # Yield another status to confirm workflow started
            yield {
                "type": "status",
                "data": {"message": "Workflow started, processing..."}
            }
            
            # Track state
            current_agent = None
            accumulated_content = ""
            step_counter = 0
            agent_steps = []
            
            # Stream events from workflow
            async for event in handler.stream_events():
                event_type = type(event).__name__
                
                # Handle Tool Call events
                if isinstance(event, ToolCall):
                    tool_name = event.tool_name
                    tool_kwargs = event.tool_kwargs
                    
                    logger.info(f"Tool Call: {tool_name} with args: {tool_kwargs}")
                    
                    # Save step to database
                    try:
                        from app.database.session import get_async_session
                        async with get_async_session() as save_db:
                            step = await ChatMessageStepRepository.create(
                                db=save_db,
                                message_id=assistant_message_id,
                                agent_name=current_agent or "workflow",
                                step_order=step_counter,
                                tool_call={
                                    "tool_name": tool_name,
                                    "tool_kwargs": tool_kwargs
                                }
                            )
                            await save_db.commit()
                            step_id = str(step.id)
                    except Exception as db_err:
                        logger.error(f"Failed to save tool call step: {db_err}")
                        step_id = f"step-{step_counter}"
                    
                    agent_steps.append({
                        "step_id": step_id,
                        "agent_name": current_agent or "workflow",
                        "tool_name": tool_name,
                        "tool_kwargs": tool_kwargs,
                        "step_order": step_counter,
                        "status": "running"
                    })
                    
                    step_counter += 1
                    
                    # Yield tool_call event
                    yield {
                        "type": "tool_call",
                        "data": {
                            "tool_name": tool_name,
                            "tool_kwargs": tool_kwargs,
                            "agent_name": current_agent
                        }
                    }
                
                # Handle Tool Call Result events
                elif isinstance(event, ToolCallResult):
                    tool_name = event.tool_name
                    tool_output = event.tool_output
                    tool_kwargs = event.tool_kwargs
                    
                    logger.info(f"Tool Result: {tool_name} returned output")
                    
                    # Check if output indicates an error
                    output_str = str(tool_output)
                    is_error = output_str.startswith("ERROR") or "error" in output_str.lower()[:100]
                    
                    # Update the last step with result
                    if agent_steps and agent_steps[-1].get("tool_name") == tool_name:
                        step_status = "error" if is_error else "completed"
                        agent_steps[-1]["status"] = step_status
                        agent_steps[-1]["tool_output"] = output_str[:500]  # Truncate large outputs
                        
                        # Update step status in database (use lowercase enum values)
                        try:
                            from app.database.session import get_async_session
                            step_id = agent_steps[-1].get("step_id")
                            if step_id and not step_id.startswith("step-"):  # Only update if it's a real DB ID
                                async with get_async_session() as save_db:
                                    await ChatMessageStepRepository.update_status(
                                        db=save_db,
                                        step_id=step_id,
                                        status="error" if is_error else "success"
                                    )
                                    await save_db.commit()
                        except Exception as db_err:
                            logger.error(f"Failed to update step status: {db_err}")
                    
                    # Yield tool_result event
                    yield {
                        "type": "tool_result",
                        "data": {
                            "tool_name": tool_name,
                            "tool_kwargs": tool_kwargs,
                            "output": output_str[:500],  # Truncate for streaming
                            "is_error": is_error
                        }
                    }
                
                # Handle agent transitions
                if hasattr(event, 'agent_name'):
                    new_agent = event.agent_name
                    if new_agent != current_agent:
                        current_agent = new_agent
                        logger.info(f"Agent transition: {current_agent}")
                        
                        # Yield agent event
                        yield {
                            "type": "agent",
                            "data": {"agent_name": current_agent}
                        }
                        
                        # Yield status update
                        yield {
                            "type": "status",
                            "data": {"message": f"Agent: {current_agent}"}
                        }
                
                # Handle streaming content (deltas)
                if hasattr(event, 'delta') and event.delta:
                    delta = event.delta
                    accumulated_content += delta
                    
                    # Yield content chunk
                    yield {
                        "type": "content",
                        "data": {"content": delta}
                    }
                
                # Handle complete messages (fallback if no streaming)
                if hasattr(event, 'msg'):
                    msg = event.msg
                    if hasattr(msg, 'content') and msg.content and not accumulated_content:
                        accumulated_content = msg.content
                        
                        # Yield complete content
                        yield {
                            "type": "content",
                            "data": {"content": msg.content}
                        }
            
            # Get final result
            result = await handler
            
            logger.info(f"Workflow completed with {len(agent_steps)} steps")
            
            # Update assistant message with final content - use separate session
            from app.database.repositories.chat_message import ChatMessageRepository
            from app.database.session import get_async_session
            
            final_content = accumulated_content or "No response generated"
            
            logger.info(f"Saving final content to database: {len(final_content)} chars")
            
            try:
                async with get_async_session() as save_db:
                    await ChatMessageRepository.update(
                        db=save_db,
                        message_id=assistant_message_id,
                        content=final_content,
                        completed_at=datetime.utcnow()
                    )
                    await save_db.commit()
                    logger.info(f"Successfully saved assistant message {assistant_message_id}")
            except Exception as db_err:
                logger.error(f"Failed to update assistant message: {db_err}", exc_info=True)
            
            # Save context state to session for next message
            if request.session_id:
                try:
                    async with get_async_session() as save_db:
                        await save_context_to_session(request.session_id, ctx, save_db)
                        await save_db.commit()
                        logger.info(f"Saved context state to session {request.session_id}")
                except Exception as ctx_err:
                    logger.error(f"Failed to save context state: {ctx_err}")
            
            # Yield completion event
            yield {
                "type": "complete",
                "data": {
                    "message": final_content,
                    "message_id": assistant_message_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "agent_steps": agent_steps,
                    "metadata": {
                        "workflow_type": "simple_workflow",
                        "total_steps": step_counter
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"Error in workflow processing: {e}", exc_info=True)
            
            # Try to save whatever content we have accumulated before the error
            if accumulated_content:
                logger.info(f"Attempting to save accumulated content despite error: {len(accumulated_content)} chars")
                try:
                    from app.database.repositories.chat_message import ChatMessageRepository
                    from app.database.session import get_async_session
                    
                    async with get_async_session() as save_db:
                        await ChatMessageRepository.update(
                            db=save_db,
                            message_id=assistant_message_id,
                            content=accumulated_content,
                            completed_at=datetime.utcnow()
                        )
                        await save_db.commit()
                        logger.info(f"Successfully saved partial content for message {assistant_message_id}")
                except Exception as save_err:
                    logger.error(f"Failed to save partial content: {save_err}", exc_info=True)
            yield {
                "type": "error",
                "data": {"error": str(e)}
            }

