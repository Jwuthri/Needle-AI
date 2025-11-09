"""
Workflow Orchestrator Service - Wraps LlamaIndex optimal_workflow.

This service provides a bridge between the FastAPI chat API and the 
LlamaIndex workflow, implementing the orchestrator interface expected
by the chat endpoints.
"""

import uuid
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, Optional

from app.models.chat import ChatRequest, ChatResponse
from app.optimal_workflow.main import run_workflow, run_workflow_streaming
from app.utils.logging import get_logger

logger = get_logger("workflow_orchestrator_service")


class WorkflowOrchestratorService:
    """
    Orchestrator service using LlamaIndex workflow.
    
    Provides compatibility layer between chat API and optimal_workflow.
    """
    
    def __init__(self, settings: Any = None):
        """
        Initialize workflow orchestrator.
        
        Args:
            settings: Application settings (optional, will use get_settings if not provided)
        """
        from app.core.config.settings import get_settings
        self.settings = settings or get_settings()
        self._initialized = False
    
    async def initialize(self):
        """Initialize the orchestrator."""
        if self._initialized:
            return
        
        try:
            # Verify settings are configured
            if not self.settings.get_secret("openrouter_api_key"):
                raise ValueError("OpenRouter API key not configured")
            
            self._initialized = True
            logger.info("Workflow orchestrator service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize workflow orchestrator: {e}")
            raise
    
    async def process_message_stream(
        self,
        request: ChatRequest,
        user_id: Optional[str] = None,
        assistant_message_id: Optional[int] = None,
        db: Optional[Any] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Process chat message with streaming updates.
        
        Yields progress updates including:
        - connected: Initial connection
        - status: Status updates
        - agent_step_start: When an agent begins
        - agent_step_content: Streaming content from agent
        - agent_step_complete: When agent finishes
        - content: Final response streaming
        - complete: Final response with metadata
        - error: If something goes wrong
        
        Args:
            request: Chat request
            user_id: User ID
            assistant_message_id: ID of assistant message for saving steps
            db: Database session (not used by workflow, kept for interface compatibility)
            
        Yields:
            Dict with update type and data
        """
        if not self._initialized:
            await self.initialize()
        
        session_id = request.session_id or str(uuid.uuid4())
        
        try:
            # Send initial status
            yield {
                "type": "connected",
                "data": {}
            }
            
            logger.info(f"Starting workflow execution for session {session_id}, assistant_message_id={assistant_message_id}")
            
            # Execute workflow with streaming - workflow now handles DB storage directly
            async for event in run_workflow_streaming(
                query=request.message,
                user_id=user_id,
                session_id=session_id,
                assistant_message_id=assistant_message_id
            ):
                # Yield the event to the chat API
                yield event
            
            logger.info(f"Workflow execution completed for session {session_id}")
            
        except Exception as e:
            logger.error(f"Error in workflow execution: {e}", exc_info=True)
            
            yield {
                "type": "error",
                "data": {
                    "error": str(e)
                }
            }
    
    async def process_message(
        self,
        request: ChatRequest,
        user_id: Optional[str] = None,
        db: Optional[Any] = None
    ) -> ChatResponse:
        """
        Process a chat message using the workflow (non-streaming).
        
        Args:
            request: Chat request
            user_id: User ID
            db: Database session (not used by workflow, kept for interface compatibility)
            
        Returns:
            ChatResponse with result
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            session_id = request.session_id or str(uuid.uuid4())
            
            logger.info(f"Starting non-streaming workflow execution for session {session_id}")
            
            # Execute workflow without streaming
            result = await run_workflow(
                query=request.message,
                user_id=user_id,
                session_id=session_id
            )
            
            # Create response
            chat_response = ChatResponse(
                message=result,
                session_id=session_id,
                message_id=str(uuid.uuid4()),
                timestamp=datetime.utcnow(),
                metadata={
                    "model": self.settings.default_model,
                    "provider": "llamaindex_workflow",
                    "user_id": user_id
                }
            )
            
            logger.info(f"Non-streaming workflow execution completed for session {session_id}")
            return chat_response
            
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            
            # Return error response
            return ChatResponse(
                message=f"I encountered an error processing your request: {str(e)}",
                session_id=request.session_id or "default",
                message_id=str(uuid.uuid4()),
                timestamp=datetime.utcnow(),
                metadata={
                    "error": str(e)
                }
            )
    
    async def cleanup(self):
        """Cleanup resources."""
        self._initialized = False
        logger.debug("Workflow orchestrator service cleaned up")

