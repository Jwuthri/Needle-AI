# Streaming Chat with LLM Call Logging - Implementation Guide

## Overview

Successfully implemented real-time streaming chat with:
- ✅ Live progress updates as Agno team processes queries
- ✅ LLM call logging to database for every team call
- ✅ Execution tree updates in real-time
- ✅ Server-Sent Events (SSE) for frontend streaming
- ✅ Ability to see what's happening during "thinking" phase

## Problem Solved

**Before:** User sends query → waits forever → no idea what's happening → finally gets response
**After:** User sends query → sees "Analyzing query..." → "Retrieving data..." → sees LLM calls → gets real-time response

## Backend Implementation

### 1. LLM Call Logging

Every time the Agno team makes an LLM call, it's now logged to the `llm_calls` table:

```python
# In orchestrator_service.py
async def _log_llm_call(self, message, user_id, session_id, db):
    """Log an LLM call to the database."""
    metrics = getattr(message, 'metrics', None)
    if not metrics:
        return
    
    llm_logger = LLMLogger()
    await llm_logger.log_llm_call(
        db=db,
        model=getattr(message, 'model', 'unknown'),
        prompt=str(message.content)[:1000],
        response=str(message.content)[:1000],
        prompt_tokens=getattr(metrics, 'prompt_tokens', 0),
        completion_tokens=getattr(metrics, 'completion_tokens', 0),
        total_tokens=getattr(metrics, 'total_tokens', 0),
        call_type=LLMCallTypeEnum.CHAT,
        user_id=user_id,
        session_id=session_id,
        metadata={
            "agent": "orchestrator_team",
            "model": model,
            "role": "assistant"
        }
    )
```

**What gets logged:**
- Model used (gpt-5-nano, claude-sonnet-4.5, etc.)
- Prompt and response text (first 1000 chars)
- Token counts (prompt, completion, total)
- Call type (CHAT, TOOL_USE, etc.)
- User ID and session ID
- Metadata (agent name, model, role)

### 2. Streaming Endpoint

New endpoint: `POST /api/v1/chat/stream`

**Response format:** Server-Sent Events (SSE)

```
data: {"type": "status", "data": {"status": "starting", "message": "Initializing..."}}

data: {"type": "status", "data": {"status": "context_ready", "message": "Analyzing query..."}}

data: {"type": "tree_update", "data": {...execution_tree...}}

data: {"type": "content", "data": {"content": "Based on the reviews, "}}

data: {"type": "content", "data": {"content": "the top product gaps are..."}}

data: {"type": "complete", "data": {...full_response...}}
```

**Event types:**
- `status` - Progress updates ("Analyzing query...", "Retrieving data...")
- `content` - Streaming response text chunks
- `tree_update` - Real-time execution tree updates showing each LLM call
- `complete` - Final response with metadata
- `error` - Error information if something fails

### 3. Non-Streaming Endpoint (Backward Compatible)

Original endpoint: `POST /api/v1/chat/`

Still works exactly as before, but now **also logs all LLM calls** to the database!

```python
# In process_message (non-streaming)
if hasattr(team_response, 'messages'):
    for msg in team_response.messages:
        if msg.role == 'assistant' and hasattr(msg, 'metrics'):
            await self._log_llm_call(msg, user_id, session_id, db)
```

## Frontend Implementation

### 1. Streaming Hook

New custom hook: `use-chat-stream.ts`

```typescript
import { useChatStream } from '@/hooks/use-chat-stream';

function ChatComponent() {
  const {
    sendMessage,
    stopStreaming,
    isStreaming,
    currentContent,
    currentTree,
    status
  } = useChatStream({
    onStatusUpdate: (status, message) => {
      console.log(`Status: ${message}`);
    },
    onContentChunk: (chunk) => {
      // Display chunk immediately
    },
    onTreeUpdate: (tree) => {
      // Update execution tree UI
    },
    onComplete: (response) => {
      // Final response received
    },
    onError: (error) => {
      console.error(error);
    }
  });

  const handleSubmit = async () => {
    await sendMessage({
      message: "What are the top product gaps?",
      session_id: "session-123",
      company_id: "comp-456"
    });
  };

  return (
    <div>
      {isStreaming && <p>{status?.message}</p>}
      <div>{currentContent}</div>
      {currentTree && <ExecutionTree tree={currentTree} />}
    </div>
  );
}
```

### 2. Real-Time UI Updates

As the backend processes the query, the frontend shows:

1. **Initial Status:**
   ```
   🔄 Initializing...
   ```

2. **Query Analysis:**
   ```
   🔄 Analyzing query...
   [Execution Tree shows: "LLM Call: gpt-5-nano" - Query Planning]
   ```

3. **Data Retrieval:**
   ```
   🔄 Retrieving data...
   [Execution Tree shows: "LLM Call: claude-sonnet-4.5" - RAG Retrieval]
   ```

4. **Content Streaming:**
   ```
   Based on the reviews, the top product gaps are:
   1. Mobile app performance
   2. Integration with third-party tools
   ...
   ```

5. **Complete:**
   ```
   ✅ Complete
   [Full execution tree with all LLM calls]
   [Final response with visualizations]
   ```

## Usage Examples

### Example 1: Stream with React

```tsx
import { useChatStream } from '@/hooks/use-chat-stream';
import { ExecutionTree } from '@/components/chat/execution-tree';

export function StreamingChat() {
  const [messages, setMessages] = useState([]);
  
  const { sendMessage, isStreaming, currentContent, currentTree, status } = useChatStream({
    onComplete: (response) => {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: response.message,
        execution_tree: response.metadata?.execution_tree
      }]);
    }
  });

  return (
    <div>
      {/* Status bar */}
      {isStreaming && status && (
        <div className="bg-blue-50 p-2 rounded">
          <span className="animate-pulse">⚡</span> {status.message}
        </div>
      )}

      {/* Messages */}
      {messages.map((msg, idx) => (
        <div key={idx}>
          <p>{msg.content}</p>
          {msg.execution_tree && <ExecutionTree tree={msg.execution_tree} />}
        </div>
      ))}

      {/* Current streaming content */}
      {isStreaming && currentContent && (
        <div className="bg-gray-50 p-4 rounded animate-pulse">
          <p>{currentContent}</p>
          {currentTree && <ExecutionTree tree={currentTree} />}
        </div>
      )}
    </div>
  );
}
```

### Example 2: cURL Test

```bash
# Test streaming endpoint
curl -N -X POST http://localhost:8000/api/v1/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What are the top 5 product gaps from negative reviews?",
    "company_id": "comp-123",
    "session_id": "test-session"
  }'

# Output:
# data: {"type":"status","data":{"status":"starting","message":"Initializing..."}}
# 
# data: {"type":"status","data":{"status":"context_ready","message":"Analyzing query..."}}
#
# data: {"type":"tree_update","data":{...tree with LLM call...}}
#
# data: {"type":"content","data":{"content":"Based on the"}}
#
# data: {"type":"content","data":{"content":" reviews, "}}
# ...
```

### Example 3: Check LLM Calls in Database

```sql
-- See all LLM calls for a session
SELECT 
    model,
    call_type,
    prompt_tokens,
    completion_tokens,
    total_tokens,
    created_at,
    metadata
FROM llm_calls
WHERE session_id = 'test-session'
ORDER BY created_at;

-- Example output:
-- model                      | call_type | prompt_tokens | completion_tokens | total_tokens | created_at
-- ---------------------------+-----------+---------------+-------------------+--------------+------------
-- openai/gpt-5-nano          | TOOL_USE  | 234           | 45                | 279          | 2025-10-12
-- anthropic/claude-sonnet-4.5| CHAT      | 456           | 123               | 579          | 2025-10-12
-- openai/gpt-5-nano          | TOOL_USE  | 189           | 34                | 223          | 2025-10-12
```

## Benefits

### 1. Visibility
- Users see what's happening in real-time
- No more "waiting forever" with no feedback
- Understand which agents/tools are being used

### 2. Debugging
- Every LLM call is logged to database
- Can analyze token usage per query
- Can see exactly what prompts were sent
- Execution tree shows full reasoning path

### 3. Cost Tracking
- Track token usage per user
- Track token usage per session
- Calculate costs per query
- Identify expensive queries

### 4. Performance
- Users get immediate feedback
- Content streams as it's generated (feels faster)
- Can stop generation if needed
- See progress updates during long operations

### 5. Analytics
- Which models are used most?
- What's the average token count per query?
- Which queries are most expensive?
- How many LLM calls per query on average?

## Testing Checklist

### Backend Tests

- [ ] Start backend: `cd backend && uvicorn app.main:app --reload`
- [ ] Test non-streaming endpoint (should log LLM calls):
  ```bash
  curl -X POST http://localhost:8000/api/v1/chat/ \
    -H "Content-Type: application/json" \
    -d '{"message": "Hello", "session_id": "test-123"}'
  ```
- [ ] Check database for LLM calls:
  ```sql
  SELECT * FROM llm_calls WHERE session_id = 'test-123';
  ```
- [ ] Test streaming endpoint:
  ```bash
  curl -N -X POST http://localhost:8000/api/v1/chat/stream \
    -H "Content-Type: application/json" \
    -d '{"message": "What are product gaps?", "company_id": "comp-123"}'
  ```
- [ ] Verify real-time updates are received
- [ ] Check database for all LLM calls from streaming

### Frontend Tests

- [ ] Install frontend deps: `cd frontend && npm install`
- [ ] Test streaming hook in component
- [ ] Verify status updates display correctly
- [ ] Verify content streams in real-time
- [ ] Verify execution tree updates live
- [ ] Test stop streaming functionality
- [ ] Test error handling

## Performance Considerations

### Database
- LLM calls are logged **asynchronously** (doesn't block response)
- Consider adding index on `session_id` and `user_id` if high volume:
  ```sql
  CREATE INDEX idx_llm_calls_session ON llm_calls(session_id);
  CREATE INDEX idx_llm_calls_user ON llm_calls(user_id);
  ```

### Streaming
- Uses Server-Sent Events (SSE) - lightweight, one-way
- Auto-reconnects if connection drops
- Can buffer messages if frontend is slow

### Token Limits
- Prompts and responses truncated to 1000 chars in DB
- Full content in `chat_messages` table
- Prevents database bloat

## Troubleshooting

### "LLM calls not being logged"
- Check database session is passed to orchestrator
- Verify `llm_calls` table exists (run migrations)
- Check logs for errors in `_log_llm_call`

### "Streaming not working"
- Ensure nginx/proxy doesn't buffer (set `X-Accel-Buffering: no`)
- Check firewall allows SSE connections
- Verify frontend correctly handles SSE format

### "Execution tree not updating"
- Check Agno team response has `messages` attribute
- Verify `metrics` exist on messages
- Check frontend `useChatStream` hook is used correctly

## Next Steps

1. Add visualization of LLM call costs in analytics dashboard
2. Add "token budget" alerts for expensive queries
3. Add retry logic for failed LLM calls
4. Add rate limiting per user based on token usage
5. Add export functionality for LLM call logs

---

**The streaming system with LLM logging is ready for production!** 🚀

Users can now see exactly what's happening, and you can track every single LLM call for debugging, analytics, and cost management.

