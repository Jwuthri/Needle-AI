"""
Agno-based Chat Service - Complete integration with Agno framework.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    from agno import Agent, Memory
    from agno.memory import ChatMemory, HybridMemory, VectorMemory
    from agno.vector_db import ChromaDB, Pinecone, Qdrant, Weaviate
    AGNO_AVAILABLE = True
except ImportError:
    AGNO_AVAILABLE = False

from app.exceptions import ConfigurationError, ExternalServiceError
from app.models.chat import ChatRequest, ChatResponse, Message
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
        if not AGNO_AVAILABLE:
            raise ConfigurationError("Agno package not installed. Install with: pip install agno")

        self.settings = settings
        self.agent: Optional[Agent] = None
        self._initialized = False

    async def initialize(self):
        """Initialize the Agno agent with proper configuration."""
        if self._initialized:
            return

        try:
            # Create memory based on configuration
            memory = await self._create_memory()

            # Create agent with full configuration
            self.agent = Agent(
                # Model configuration
                model=self.settings.default_model,
                provider="openrouter" if self.settings.llm_provider == "openrouter" else "openai",
                api_key=self._get_api_key(),

                # Memory configuration
                memory=memory,

                # Agent configuration
                instructions=self.settings.agent_instructions or self._get_default_instructions(),
                structured_outputs=self.settings.structured_outputs,

                # Advanced features
                debug=self.settings.debug,
                show_tool_calls=self.settings.debug,

                # Performance settings
                max_retries=3,
                temperature=self.settings.temperature,
                max_tokens=self.settings.max_tokens,
            )

            self._initialized = True
            logger.info("Agno chat service initialized successfully")

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

    async def _create_memory(self) -> Memory:
        """Create Agno memory based on configuration."""
        vector_db = self.settings.vector_database.lower()
        memory_type = self.settings.memory_type.lower()

        # Vector database configuration
        vector_store = None

        if vector_db == "pinecone":
            vector_store = Pinecone(
                api_key=self.settings.get_secret("pinecone_api_key"),
                environment=self.settings.pinecone_environment,
                index_name=self.settings.pinecone_index_name
            )
        elif vector_db == "weaviate":
            vector_store = Weaviate(
                url=self.settings.weaviate_url,
                api_key=self.settings.get_secret("weaviate_api_key"),
                openai_api_key=self.settings.get_secret("weaviate_openai_api_key")
            )
        elif vector_db == "qdrant":
            vector_store = Qdrant(
                url=self.settings.qdrant_url,
                api_key=self.settings.get_secret("qdrant_api_key"),
                collection_name=self.settings.qdrant_collection_name
            )
        elif vector_db == "chromadb":
            vector_store = ChromaDB(
                path=self.settings.chromadb_path,
                collection_name=self.settings.chromadb_collection_name
            )

        # Memory type configuration
        if memory_type == "vector" and vector_store:
            return VectorMemory(vector_db=vector_store)
        elif memory_type == "hybrid" and vector_store:
            return HybridMemory(
                chat_memory=ChatMemory(),
                vector_memory=VectorMemory(vector_db=vector_store)
            )
        else:
            # Default to chat memory
            return ChatMemory()

    def _get_api_key(self) -> str:
        """Get the appropriate API key based on provider."""
        if self.settings.llm_provider == "openrouter":
            api_key = self.settings.get_secret("openrouter_api_key")
            if not api_key:
                raise ConfigurationError("OpenRouter API key not configured")
            return api_key
        else:
            # Default to OpenAI
            api_key = self.settings.get_secret("openai_api_key")
            if not api_key:
                raise ConfigurationError("OpenAI API key not configured")
            return api_key

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

            # Add user context if available
            context = {}
            if user_id:
                context["user_id"] = user_id
            if request.metadata:
                context.update(request.metadata)

            # Process message with Agno
            # Agno handles conversation history and memory automatically
            response = await self.agent.run(
                message=request.message,
                session_id=session_id,
                context=context
            )

            # Extract response content
            if isinstance(response, str):
                response_content = response
            elif hasattr(response, 'content'):
                response_content = response.content
            elif isinstance(response, dict):
                response_content = response.get('content', str(response))
            else:
                response_content = str(response)

            # Create response
            chat_response = ChatResponse(
                message=response_content,
                session_id=session_id,
                metadata={
                    "model": self.settings.default_model,
                    "provider": "agno",
                    "timestamp": datetime.utcnow().isoformat(),
                    "user_id": user_id,
                    **context
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
    ) -> List[Message]:
        """
        Get conversation history using Agno's memory system.

        Args:
            session_id: Session identifier
            limit: Maximum number of messages to retrieve

        Returns:
            List of conversation messages
        """
        if not self._initialized:
            await self.initialize()

        try:
            # Get messages from Agno's memory
            messages = await self.agent.memory.get_messages(
                session_id=session_id,
                limit=limit or 50
            )

            # Convert to our Message format
            conversation_messages = []
            for msg in messages:
                message = Message(
                    role=msg.get("role", "unknown"),
                    content=msg.get("content", ""),
                    timestamp=msg.get("timestamp"),
                    metadata=msg.get("metadata", {})
                )
                conversation_messages.append(message)

            return conversation_messages

        except Exception as e:
            logger.error(f"Error retrieving conversation history: {e}")
            raise ExternalServiceError(f"Failed to get conversation history: {e}", service="agno_memory")

    async def clear_conversation(self, session_id: str) -> bool:
        """
        Clear conversation history for a session.

        Args:
            session_id: Session identifier

        Returns:
            True if successful
        """
        if not self._initialized:
            await self.initialize()

        try:
            await self.agent.memory.clear_session(session_id)
            logger.info(f"Cleared conversation for session {session_id}")
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
        Search conversations using Agno's semantic search.

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
            # Use Agno's search capability if available
            if hasattr(self.agent.memory, 'search'):
                results = await self.agent.memory.search(
                    query=query,
                    session_id=session_id,
                    limit=limit
                )

                search_results = []
                for result in results:
                    search_result = {
                        "content": result.get("content", ""),
                        "score": result.get("score", 0.0),
                        "session_id": result.get("session_id"),
                        "timestamp": result.get("timestamp"),
                        "metadata": result.get("metadata", {})
                    }
                    search_results.append(search_result)

                return search_results
            else:
                # Fallback to simple message retrieval
                messages = await self.get_conversation_history(session_id or "default", limit)
                return [
                    {
                        "content": msg.content,
                        "score": 1.0,
                        "session_id": session_id,
                        "timestamp": msg.timestamp,
                        "metadata": msg.metadata or {}
                    }
                    for msg in messages
                    if query.lower() in msg.content.lower()
                ]

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
