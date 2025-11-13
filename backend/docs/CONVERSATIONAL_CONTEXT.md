# Conversational Context Integration

## Overview

The Product Review Analysis Workflow now supports conversational context persistence and follow-up query handling. This enables multi-turn conversations where users can reference previous results and the system can reuse cached data for efficiency.

## Architecture

### Components

1. **ConversationalContextManager** (`app/core/llm/workflow/context_manager.py`)
   - Manages context persistence to Redis
   - Detects follow-up queries
   - Provides context-aware planning hints

2. **ProductReviewAnalysisWorkflow** (`app/optimal_workflow/product_review_workflow.py`)
   - Loads previous context at workflow start
   - Saves context after workflow completion
   - Integrates follow-up detection into coordinator step
   - Provides planning hints to planner agent

3. **Redis Storage**
   - Stores conversation history (up to 10 turns)
   - Caches insights and agent outputs
   - TTL: 24 hours

## Features

### 1. Context Persistence

After each workflow execution, the system saves:
- Original query
- Generated insights from all agents
- Agent outputs for potential reuse
- Execution metadata (timestamps, step counts)

```python
# Saved context structure
{
    "session_id": "session_123",
    "history": [
        {
            "query": "What are the main product gaps?",
            "insights": [...],
            "agent_outputs": {...},
            "metadata": {...},
            "timestamp": "2025-11-12T10:30:00Z"
        }
    ],
    "last_updated": "2025-11-12T10:30:00Z"
}
```

### 2. Follow-up Query Detection

The system uses multiple strategies to detect follow-up queries:

**Keyword Detection:**
- "that", "the biggest", "compare", "show me more"
- "what about", "how about", "also"
- "those", "these", "them"

**Pronoun Detection:**
- Queries starting with "it", "they", "them", "those", "these", "that"

**Short Query Detection:**
- Queries with < 5 words are likely follow-ups

**Example Follow-ups:**
```
Initial: "What are the main product gaps?"
Follow-up 1: "Show me the reviews for the biggest gap"
Follow-up 2: "Compare that to last month"
Follow-up 3: "What about positive feedback?"
```

### 3. Context-Aware Planning

When a follow-up query is detected, the planner receives:

```python
{
    "previous_queries": ["What are the main product gaps?"],
    "available_insights": [...],  # Insights from previous turns
    "cached_data": {...},  # Reusable data
    "suggested_shortcuts": [
        "reuse_top_insight",
        "reuse_previous_data",
        "expand_previous_insight"
    ],
    "last_visualization": {...}  # For "show me more" queries
}
```

This enables the planner to:
- Reuse cached results instead of re-fetching data
- Generate simpler execution plans
- Reference previous insights directly

## Implementation Details

### Workflow Integration

**Step 1: Load Context (start_workflow)**
```python
# Initialize Redis client
redis_client = RedisClient()
await redis_client.connect()

# Initialize context manager
context_manager = ConversationalContextManager(redis_client=redis_client)

# Load previous context
previous_context = await context_manager.load_context(session_id)

if previous_context:
    # Merge cached results
    execution_context["cached_results"] = previous_context.cached_results
    execution_context["previous_insights"] = previous_context.insights
```

**Step 2: Detect Follow-ups (coordinator_step)**
```python
# Check if this is a follow-up query
is_follow_up = await context_manager.is_follow_up_query(
    query=query,
    previous_context=previous_context
)

# Add to classification
classification["is_follow_up"] = is_follow_up
```

**Step 3: Context-Aware Planning (iterative_planning_loop)**
```python
# Get planning hints for follow-up queries
if is_follow_up:
    planning_context = await context_manager.get_context_for_planning(
        session_id=session_id,
        current_query=query
    )
    execution_context["planning_hints"] = planning_context
```

**Step 4: Save Context (synthesis_step)**
```python
# Save execution results for future reference
await context_manager.save_context(
    session_id=session_id,
    query=query,
    insights=insights,
    agent_outputs=agent_outputs,
    metadata=metadata
)
```

## Configuration

### Redis Settings

The context manager uses the Redis client configured in `app/services/redis_client.py`:

```python
# Environment variables
REDIS_URL=rediss://user:password@host:port/db

# Context TTL (default: 24 hours)
context_ttl = 86400
```

### History Limits

- Maximum conversation turns stored: 10
- Oldest turns are automatically removed when limit is reached
- Each turn includes: query, insights, agent outputs, metadata

## Error Handling

The system gracefully handles Redis unavailability:

```python
try:
    # Load/save context
    context = await context_manager.load_context(session_id)
except Exception as e:
    logger.warning(f"Could not load context: {e}")
    # Continue without previous context
```

If Redis is unavailable:
- Workflow continues without context persistence
- Follow-up detection is disabled
- Each query is treated as independent

## Testing

Comprehensive tests are available in `backend/tests/unit/test_conversational_context.py`:

```bash
# Run tests
pytest tests/unit/test_conversational_context.py -v
```

Test coverage includes:
- Context save/load operations
- Follow-up query detection (keywords, pronouns, short queries)
- Context-aware planning hints
- History management (append, limit)
- Error handling

## Usage Examples

### Example 1: Product Gap Analysis with Follow-ups

```
User: "What are the main product gaps?"
System: [Analyzes data, generates insights about UI issues, performance problems]

User: "Show me the reviews for the biggest gap"
System: [Detects follow-up, reuses previous insights, retrieves specific reviews]

User: "Compare that to last month"
System: [Detects follow-up, runs analysis only on last month's data]
```

### Example 2: Sentiment Analysis with Drill-down

```
User: "How is the sentiment trending?"
System: [Analyzes sentiment over time, generates trend insights]

User: "What about the negative reviews?"
System: [Detects follow-up, filters to negative sentiment, provides details]

User: "Show me those reviews"
System: [Detects follow-up, retrieves the specific negative reviews]
```

## Performance Benefits

1. **Reduced Data Fetching**: Reuse cached datasets from previous queries
2. **Simpler Execution Plans**: Skip redundant analysis steps
3. **Faster Response Times**: Leverage pre-computed insights
4. **Better User Experience**: Natural conversational flow

## Requirements Satisfied

This implementation satisfies the following requirements from the design document:

- **Requirement 12.1**: Save execution context to Redis for future reference
- **Requirement 12.2**: Store insights, agent outputs, and metadata
- **Requirement 12.3**: Detect follow-up queries using multiple strategies
- **Requirement 12.6**: Load previous context and enable context-aware planning

## Future Enhancements

Potential improvements for future iterations:

1. **LLM-based Follow-up Detection**: Use LLM to understand complex references
2. **Semantic Similarity**: Match queries to previous queries using embeddings
3. **Context Summarization**: Compress long conversation histories
4. **Cross-session Context**: Link related sessions for the same user
5. **Context Visualization**: Show users what context is being used

## Troubleshooting

### Context Not Loading

**Symptom**: Follow-up queries don't reference previous results

**Solutions**:
1. Check Redis connectivity: `await redis_client.health_check()`
2. Verify session_id is consistent across queries
3. Check Redis TTL hasn't expired (default: 24 hours)
4. Review logs for context loading errors

### Follow-up Not Detected

**Symptom**: Follow-up queries treated as new queries

**Solutions**:
1. Ensure conversation_history is passed to workflow
2. Check query contains follow-up keywords/pronouns
3. Verify previous context exists in Redis
4. Review follow-up detection logs

### Redis Unavailable

**Symptom**: Warnings about Redis connection failures

**Solutions**:
1. Verify REDIS_URL environment variable
2. Check Redis server is running
3. Verify network connectivity
4. System will continue without context persistence

## Related Documentation

- [Chat Message Step Tracking](./CHAT_MESSAGE_STEP_TRACKING.md)
- [Workflow Architecture](../app/optimal_workflow/README.md)
- [Redis Client](../app/services/redis_client.py)
