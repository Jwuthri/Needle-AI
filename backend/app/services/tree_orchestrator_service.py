"""
Tree-based Orchestrator Service.

Integrates tree architecture with the existing chat system,
providing streaming agent steps to frontend and DB persistence.
"""

import uuid
from datetime import datetime
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional

from app.agents.tree.workflows.multi_branch import create_multi_branch_workflow
from app.agents.tree.executors.agno_executor import AgnoTreeExecutor
from app.config import get_settings
from app.models.chat import ChatRequest, ChatResponse
from app.database.models.llm_call import LLMCallTypeEnum, LLMCallStatusEnum
from app.utils.logging import get_logger

logger = get_logger("tree_orchestrator_service")


class TreeOrchestratorService:
    """
    Orchestrator service using tree-based architecture.
    
    Provides:
    - Tree-based decision making
    - Step-by-step agent streaming
    - Database persistence of steps
    - Compatible with existing chat API
    """
    
    def __init__(self, settings: Any = None):
        """
        Initialize tree orchestrator.
        
        Args:
            settings: Application settings
        """
        self.settings = settings or get_settings()
        self.executor: Optional[AgnoTreeExecutor] = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize the tree orchestrator."""
        if self._initialized:
            return
        
        try:
            # Create model
            model = self._create_model()
            
            # Create database for persistence
            db = await self._create_persistence_db()
            
            # Create multi-branch workflow executor
            self.executor = create_multi_branch_workflow(
                name="NeedleAI Tree Workflow",
                model=model,
                db=db,
                settings=self.settings
            )
            
            self._initialized = True
            logger.info("Tree orchestrator service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize tree orchestrator: {e}")
            raise
    
    def _create_model(self):
        """Create OpenRouter model instance."""
        from agno.models.openrouter import OpenRouter
        
        api_key = self.settings.get_secret("openrouter_api_key")
        if not api_key:
            raise ValueError("OpenRouter API key not configured")
        
        api_key_str = str(api_key) if hasattr(api_key, '__str__') else api_key
        
        return OpenRouter(
            id=self.settings.default_model,
            api_key=api_key_str,
            max_tokens=4096
        )
    
    async def _create_persistence_db(self) -> Optional[Any]:
        """Create PostgreSQL database for persistence."""
        try:
            from agno.db.postgres import PostgresDb
            
            db_config = self.settings.parse_database_url()
            db_url = (
                f"postgresql+psycopg://{db_config['user']}:{db_config['password']}"
                f"@{db_config['host']}:{db_config['port']}"
                f"/{db_config['database']}"
            )
            
            db = PostgresDb(
                db_url=db_url,
                table_name="agno_tree_orchestrator"
            )
            logger.info("Created PostgreSQL DB for tree orchestrator persistence")
            return db
        except Exception as e:
            logger.warning(f"Failed to create persistence DB: {e}")
            return None
    
    async def process_message_stream(
        self,
        request: ChatRequest,
        user_id: Optional[str] = None,
        db: Optional[Any] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Process chat message with tree-based orchestration and streaming.
        
        Yields:
        - agent_step_start: When an agent begins
        - agent_step_content: Streaming content from agent
        - agent_step_complete: When agent finishes (with full content)
        - content: Final response streaming
        - complete: Final response with metadata
        
        Args:
            request: Chat request
            user_id: User ID
            db: Database session
            
        Yields:
            Dict with update type and data
        """
        if not self._initialized:
            await self.initialize()
        
        session_id = request.session_id or "default"
        message_id = str(uuid.uuid4())
        
        # Create stream callback
        queued_updates = []
        
        async def stream_callback(update: Dict[str, Any]):
            """Callback to queue updates for streaming."""
            queued_updates.append(update)
        
        try:
            # Send initial status
            yield {
                "type": "connected",
                "data": {}
            }
            
            # Build context message
            context_message = await self._build_context_message(request, db)
            
            yield {
                "type": "status",
                "data": {"status": "tree_executing", "message": "Starting tree execution..."}
            }
            
            logger.info(f"Starting tree execution for session {session_id}")
            
            # Execute tree with streaming
            response_content = ""
            
            async for chunk in self.executor.run(
                user_prompt=context_message,
                stream_callback=stream_callback,
                db_session=db,
                message_id=message_id,
                user_id=user_id,
                session_id=session_id
            ):
                # Yield any queued updates from stream_callback
                while queued_updates:
                    update = queued_updates.pop(0)
                    yield update
                
                # Handle team streaming events
                event_type = getattr(chunk, 'event', 'N/A')
                
                if event_type == "TeamRunContent":
                    # Stream final response content
                    content_chunk = chunk.content if hasattr(chunk, 'content') else str(chunk)
                    if isinstance(content_chunk, str):
                        response_content += content_chunk
                        yield {
                            "type": "content",
                            "data": {"content": content_chunk}
                        }
                
                elif event_type == "TeamRunResponse":
                    # Final response available
                    if hasattr(chunk, 'content') and chunk.content:
                        full_content = chunk.content
                        
                        # If we haven't streamed anything yet, stream it now
                        if len(response_content) == 0:
                            import asyncio
                            chunk_size = 50
                            for i in range(0, len(full_content), chunk_size):
                                content_chunk = full_content[i:i+chunk_size]
                                yield {
                                    "type": "content",
                                    "data": {"content": content_chunk}
                                }
                                await asyncio.sleep(0.01)
                        # If partially streamed, send remainder
                        elif len(full_content) > len(response_content):
                            remaining = full_content[len(response_content):]
                            yield {
                                "type": "content",
                                "data": {"content": remaining}
                            }
                        
                        response_content = full_content
            
            # Yield any remaining queued updates
            while queued_updates:
                update = queued_updates.pop(0)
                yield update
            
            # Ensure we have response content
            if not response_content:
                response_content = "Tree execution completed. Check agent steps for details."
            
            # Create final response
            chat_response = ChatResponse(
                message=response_content,
                session_id=session_id,
                message_id=message_id,
                timestamp=datetime.utcnow(),
                metadata={
                    "model": self.settings.default_model,
                    "provider": "agno_tree",
                    "user_id": user_id,
                    "tree_name": self.executor.tree.name
                }
            )
            
            # Send final response
            yield {
                "type": "complete",
                "data": chat_response.dict()
            }
            
        except Exception as e:
            logger.error(f"Error processing tree message: {e}", exc_info=True)
            
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
        Process message using tree orchestrator (non-streaming).
        
        Args:
            request: Chat request
            user_id: User ID
            db: Database session
            
        Returns:
            ChatResponse with result
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            session_id = request.session_id or "default"
            message_id = str(uuid.uuid4())
            
            # Build context message
            context_message = await self._build_context_message(request, db)
            
            # Execute tree (collect all chunks)
            response_content = ""
            
            async for chunk in self.executor.run(
                user_prompt=context_message,
                stream_callback=None,  # No streaming callback
                db_session=db,
                message_id=message_id,
                user_id=user_id,
                session_id=session_id
            ):
                # Extract content from chunks
                if hasattr(chunk, 'content'):
                    content = chunk.content
                    if isinstance(content, str):
                        response_content += content
            
            if not response_content:
                response_content = "Tree execution completed."
            
            # Create response
            chat_response = ChatResponse(
                message=response_content,
                session_id=session_id,
                message_id=message_id,
                timestamp=datetime.utcnow(),
                metadata={
                    "model": self.settings.default_model,
                    "provider": "agno_tree",
                    "user_id": user_id,
                    "tree_name": self.executor.tree.name
                }
            )
            
            logger.debug(f"Processed tree message for session {session_id}")
            return chat_response
            
        except Exception as e:
            logger.error(f"Error processing tree message: {e}", exc_info=True)
            
            return ChatResponse(
                message=f"I encountered an error processing your request: {str(e)}",
                session_id=request.session_id or "default",
                message_id=str(uuid.uuid4()),
                timestamp=datetime.utcnow(),
                metadata={
                    "error": str(e)
                }
            )
    
    async def _build_context_message(self, request: ChatRequest, db: Optional[Any]) -> str:
        """
        Build context message with NeedleAI info and company context.
        
        Args:
            request: Chat request
            db: Database session
            
        Returns:
            Formatted context message
        """
        context = """You are NeedleAI, an AI-powered product analytics assistant using a tree-based decision architecture.

You have access to:
- Product reviews and customer feedback from various sources (G2, Capterra, Trustpilot, etc.)
- Statistical aggregation tools
- Data visualization capabilities
- Web search for external information

Your goal is to provide actionable insights based on customer feedback and data."""
        
        # Add company context if provided
        if request.company_id and db:
            try:
                from app.database.repositories.company import CompanyRepository
                company = await CompanyRepository.get_by_id(db, request.company_id)
                if company:
                    context += f"\n\nCurrent context: Analyzing data for {company.name}"
                else:
                    context += f"\n\nCurrent context: Analyzing data for company ID {request.company_id}"
            except Exception as e:
                logger.warning(f"Failed to load company info: {e}")
                context += f"\n\nCurrent context: Analyzing data for company ID {request.company_id}"
        
        # Add user's query
        context += f"\n\nUser query: {request.message}"
        
        return context
    
    async def cleanup(self):
        """Cleanup resources."""
        self._initialized = False
        logger.debug("Tree orchestrator service cleaned up")

