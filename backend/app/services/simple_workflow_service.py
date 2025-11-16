"""
Simple Workflow Service for experimental chat with streaming agent execution.
"""

import json
import uuid
from datetime import datetime
from typing import AsyncGenerator, Dict, Optional

from app.core.config.settings import get_settings
from app.core.llm.simple_workflow.workflow import create_product_review_workflow
from app.database.repositories.chat_message_step import ChatMessageStepRepository
from app.models.chat import ChatRequest, ChatResponse
from app.utils.logging import get_logger
from llama_index.core.agent.workflow import ToolCall, ToolCallResult
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
            
            # Start workflow execution with proper context (matching main.py pattern)
            handler = workflow.run(
                user_msg=request.message,
                initial_state={"user_id": user_id or "default_user"}
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
                    
                    # Update the last step with result
                    if agent_steps and agent_steps[-1].get("tool_name") == tool_name:
                        agent_steps[-1]["status"] = "completed"
                        agent_steps[-1]["tool_output"] = str(tool_output)[:500]  # Truncate large outputs
                    
                    # Yield tool_result event
                    yield {
                        "type": "tool_result",
                        "data": {
                            "tool_name": tool_name,
                            "tool_kwargs": tool_kwargs,
                            "output": str(tool_output)[:500]  # Truncate for streaming
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
            
            try:
                async with get_async_session() as save_db:
                    await ChatMessageRepository.update(
                        db=save_db,
                        message_id=assistant_message_id,
                        content=final_content,
                        completed_at=datetime.utcnow()
                    )
                    await save_db.commit()
            except Exception as db_err:
                logger.error(f"Failed to update assistant message: {db_err}")
            
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
            yield {
                "type": "error",
                "data": {"error": str(e)}
            }

