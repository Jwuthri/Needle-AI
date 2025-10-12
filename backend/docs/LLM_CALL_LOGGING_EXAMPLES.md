# LLM Call Logging - Complete Examples

## Schema Overview

```python
{
    # Identification
    "id": "uuid",
    "call_type": "CHAT | RAG_QUERY | SENTIMENT_ANALYSIS | ...",
    "status": "SUCCESS | ERROR | ...",
    
    # Provider
    "provider": "openrouter",
    "model": "gpt-4",
    
    # Request (matches LLM API format)
    "system_prompt": "You are a helpful assistant",  # Optional
    "messages": [
        {"role": "user", "content": "Hello!"},
        {"role": "assistant", "content": "Hi there!", "tool_calls": [...]}  # Previous turns
    ],
    "tools": [...]  # Tool definitions (optional)
    "tool_choice": "auto",  # Optional
    
    # Response (matches LLM API format)
    "response_message": {
        "role": "assistant",
        "content": "How can I help?",
        "tool_calls": [...]  # Optional
    },
    "finish_reason": "stop",
    
    # Metrics
    "prompt_tokens": 10,
    "completion_tokens": 5,
    "total_tokens": 15,
    "estimated_cost": 0.00045,
    "latency_ms": 1234
}
```

## Example 1: Simple Chat Message

```python
from app.services.llm_logger import LLMLogger
from app.database.models.llm_call import LLMCallTypeEnum

# Log a simple chat interaction
async with LLMLogger.log_call(
    call_type=LLMCallTypeEnum.CHAT,
    provider="openrouter",
    model="gpt-4",
    messages=[
        {"role": "user", "content": "What are the main product gaps for Gorgias?"}
    ],
    system_prompt="You are a product analysis AI assistant.",
    user_id=user_id,
    session_id=session_id
) as log_id:
    # Make LLM call
    response = await llm_client.chat(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a product analysis AI assistant."},
            {"role": "user", "content": "What are the main product gaps for Gorgias?"}
        ]
    )
    
    # Log completion
    await LLMLogger.complete(
        log_id,
        response_message={
            "role": "assistant",
            "content": response.choices[0].message.content
        },
        tokens={
            'prompt_tokens': response.usage.prompt_tokens,
            'completion_tokens': response.usage.completion_tokens,
            'total_tokens': response.usage.total_tokens
        },
        estimated_cost=response.usage.total_tokens * 0.00003,
        finish_reason=response.choices[0].finish_reason
    )
```

## Example 2: Multi-turn Conversation

```python
# Log a conversation with context
messages = [
    {"role": "user", "content": "What is Gorgias?"},
    {"role": "assistant", "content": "Gorgias is a customer support platform."},
    {"role": "user", "content": "What are its main features?"}
]

log_id = await LLMLogger.start(
    call_type=LLMCallTypeEnum.CHAT,
    provider="openrouter",
    model="gpt-4",
    messages=messages,  # Full conversation history
    system_prompt="You are a product expert.",
    user_id=user_id,
    session_id=session_id,
    temperature=0.7,
    max_tokens=500
)

try:
    response = await llm_client.chat(model="gpt-4", messages=messages)
    
    await LLMLogger.complete(
        log_id,
        response_message={
            "role": "assistant",
            "content": response.choices[0].message.content
        },
        tokens=response.usage.__dict__,
        finish_reason=response.choices[0].finish_reason
    )
except Exception as e:
    await LLMLogger.fail(log_id, str(e))
    raise
```

## Example 3: Function/Tool Calling

```python
# Define tools
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_competitor_data",
            "description": "Get competitor analysis data",
            "parameters": {
                "type": "object",
                "properties": {
                    "company_name": {"type": "string"},
                    "competitors": {"type": "array", "items": {"type": "string"}}
                }
            }
        }
    }
]

# Log with tools
log_id = await LLMLogger.start(
    call_type=LLMCallTypeEnum.RAG_QUERY,
    provider="openrouter",
    model="gpt-4",
    messages=[
        {"role": "user", "content": "Compare Gorgias with its top competitors"}
    ],
    system_prompt="You are a competitive analysis AI.",
    tools=tools,
    tool_choice="auto",
    company_id=company_id
)

response = await llm_client.chat(
    model="gpt-4",
    messages=[...],
    tools=tools,
    tool_choice="auto"
)

# Response includes tool calls
response_msg = response.choices[0].message
await LLMLogger.complete(
    log_id,
    response_message={
        "role": "assistant",
        "content": response_msg.content,
        "tool_calls": [
            {
                "id": "call_abc123",
                "type": "function",
                "function": {
                    "name": "get_competitor_data",
                    "arguments": '{"company_name": "Gorgias", "competitors": ["Zendesk", "Freshdesk"]}'
                }
            }
        ] if response_msg.tool_calls else None
    },
    tokens=response.usage.__dict__,
    finish_reason=response.choices[0].finish_reason  # "tool_calls"
)
```

## Example 4: Tool Response Logging

```python
# After tool execution, log the follow-up call
previous_messages = [
    {"role": "user", "content": "Compare Gorgias with competitors"},
    {
        "role": "assistant",
        "content": None,
        "tool_calls": [{
            "id": "call_abc123",
            "type": "function",
            "function": {
                "name": "get_competitor_data",
                "arguments": '{"company_name": "Gorgias", ...}'
            }
        }]
    },
    {
        "role": "tool",
        "tool_call_id": "call_abc123",
        "name": "get_competitor_data",
        "content": '{"competitors": [{"name": "Zendesk", "features": [...]}]}'
    }
]

# Log the synthesis call
log_id = await LLMLogger.start(
    call_type=LLMCallTypeEnum.RAG_SYNTHESIS,
    provider="openrouter",
    model="gpt-4",
    messages=previous_messages,
    system_prompt="Synthesize competitor analysis.",
    company_id=company_id,
    parent_call_id=original_call_log_id  # Link to parent
)

response = await llm_client.chat(model="gpt-4", messages=previous_messages)

await LLMLogger.complete(
    log_id,
    response_message={
        "role": "assistant",
        "content": response.choices[0].message.content
    },
    tokens=response.usage.__dict__,
    finish_reason="stop"
)
```

## Example 5: Hidden RAG Query

```python
# Hidden call for RAG retrieval (not shown to user)
log_id = await LLMLogger.start(
    call_type=LLMCallTypeEnum.RAG_QUERY,
    provider="openrouter",
    model="gpt-3.5-turbo",
    messages=[
        {"role": "user", "content": f"Extract key themes from these reviews: {reviews_text}"}
    ],
    system_prompt="You are a text analysis AI. Extract key themes briefly.",
    company_id=company_id,
    trace_id=request_trace_id,
    tags=["hidden", "rag", "preprocessing"],
    temperature=0.0,
    max_tokens=200
)

themes = await extract_themes(reviews_text)

await LLMLogger.complete(
    log_id,
    response_message={
        "role": "assistant",
        "content": str(themes)
    },
    tokens={'total_tokens': 250},
    estimated_cost=0.0005
)
```

## Example 6: Sentiment Analysis Task

```python
from app.services.llm_logger import log_sentiment_analysis

# Celery task for sentiment analysis
@celery_app.task
async def analyze_review_sentiment(review_id: str):
    review = await get_review(review_id)
    
    log_id = await log_sentiment_analysis(
        text=review.content,
        model="gpt-3.5-turbo",
        review_id=review_id,
        provider="openrouter",
        task_id=analyze_review_sentiment.request.id
    )
    
    try:
        result = await llm_client.chat(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "Analyze sentiment. Respond with: positive, negative, or neutral."
                },
                {
                    "role": "user",
                    "content": review.content
                }
            ]
        )
        
        sentiment = result.choices[0].message.content.strip().lower()
        
        await LLMLogger.complete(
            log_id,
            response_message={
                "role": "assistant",
                "content": sentiment
            },
            tokens=result.usage.__dict__,
            estimated_cost=result.usage.total_tokens * 0.000001
        )
        
        return sentiment
    except Exception as e:
        await LLMLogger.fail(log_id, str(e))
        raise
```

## Example 7: Full RAG Pipeline with Tracing

```python
import uuid

async def rag_pipeline(user_question: str, company_id: str, user_id: str):
    trace_id = str(uuid.uuid4())
    
    # Step 1: Query understanding
    step1_log = await LLMLogger.start(
        call_type=LLMCallTypeEnum.RAG_QUERY,
        provider="openrouter",
        model="gpt-3.5-turbo",
        messages=[
            {"role": "user", "content": f"Classify this question: {user_question}"}
        ],
        system_prompt="Classify into: product_gap, competitor, feature, support",
        trace_id=trace_id,
        company_id=company_id,
        tags=["rag", "classification"]
    )
    
    query_type = await classify_query(user_question)
    await LLMLogger.complete(step1_log, response_message={"role": "assistant", "content": query_type})
    
    # Step 2: Retrieve relevant reviews (no LLM call, but could add embedding call logging)
    relevant_reviews = await vector_db.search(user_question, company_id=company_id)
    
    # Step 3: Generate answer
    context = "\n".join([r.content for r in relevant_reviews])
    step3_log = await LLMLogger.start(
        call_type=LLMCallTypeEnum.RAG_SYNTHESIS,
        provider="openrouter",
        model="gpt-4",
        messages=[
            {
                "role": "user",
                "content": f"Question: {user_question}\n\nContext:\n{context}\n\nAnswer:"
            }
        ],
        system_prompt="You are a product analyst. Answer based on the provided reviews.",
        trace_id=trace_id,
        user_id=user_id,
        company_id=company_id,
        parent_call_id=step1_log,  # Link to parent
        metadata={
            "review_count": len(relevant_reviews),
            "query_type": query_type
        }
    )
    
    response = await llm_client.chat(...)
    
    await LLMLogger.complete(
        step3_log,
        response_message={
            "role": "assistant",
            "content": response.choices[0].message.content
        },
        tokens=response.usage.__dict__
    )
    
    return response.choices[0].message.content


# Later: Debug the entire pipeline
async with get_async_session() as db:
    all_calls = await LLMCallRepository.get_calls_by_trace(db, trace_id)
    for call in all_calls:
        print(f"{call.call_type.value}: {call.messages[-1]['content'][:50]}")
        print(f"  Response: {call.response_message['content'][:50] if call.response_message else 'N/A'}")
        print(f"  Latency: {call.latency_ms}ms, Cost: ${call.estimated_cost}")
```

## Example 8: Querying Logs

### Get all calls for a user session

```python
from app.database.repositories.llm_call import LLMCallRepository

async with get_async_session() as db:
    calls = await LLMCallRepository.list_by_filters(
        db,
        session_id=session_id,
        limit=50
    )
    
    for call in calls:
        # Get last user message
        user_msg = next((m for m in reversed(call.messages) if m['role'] == 'user'), None)
        print(f"User: {user_msg['content'] if user_msg else 'N/A'}")
        
        # Get assistant response
        if call.response_message:
            print(f"Assistant: {call.response_message['content']}")
            if call.response_message.get('tool_calls'):
                print(f"  Tool calls: {len(call.response_message['tool_calls'])}")
```

### Find failed RAG queries

```python
failed_rag = await LLMCallRepository.list_by_filters(
    db,
    call_type=LLMCallTypeEnum.RAG_QUERY,
    status=LLMCallStatusEnum.ERROR,
    company_id=company_id,
    start_date=datetime.now() - timedelta(days=7)
)

for call in failed_rag:
    print(f"Failed at: {call.created_at}")
    print(f"Messages: {call.messages}")
    print(f"Error: {call.error_message}")
```

### Analyze tool usage

```python
# Find all calls with tool usage
calls = await LLMCallRepository.list_by_filters(db, limit=1000)

tool_usage = {}
for call in calls:
    if call.response_message and call.response_message.get('tool_calls'):
        for tool_call in call.response_message['tool_calls']:
            tool_name = tool_call['function']['name']
            tool_usage[tool_name] = tool_usage.get(tool_name, 0) + 1

print("Tool usage:", tool_usage)
```

## Summary

✅ **Messages Array** - Store full conversation history
✅ **System Prompt** - Separate field for clarity
✅ **Tools** - Log tool definitions and calls
✅ **Response Message** - Full LLM response with tool_calls
✅ **Finish Reason** - Know why completion stopped
✅ **Trace IDs** - Debug multi-step pipelines
✅ **Parent Calls** - Link nested calls

**Now your logs match exactly what you send/receive from LLM APIs! 🎯**

