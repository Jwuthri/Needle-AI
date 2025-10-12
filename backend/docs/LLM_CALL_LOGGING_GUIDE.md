# LLM Call Logging Guide

## Overview

The `llm_calls` table logs **ALL** LLM API calls made by your application, including:
- ✅ User-visible chat messages
- ✅ Hidden RAG queries for retrieval
- ✅ Background sentiment analysis
- ✅ Review summarization tasks
- ✅ Embedding generation
- ✅ Any internal LLM calls

This is **essential** for:
- **Debugging** - Trace issues in RAG pipelines
- **Cost tracking** - Monitor LLM spend per user/company
- **Performance monitoring** - Track response times
- **Audit trails** - Compliance and security
- **Finding bugs** - Reproduce production issues

## Table Structure

```python
class LLMCall:
    # Identification
    id: str                    # Unique call ID
    call_type: LLMCallTypeEnum  # CHAT, RAG_QUERY, SENTIMENT_ANALYSIS, etc.
    status: LLMCallStatusEnum   # PENDING, SUCCESS, ERROR, etc.
    
    # Provider info
    provider: str              # openrouter, openai, anthropic
    model: str                 # gpt-4, claude-3, etc.
    
    # Request
    prompt: str                # The actual prompt
    system_prompt: str         # System prompt if used
    temperature: float
    max_tokens: int
    
    # Response
    response: str              # The actual response
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost: float      # In USD
    
    # Performance
    latency_ms: int            # Response time
    started_at: datetime
    completed_at: datetime
    
    # Context (for tracing)
    user_id: str               # If user-initiated
    session_id: str            # Chat session
    task_id: str               # Celery task
    company_id: str            # Related company
    review_id: str             # Related review
    trace_id: str              # Distributed tracing
    parent_call_id: str        # Parent call if nested
    
    # Metadata
    metadata: dict             # Additional context
    tags: list                 # Tags for filtering
```

## Usage Examples

### Example 1: Simple Logging (Context Manager)

```python
from app.services.llm_logger import LLMLogger
from app.database.models.llm_call import LLMCallTypeEnum

# Wrap your LLM call
async with LLMLogger.log_call(
    call_type=LLMCallTypeEnum.CHAT,
    provider="openrouter",
    model="gpt-4",
    prompt="What are the main product gaps?",
    user_id=user_id,
    session_id=session_id
) as log_id:
    # Make your LLM call
    response = await llm_client.generate(
        prompt="What are the main product gaps?",
        model="gpt-4"
    )
    
    # Log completion (automatic timing!)
    await LLMLogger.complete(
        log_id,
        response=response.text,
        tokens={
            'prompt_tokens': response.usage.prompt_tokens,
            'completion_tokens': response.usage.completion_tokens,
            'total_tokens': response.usage.total_tokens
        },
        estimated_cost=response.usage.total_tokens * 0.00003  # Example
    )
```

### Example 2: Hidden RAG Query

```python
from app.services.llm_logger import LLMLogger, log_rag_query

# Log a hidden RAG retrieval query
log_id = await log_rag_query(
    prompt="Extract key product issues from: ...",
    model="gpt-3.5-turbo",
    company_id=company_id,
    trace_id=request_trace_id,
    tags=["rag", "retrieval", "production"]
)

try:
    # Make the hidden LLM call
    issues = await extract_product_issues(reviews)
    
    # Mark as completed
    await LLMLogger.complete(
        log_id,
        response=str(issues),
        tokens={'total_tokens': 500},
        estimated_cost=0.001
    )
except Exception as e:
    # Log the error
    await LLMLogger.fail(log_id, str(e))
    raise
```

### Example 3: Sentiment Analysis Task

```python
from app.database.models.llm_call import LLMCallTypeEnum

# Log sentiment analysis in background task
async def analyze_sentiment_task(review_id: str):
    review = await get_review(review_id)
    
    log_id = await LLMLogger.start(
        call_type=LLMCallTypeEnum.SENTIMENT_ANALYSIS,
        provider="openrouter",
        model="gpt-3.5-turbo",
        prompt=f"Analyze sentiment: {review.content[:200]}",
        review_id=review_id,
        task_id=current_task.request.id,
        tags=["sentiment", "background"]
    )
    
    try:
        result = await llm_client.analyze_sentiment(review.content)
        
        await LLMLogger.complete(
            log_id,
            response=result.sentiment,
            tokens=result.usage,
            estimated_cost=result.cost
        )
        
        return result
    except Exception as e:
        await LLMLogger.fail(log_id, str(e))
        raise
```

### Example 4: Multi-Step RAG Pipeline

```python
# Log parent call
parent_log_id = await LLMLogger.start(
    call_type=LLMCallTypeEnum.RAG_SYNTHESIS,
    provider="openrouter",
    model="gpt-4",
    prompt="Synthesize answer from reviews",
    user_id=user_id,
    company_id=company_id,
    trace_id=trace_id
)

# Step 1: Query understanding (child call)
understanding_log_id = await LLMLogger.start(
    call_type=LLMCallTypeEnum.RAG_QUERY,
    provider="openrouter",
    model="gpt-3.5-turbo",
    prompt="Classify query intent",
    parent_call_id=parent_log_id,  # Link to parent
    trace_id=trace_id
)
query_intent = await classify_query(user_question)
await LLMLogger.complete(understanding_log_id, response=query_intent)

# Step 2: Retrieval (child call)
retrieval_log_id = await LLMLogger.start(
    call_type=LLMCallTypeEnum.RAG_QUERY,
    provider="openrouter",
    model="gpt-3.5-turbo",
    prompt="Generate retrieval query",
    parent_call_id=parent_log_id,
    trace_id=trace_id
)
relevant_reviews = await retrieve_reviews(query_intent)
await LLMLogger.complete(retrieval_log_id, response=str(relevant_reviews[:5]))

# Step 3: Final synthesis (parent completes)
final_response = await synthesize_answer(user_question, relevant_reviews)
await LLMLogger.complete(parent_log_id, response=final_response)
```

## Querying Logs

### Get Cost Statistics

```python
from app.services.llm_logger import LLMLogger

# Get costs for a user
stats = await LLMLogger.get_cost_stats(user_id="user_123", days=30)
print(f"Total cost: ${stats['total_cost']}")
print(f"Total calls: {stats['total_calls']}")
print(f"By type: {stats['by_call_type']}")
print(f"By model: {stats['by_model']}")
```

### Get Performance Stats

```python
# Get performance metrics
perf = await LLMLogger.get_performance_stats(
    provider="openrouter",
    model="gpt-4",
    days=7
)
print(f"Average latency: {perf['avg_latency_ms']}ms")
print(f"P95 latency: {perf['p95_latency_ms']}ms")
```

### Debug a Trace

```python
from app.database.repositories.llm_call import LLMCallRepository

# Get all calls for a trace (to debug issues)
async with get_async_session() as db:
    calls = await LLMCallRepository.get_calls_by_trace(db, trace_id)
    
    for call in calls:
        print(f"{call.call_type.value}: {call.model}")
        print(f"  Status: {call.status.value}")
        print(f"  Latency: {call.latency_ms}ms")
        print(f"  Cost: ${call.estimated_cost}")
        if call.error_message:
            print(f"  ERROR: {call.error_message}")
```

### Filter by Multiple Criteria

```python
from app.database.models.llm_call import LLMCallTypeEnum, LLMCallStatusEnum

async with get_async_session() as db:
    # Find all failed RAG queries for a company
    failed_rag = await LLMCallRepository.list_by_filters(
        db,
        call_type=LLMCallTypeEnum.RAG_QUERY,
        status=LLMCallStatusEnum.ERROR,
        company_id="comp_123",
        start_date=datetime.now() - timedelta(days=7),
        limit=50
    )
    
    for call in failed_rag:
        print(f"Failed at: {call.created_at}")
        print(f"Error: {call.error_message}")
        print(f"Prompt preview: {call.prompt[:100]}")
```

## Database Migration

Run the migration to create the table:

```bash
# Create the llm_calls table
alembic upgrade head
```

## Cleanup

Old logs can be cleaned up (but keep them for analysis!):

```python
from app.database.repositories.llm_call import LLMCallRepository

async with get_async_session() as db:
    # Clean up logs older than 90 days
    deleted = await LLMCallRepository.cleanup_old_logs(db, days_old=90)
    await db.commit()
    print(f"Cleaned up {deleted} old logs")
```

## Call Types

```python
class LLMCallTypeEnum:
    CHAT = "chat"                       # User-visible chat
    RAG_QUERY = "rag_query"             # Hidden RAG query
    RAG_SYNTHESIS = "rag_synthesis"     # Final answer synthesis
    SENTIMENT_ANALYSIS = "sentiment_analysis"
    SUMMARIZATION = "summarization"
    EMBEDDING = "embedding"             # Text embeddings
    CLASSIFICATION = "classification"   # Text classification
    EXTRACTION = "extraction"           # Info extraction
    SYSTEM = "system"                   # System calls
    OTHER = "other"
```

## Best Practices

### 1. Always Log Hidden Calls

```python
# ❌ BAD: No logging
sentiment = await llm.analyze_sentiment(review.content)

# ✅ GOOD: Log the hidden call
log_id = await LLMLogger.start(...)
sentiment = await llm.analyze_sentiment(review.content)
await LLMLogger.complete(log_id, response=sentiment)
```

### 2. Use Trace IDs for Request Tracking

```python
# Generate a trace ID per user request
trace_id = str(uuid.uuid4())

# Pass it to all related LLM calls
await LLMLogger.start(..., trace_id=trace_id)

# Later: debug the entire request flow
calls = await LLMCallRepository.get_calls_by_trace(db, trace_id)
```

### 3. Tag Production Calls

```python
# Tag calls for easier filtering
await LLMLogger.start(
    ...,
    tags=["production", "rag", "high-priority"]
)

# Later: filter by tags
metadata={'environment': 'production'}
```

### 4. Track Costs Accurately

```python
# Calculate cost based on model pricing
cost = (prompt_tokens * model.prompt_price + 
        completion_tokens * model.completion_price)

await LLMLogger.complete(log_id, estimated_cost=cost)
```

## Integration with Existing Code

### Chat Service

```python
# In your chat service
async def process_message(self, message: str, session_id: str):
    log_id = await LLMLogger.start(
        call_type=LLMCallTypeEnum.CHAT,
        provider=self.provider,
        model=self.model,
        prompt=message,
        user_id=self.user_id,
        session_id=session_id
    )
    
    try:
        response = await self.llm_client.chat(message)
        await LLMLogger.complete(log_id, response=response.text)
        return response
    except Exception as e:
        await LLMLogger.fail(log_id, str(e))
        raise
```

### RAG Service

```python
# In your RAG service
async def process_with_rag(self, query: str, company_ids: List[str]):
    trace_id = str(uuid.uuid4())
    
    # Log all sub-calls with same trace_id
    # ... (see Example 4 above)
```

## Monitoring Dashboard Ideas

With this data, you can build dashboards showing:

1. **Cost Over Time** - Daily/weekly/monthly LLM costs
2. **Usage by User** - Top users by cost/calls
3. **Performance** - Latency percentiles by model
4. **Error Rates** - Failed calls by type/model
5. **RAG Pipeline Health** - Success rate of RAG queries
6. **Model Comparison** - Compare costs/performance across models

## Summary

✅ **Log ALL LLM calls** - Visible and hidden
✅ **Use context manager** - Automatic timing
✅ **Track costs** - Monitor spending
✅ **Use trace IDs** - Debug complex flows
✅ **Tag appropriately** - Easy filtering
✅ **Monitor performance** - Track latencies
✅ **Keep for analysis** - Don't delete too soon!

**Now you'll never lose track of any LLM call again! 🚀**

