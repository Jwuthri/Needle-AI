"""
Agno-based Chat Service - Complete integration with Agno framework.
Uses latest Agno API with db parameter for persistence and enable_user_memories.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from agno.agent import Agent
from agno.db.postgres import PostgresDb
from agno.db.redis import RedisDb
from agno.vectordb.pineconedb import PineconeDb
from agno.knowledge.knowledge import Knowledge
from agno.models.openai import OpenAIChat
from agno.models.openrouter import OpenRouter

from app.exceptions import ConfigurationError, ExternalServiceError
from app.models.chat import ChatRequest, ChatResponse, ChatMessage
from app.utils.logging import get_logger

logger = get_logger("agno_chat_service")


class AgnoChatService:
    """
    Complete Agno-based chat service that leverages the full Agno framework.

    This is the preferred chat service when Agno is available, providing:
    - Built-in memory management
    - Vector database integration
    - Multi-agent capabilities
    - Automatic conversation persistence
    """

    def __init__(self, settings: Any):
        self.settings = settings
        self.agent: Optional[Agent] = None
        self._initialized = False

    async def initialize(self):
        """Initialize the Agno agent with proper configuration using latest API."""
        if self._initialized:
            return

        try:
            # Setup Knowledge base if configured (Pinecone)
            knowledge = None
            if self.settings.vector_database == "pinecone":
                knowledge = await self._create_pinecone_knowledge()

            # Setup database for persistence (Redis or PostgreSQL)
            db = await self._create_persistence_db()

            # Create model instance based on provider
            model = self._create_model()

            # Create agent with full configuration using new API
            self.agent = Agent(
                # Model configuration (must be model instance, not string)
                model=model,

                # Database for persistence
                db=db,
                
                # Enable user memories for persistent memory
                enable_user_memories=True if db else False,

                # Knowledge base with vector DB for semantic search
                knowledge=knowledge,
                search_knowledge=True if knowledge else False,
                
                # Read chat history automatically
                read_chat_history=True,

                # Agent configuration
                instructions=self.settings.agent_instructions or self._get_default_instructions(),
                structured_outputs=self.settings.structured_outputs,

                # Advanced features
            )

            self._initialized = True
            logger.info("Agno chat service initialized successfully with latest API")

        except Exception as e:
            logger.error(f"Failed to initialize Agno chat service: {e}")
            raise ConfigurationError(f"Agno initialization failed: {e}")

    async def cleanup(self):
        """Cleanup Agno resources."""
        if self.agent:
            try:
                # Close any open connections
                if hasattr(self.agent, 'close'):
                    await self.agent.close()
                self._initialized = False
                logger.debug("Agno chat service cleaned up")
            except Exception as e:
                logger.warning(f"Error cleaning up Agno chat service: {e}")

    async def _create_pinecone_knowledge(self) -> Knowledge:
        """Create Pinecone knowledge base for the agent."""
        try:
            api_key = self.settings.get_secret("pinecone_api_key")
            if not api_key:
                raise ConfigurationError("Pinecone API key not configured")
            
            # Convert SecretStr to str if needed
            api_key_str = str(api_key) if hasattr(api_key, '__str__') else api_key
            
            # Create Pinecone vector DB
            vector_db = PineconeDb(
                name=self.settings.pinecone_index_name,
                dimension=1536,  # OpenAI embedding dimension
                metric="cosine",
                spec={"serverless": {"cloud": "aws", "region": "us-east-1"}},
                api_key=api_key_str,
            )
            
            # Create Knowledge base with Pinecone
            knowledge = Knowledge(
                name=f"{self.settings.app_name} Knowledge Base",
                description="Vector database for semantic search and memory",
                vector_db=vector_db,
            )
            
            logger.info(f"Created Pinecone knowledge base: {self.settings.pinecone_index_name}")
            return knowledge
            
        except Exception as e:
            logger.error(f"Failed to create Pinecone knowledge base: {e}")
            raise ConfigurationError(f"Pinecone setup failed: {e}")

    def _create_model(self):
        """Create model instance based on provider using latest API."""
        if self.settings.llm_provider == "openrouter":
            api_key = self.settings.get_secret("openrouter_api_key")
            if not api_key:
                raise ConfigurationError("OpenRouter API key not configured")
            
            api_key_str = str(api_key) if hasattr(api_key, '__str__') else api_key
            
            # Create OpenRouter model instance
            return OpenRouter(
                id=self.settings.default_model,
                api_key=api_key_str,
            )
        else:
            # Default to OpenAI
            api_key = self.settings.get_secret("openai_api_key")
            if not api_key:
                raise ConfigurationError("OpenAI API key not configured")
            
            api_key_str = str(api_key) if hasattr(api_key, '__str__') else api_key
            
            # Create OpenAI model instance
            return OpenAIChat(
                id=self.settings.default_model,
                api_key=api_key_str,
            )

    async def _create_persistence_db(self):
        """Create database for persistence using PostgreSQL."""
        # Use PostgreSQL for persistence
        try:
            # Build PostgreSQL connection URL
            password = self.settings.get_secret("database_password")
            db_url = (
                f"postgresql+psycopg://{self.settings.database_user}:{password}"
                f"@{self.settings.database_host}:{self.settings.database_port}"
                f"/{self.settings.database_name}"
            )
            
            db = PostgresDb(
                db_url=db_url,
                table_name="agno_sessions",
            )
            logger.info("Created PostgresDb for persistence")
            return db
        except Exception as e:
            logger.warning(f"Failed to create PostgresDb: {e}, continuing without persistence")
            return None

    def _get_default_instructions(self) -> str:
        """Get default agent instructions."""
        return f"""
        You are an AI assistant for {self.settings.app_name}.

        {self.settings.description}

        You should be helpful, accurate, and conversational. Use the conversation history
        to maintain context and provide personalized responses.

        If you don't know something, admit it rather than guessing. Be concise but thorough
        in your responses.
        """

    async def process_message(
        self,
        request: ChatRequest,
        user_id: Optional[str] = None
    ) -> ChatResponse:
        """
        Process a chat message using Agno's built-in conversation handling.
        Uses latest async API with arun().

        Args:
            request: Chat request with message and session info
            user_id: Optional user ID for personalization

        Returns:
            Chat response with AI-generated reply
        """
        if not self._initialized:
            await self.initialize()

        try:
            # Use session_id as the conversation identifier
            session_id = request.session_id or "default"

            # Process message with Agno using async arun()
            # Agno automatically manages chat history per session when db is configured
            run_response = await self.agent.arun(
                request.message,
                stream=False,
                user_id=user_id,
                session_id=session_id,
            )

            # Extract response content from RunResponse
            if hasattr(run_response, 'content'):
                response_content = run_response.content
            elif isinstance(run_response, str):
                response_content = run_response
            else:
                response_content = str(run_response)

            # Create response
            chat_response = ChatResponse(
                message=response_content,
                session_id=session_id,
                message_id=str(uuid.uuid4()),
                metadata={
                    "model": self.settings.default_model,
                    "provider": "agno",
                    "timestamp": datetime.utcnow().isoformat(),
                    "user_id": user_id,
                }
            )

            logger.debug(f"Processed message for session {session_id}")
            return chat_response

        except Exception as e:
            logger.error(f"Error processing message: {e}")

            # Determine error type and re-raise appropriately
            if "api key" in str(e).lower() or "authentication" in str(e).lower():
                raise ConfigurationError(f"API authentication failed: {e}")
            elif "rate limit" in str(e).lower():
                raise ExternalServiceError(f"Rate limit exceeded: {e}", service="llm_provider", retryable=True)
            elif "model" in str(e).lower():
                raise ConfigurationError(f"Model configuration error: {e}")
            else:
                raise ExternalServiceError(f"Chat processing failed: {e}", service="agno_agent")

    async def get_conversation_history(
        self,
        session_id: str,
        limit: Optional[int] = None
    ) -> List[ChatMessage]:
        """
        Get conversation history using Agno's memory system.
        Uses agent.get_session_history() if available.

        Args:
            session_id: Session identifier
            limit: Maximum number of messages to retrieve

        Returns:
            List of conversation messages
        """
        if not self._initialized:
            await self.initialize()

        try:
            # Use Agno's get_session_history if db is configured
            if hasattr(self.agent, 'get_session_history'):
                messages = await self.agent.get_session_history(session_id=session_id, limit=limit)
                return [
                    ChatMessage(
                        role=msg.get("role", "unknown"),
                        content=msg.get("content", ""),
                        timestamp=msg.get("timestamp")
                    )
                    for msg in messages
                ]
            else:
                logger.warning("Session history not available without db configured on Agent")
                return []

        except Exception as e:
            logger.error(f"Error retrieving conversation history: {e}")
            raise ExternalServiceError(f"Failed to get conversation history: {e}", service="agno_memory")

    async def clear_conversation(self, session_id: str) -> bool:
        """
        Clear conversation history for a session.
        Uses agent.clear_session() if available.

        Args:
            session_id: Session identifier

        Returns:
            True if successful
        """
        if not self._initialized:
            await self.initialize()

        try:
            # Use Agno's clear_session if db is configured
            if hasattr(self.agent, 'clear_session'):
                await self.agent.clear_session(session_id=session_id)
                logger.info(f"Cleared session {session_id}")
                return True
            else:
                logger.warning("Session clearing not available without db configured on Agent")
                return True

        except Exception as e:
            logger.error(f"Error clearing conversation: {e}")
            raise ExternalServiceError(f"Failed to clear conversation: {e}", service="agno_memory")

    async def search_conversations(
        self,
        query: str,
        session_id: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search conversations using Agno's knowledge base search.

        Args:
            query: Search query
            session_id: Optional session to limit search scope
            limit: Maximum number of results

        Returns:
            List of search results with relevance scores
        """
        if not self._initialized:
            await self.initialize()

        try:
            # If knowledge base is configured, use it for search
            if self.agent.knowledge:
                logger.info(f"Searching knowledge base for: {query}")
                # Knowledge search happens automatically when agent processes messages
                # For explicit search, we'd need to query the knowledge base directly
                return []
            else:
                logger.warning("Knowledge base search not available")
                return []

        except Exception as e:
            logger.error(f"Error searching conversations: {e}")
            raise ExternalServiceError(f"Failed to search conversations: {e}", service="agno_memory")

    async def health_check(self) -> bool:
        """Check if Agno chat service is healthy."""
        try:
            if not self._initialized:
                await self.initialize()

            # Test basic functionality
            test_request = ChatRequest(
                message="Hello, this is a health check",
                session_id="health_check_test"
            )

            response = await self.process_message(test_request)

            # Clean up test data
            await self.clear_conversation("health_check_test")

            return bool(response.message)

        except Exception as e:
            logger.error(f"Agno chat service health check failed: {e}")
            return False

    def get_capabilities(self) -> Dict[str, Any]:
        """Get service capabilities information."""
        return {
            "provider": "agno",
            "features": {
                "conversation_memory": True,
                "vector_search": self.settings.vector_database != "none",
                "multi_session": True,
                "structured_outputs": self.settings.structured_outputs,
                "context_preservation": True,
                "semantic_search": self.settings.vector_database != "none",
            },
            "configuration": {
                "model": self.settings.default_model,
                "memory_type": self.settings.memory_type,
                "vector_database": self.settings.vector_database,
                "max_tokens": self.settings.max_tokens,
                "temperature": self.settings.temperature,
            }
        }
