# Conversation History & Context Persistence Implementation

## Overview

This implementation adds conversation history awareness and Context state persistence to the experimental chat workflow, enabling:

1. **Follow-up question handling** - The coordinator can answer follow-up questions without re-fetching data
2. **Context persistence** - Analysis results (clustering, gap analysis, etc.) persist across conversation turns
3. **Optimized data retrieval** - Data is only loaded once and reused for subsequent questions

## Changes Made

### 1. ChatRequest Model (`backend/app/models/chat.py`)

Added `conversation_history` field to support passing recent messages:

```python
conversation_history: Optional[List[dict]] = Field(
    default=None, 
    description="Recent conversation history (last N messages) for context awareness"
)
```

### 2. Context Persistence Utilities (`backend/app/core/llm/simple_workflow/utils/context_persistence.py`)

New utility module that handles:

- **Serialization**: Converts Context state to JSON-compatible format
  - Handles pandas DataFrames (stores full data for <1000 rows, metadata only for larger)
  - Handles numpy types, datetime objects
  - Recursive serialization of nested structures

- **Deserialization**: Restores Context state from JSON
  - Reconstructs DataFrames with proper dtypes
  - Handles special type markers

- **Database Integration**:
  - `save_context_to_session()`: Saves Context state to session metadata
  - `load_context_from_session()`: Restores Context state from session metadata

### 3. SimpleWorkflowService (`backend/app/services/simple_workflow_service.py`)

Updated `process_message_stream()` to:

1. **Load previous context state** before workflow starts
   - Fetches context state from session metadata
   - Restores state into new Context object
   - Logs restoration status

2. **Store conversation history** in Context
   - Makes history accessible to all agents
   - Logs number of messages added

3. **Save context state** after workflow completes
   - Serializes final Context state
   - Stores in session metadata for next turn
   - Handles errors gracefully

### 4. Coordinator Agent (`backend/app/core/llm/simple_workflow/agents/coordinator_agent.py`)

Enhanced system prompt to:

- **Check conversation history** before routing
- **Identify follow-up questions** (phrases like "what about", "tell me more", etc.)
- **Answer directly** from history when possible
- **Route to Data Discovery only** when new data is needed
- **Optimize data retrieval** by avoiding unnecessary fetches

Key behaviors:
- Time/date/greetings → General Assistant
- Follow-up questions with info in history → Answer directly
- New data questions → Data Discovery (only if data not loaded)

### 5. Data Discovery Agent (`backend/app/core/llm/simple_workflow/agents/data_discovery_agent.py`)

Enhanced system prompt to:

- **Check context state** for existing dataset_data
- **Skip data loading** if dataset already exists from previous query
- **Load data only when needed** (not already present)
- **Optimize for efficiency** by reusing loaded data

Workflow examples:
- **Follow-up**: "What about sentiment?" → Check context, skip loading, route to sentiment_analysis
- **Initial**: "What are my product gaps?" → Load data, then route to gap_analysis

### 6. Chat Experimental API (`backend/app/api/v1/chat_experimental.py`)

Updated to:

1. **Fetch recent messages** from session (last 10 messages = 5 exchanges)
2. **Format as conversation history** with role and content
3. **Track parent_message_id** for message threading:
   - User message links to previous assistant message
   - Assistant message links to current user message
4. **Add to request** before calling workflow service
5. **Log history size and parent relationships** for debugging

### 7. Demo Script (`backend/app/core/llm/simple_workflow/main.py`)

Updated `StreamingProductReviewWorkflow` to:

1. **Accept conversation history and session_id** in StartEvent
2. **Load previous context state** from session before workflow starts
3. **Store conversation history** in Context for agents
4. **Save context state** to session after workflow completes
5. **Demo with follow-up questions** to show context persistence in action

## How It Works

### First Message in Session

```
User: "What are my product gaps?"
  ↓
1. API fetches history (empty for new session)
2. Workflow service creates fresh Context
3. Coordinator routes to Data Discovery
4. Data Discovery loads 'reviews' dataset
5. Gap Analysis performs analysis
6. Context state saved to session metadata
  ↓
Response: Gap analysis results
```

### Follow-up Message

```
User: "What about sentiment?"
  ↓
1. API fetches history (includes previous Q&A)
2. Workflow service loads Context state (reviews dataset already loaded)
3. Coordinator checks history, routes to Data Discovery
4. Data Discovery checks context, sees reviews already loaded, skips loading
5. Sentiment Analysis uses existing data
6. Updated Context state saved
  ↓
Response: Sentiment analysis results (no data reload!)
```

### Follow-up Question Answered from History

```
User: "Tell me more about the top gap"
  ↓
1. API fetches history (includes gap analysis results)
2. Workflow service loads Context state
3. Coordinator checks history, finds gap analysis info
4. Coordinator answers directly without routing
  ↓
Response: Details about top gap from history
```

## Configuration

- **History limit**: 10 messages (5 exchanges) - configurable in `chat_experimental.py`
- **Large DataFrame threshold**: 1000 rows - configurable in `context_persistence.py`
- **Context storage**: Session metadata (JSONB column in database)
- **Message threading**: `parent_message_id` field tracks conversation flow:
  - User messages link to previous assistant message
  - Assistant messages link to triggering user message

## Benefits

1. **Faster responses** - No redundant data loading for follow-up questions
2. **Better context awareness** - Agents can reference previous analysis
3. **Reduced API calls** - Database queries only when needed
4. **Persistent analysis** - Clustering, gap analysis results persist across turns
5. **Natural conversation flow** - Users can ask follow-up questions naturally

## Error Handling

- Context restoration failures are logged but don't block workflow execution
- Context save failures are logged but don't affect response delivery
- Serialization errors fall back to string representation
- Large DataFrames store metadata only to prevent bloat

## Testing Recommendations

Test these scenarios:

1. **Initial question** → "What are my product gaps?"
   - Verify data is loaded
   - Verify context is saved
   - Verify parent_message_id is null for first user message

2. **Follow-up with same data** → "What about sentiment?"
   - Verify data is NOT reloaded
   - Verify sentiment analysis uses existing data
   - Verify parent_message_id links to previous assistant message

3. **Follow-up referencing history** → "Tell me more about the first gap"
   - Verify coordinator answers from history
   - Verify no data retrieval occurs
   - Verify message threading is maintained

4. **New session** → Start fresh conversation
   - Verify no context is loaded
   - Verify fresh data fetch occurs
   - Verify parent_message_id is null for first message

5. **Large dataset** → Use dataset with >1000 rows
   - Verify only metadata is stored
   - Verify workflow still functions correctly

6. **Demo script** → Run `python backend/app/core/llm/simple_workflow/main.py`
   - Verify conversation history is tracked
   - Verify context persistence across queries
   - Verify follow-up question reuses loaded data

## Future Enhancements

Potential improvements:

1. **Configurable history limit** - Allow users to set history depth
2. **Selective context persistence** - Store only relevant parts of context
3. **Context compression** - Compress large context states
4. **Context expiration** - Auto-clear old context after N days
5. **Multi-dataset support** - Better handling of multiple datasets in context

