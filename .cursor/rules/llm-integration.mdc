---
description: "LLM and AI agent integration patterns and best practices"
---

# LLM & AI Integration Rules

Follow these patterns for LLM and AI agent integration:

## LLM Service Architecture
- **Abstraction Layer**: Use LLM service abstractions in [app/core/llm/](mdc:needleai/backend/app/core/llm/)
- **Multi-Provider Support**: Support OpenRouter, OpenAI, Anthropic via factory pattern
- **Error Handling**: Implement robust error handling for external API failures
- **Rate Limiting**: Implement rate limiting to respect provider limits

## Agno AI Agent Framework
When using Agno agents, follow these patterns:

### Agent Configuration
```python
from agno import Agent, AgentTeam
from app.core.memory import get_memory_store

# Single agent configuration
agent = Agent(
    model=settings.default_model,
    memory=get_memory_store(),
    instructions="You are a helpful assistant...",
    structured_outputs=settings.structured_outputs
)

# Team-based agents for complex workflows
team = AgentTeam(
    name="Customer Support Team",
    agents=[
        Agent(name="Analyst", model="gpt-4", instructions="Analyze customer issues"),
        Agent(name="Resolver", model="gpt-4-turbo", instructions="Provide solutions")
    ]
)
```

### Memory Management
- **Memory Types**: Support in-memory, Redis, and vector database memory
- **Memory Configuration**: Configure via [app/core/memory/](mdc:needleai/backend/app/core/memory/)
- **Persistence**: Use persistent memory for important conversations
- **Cleanup**: Implement memory cleanup for expired sessions

Example memory configuration:
```python
# app/core/memory/agno_memory.py
class AgnoMemoryManager:
    def __init__(self, settings: Settings):
        if settings.memory_type == "vector":
            self.memory = VectorMemory(
                collection_name=settings.vector_collection_name,
                embeddings_model=settings.embeddings_model
            )
        elif settings.memory_type == "redis":
            self.memory = RedisMemory(
                redis_url=settings.redis_url
            )
        else:
            self.memory = InMemory()
```

## Chat Service Patterns

### Service Factory
Use the chat service factory for flexible chat implementations:
```python
from app.services.chat_service_factory import ChatServiceFactory, ChatServiceType

# Auto-detection (tries Agno first, falls back to custom)
chat_service = await ChatServiceFactory.create_chat_service(
    settings=settings,
    service_type=ChatServiceType.AUTO
)

# Explicit Agno usage
chat_service = await ChatServiceFactory.create_chat_service(
    settings=settings,
    service_type=ChatServiceType.AGNO
)
```

### Custom Chat Service Implementation
For custom implementations without Agno:
```python
class CustomChatService:
    def __init__(self, llm_service, memory_store, settings):
        self.llm_service = llm_service
        self.memory_store = memory_store
        self.settings = settings

    async def process_message(self, message: str, session_id: str, user_id: str = None):
        # Get conversation context
        context = await self._get_conversation_context(session_id)

        # Generate response using LLM
        response = await self._generate_response(message, context)

        # Store conversation
        await self._store_conversation(session_id, message, response)

        return {
            "message": response["content"],
            "session_id": session_id,
            "message_id": generate_id(),
            "metadata": response.get("metadata", {})
        }
```

## Vector Database Integration
For memory and RAG (Retrieval-Augmented Generation):

### Supported Vector Databases
- **Pinecone**: Cloud-native vector database
- **Weaviate**: Open-source vector database
- **Qdrant**: High-performance vector database
- **ChromaDB**: Lightweight vector database

Example vector database setup:
```python
# For ChromaDB
from chromadb import Client
from chromadb.config import Settings as ChromaSettings

def create_chromadb_client(settings):
    return Client(ChromaSettings(
        persist_directory=settings.chromadb_path,
        anonymized_telemetry=False
    ))

# For Pinecone
import pinecone
from pinecone import Pinecone

def create_pinecone_client(settings):
    pc = Pinecone(api_key=settings.get_secret("pinecone_api_key"))
    return pc.Index(settings.pinecone_index_name)
```

## LLM Provider Configuration

### OpenRouter Integration
```python
# Use OpenRouter for access to multiple models
OPENROUTER_CONFIG = {
    "base_url": "https://openrouter.ai/api/v1",
    "api_key": settings.get_secret("openrouter_api_key"),
    "default_model": "anthropic/claude-3-sonnet:beta",  # Use Anthropic Sonnet 4
    "site_url": settings.site_url,  # For referrer tracking
    "app_name": settings.app_name
}
```

### Model Selection Guidelines
- **Fast Responses**: Use GPT-4.1 mini or nano for quick responses
- **Complex Reasoning**: Use GPT-4.1 or Anthropic Sonnet 4 for complex tasks
- **Code Generation**: Use specialized code models when available
- **Cost Optimization**: Balance model capability with cost requirements

## Error Handling & Resilience

### Retry Logic
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
async def call_llm_with_retry(prompt: str, model: str):
    try:
        response = await llm_client.generate_completion(
            messages=[{"role": "user", "content": prompt}],
            model=model
        )
        return response
    except Exception as e:
        logger.warning(f"LLM call failed: {e}")
        raise
```

### Fallback Strategies
- **Model Fallback**: Try cheaper/faster models if primary fails
- **Provider Fallback**: Switch providers on failures
- **Cache Fallback**: Use cached responses when available
- **Graceful Degradation**: Provide meaningful error messages to users

## Prompt Engineering

### Prompt Templates
```python
SYSTEM_PROMPTS = {
    "helpful_assistant": """You are a helpful, harmless, and honest AI assistant.
    Provide accurate and helpful responses while being concise and clear.""",

    "code_assistant": """You are an expert software developer.
    Provide high-quality code solutions with explanations.
    Follow best practices and include error handling.""",

    "customer_support": """You are a customer support agent.
    Be empathetic, professional, and solution-oriented.
    Escalate complex issues when necessary."""
}
```

### Context Management
- **Context Limits**: Respect model context window limits
- **Context Compression**: Summarize older messages when needed
- **Relevance Filtering**: Include only relevant conversation history
- **Metadata Preservation**: Maintain important conversation metadata

## Security & Privacy

### Data Handling
- **Data Minimization**: Only send necessary data to LLM providers
- **PII Scrubbing**: Remove or mask personally identifiable information
- **Input Sanitization**: Clean user inputs before sending to LLMs
- **Output Filtering**: Filter potentially harmful LLM responses

### API Key Management
- **Secret Storage**: Store API keys in secure secret management
- **Rotation**: Implement API key rotation procedures
- **Monitoring**: Monitor API usage and costs
- **Rate Limiting**: Implement usage limits per user/session

## Monitoring & Observability

### LLM Metrics
- **Response Times**: Track latency for different models
- **Token Usage**: Monitor input/output token consumption
- **Success Rates**: Track API success/failure rates
- **Cost Tracking**: Monitor costs per request and per user

### Logging
```python
logger.info(
    "LLM request completed",
    extra={
        "model": model_name,
        "tokens_used": response["usage"]["total_tokens"],
        "response_time": response_time,
        "user_id": user_id,
        "session_id": session_id
    }
)
```

## Testing LLM Integration

### Mock LLM Services
```python
class MockLLMService:
    def __init__(self, responses: List[str] = None):
        self.responses = responses or ["Mock response"]
        self.call_count = 0

    async def generate_completion(self, messages: list, **kwargs):
        response = self.responses[self.call_count % len(self.responses)]
        self.call_count += 1

        return {
            "choices": [{
                "message": {"role": "assistant", "content": response},
                "finish_reason": "stop"
            }],
            "usage": {"total_tokens": 100}
        }
```

### Integration Testing
- **Mock External APIs**: Never call real LLM APIs in tests
- **Response Validation**: Test response format validation
- **Error Scenarios**: Test various API failure scenarios
- **Performance Testing**: Test with realistic token loads
