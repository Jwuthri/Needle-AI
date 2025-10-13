# Agno Pipeline Refactor Plan

## Backend: Database Layer

### Remove Execution Tree Tables

- Delete `backend/app/database/models/execution_tree.py`
- Delete `backend/app/database/repositories/execution_tree.py`
- Delete `backend/app/api/v1/execution_tree.py`
- Delete migration `backend/alembic/versions/005_add_execution_tree.py`

### Create Chat Message Steps Table

Create `backend/app/database/models/chat_message_step.py`:

- Fields: `id`, `message_id` (FK to chat_messages.id), `agent_name`, `step_order`, `tool_call` (JSONB), `prediction` (Text), `created_at`
- Store structured output (BaseModel) in `tool_call` as JSONB
- Store text output in `prediction`
- Link to the assistant's final message

Create `backend/app/database/repositories/chat_message_step.py`:

- Methods: `create()`, `get_by_message_id()`, `delete_by_message_id()`

Create Alembic migration `006_replace_execution_tree_with_steps.py`:

- Drop `execution_tree_sessions` and `execution_tree_nodes` tables
- Create `chat_message_steps` table

## Backend: Streaming Protocol (SSE)

### Streaming Architecture

Using **Server-Sent Events (SSE)** with JSON payloads for reliable real-time updates.

Event types sent to frontend:

```python
{type: "connected", data: {}}  # Initial handshake
{type: "agent_step_start", data: {agent_name, step_id, timestamp}}  # Agent starts
{type: "agent_step_content", data: {step_id, content_chunk}}  # Streaming content
{type: "agent_step_complete", data: {step_id, agent_name, content, is_structured}}  # Agent done
{type: "content", data: {content}}  # Final response streaming
{type: "complete", data: {message, metadata}}  # All done
{type: "error", data: {error}}  # Error occurred
```

### Update Orchestrator Service

Update `backend/app/services/orchestrator_service.py`:

**Reliability improvements:**

1. Track active agent steps with unique `step_id` (UUID)
2. Buffer content accumulation per step to handle out-of-order events
3. Graceful fallback if agent_name missing
4. Proper error handling with step cleanup
5. Ensure steps are stored even if frontend disconnects

**Event handling logic:**

```python
# State tracking
active_steps = {}  # step_id -> {agent_name, content_buffer, started_at}
completed_steps = []  # For DB storage

if event_type == "TeamToolCallStarted":
    agent_id = getattr(chunk, 'agent_id', None) or getattr(chunk, 'agent', None) or 'unknown-agent'
    step_id = str(uuid.uuid4())
    active_steps[step_id] = {
        'agent_name': agent_id,
        'content_buffer': [],
        'started_at': datetime.utcnow()
    }
    # Emit to frontend
    yield {
        "type": "agent_step_start",
        "data": {"agent_name": agent_id, "step_id": step_id, "timestamp": ...}
    }

# Accumulate content between start and complete
if event_type == "RunContent" and current_step_id:
    content = chunk.content
    active_steps[current_step_id]['content_buffer'].append(content)
    # Stream content to frontend
    yield {
        "type": "agent_step_content",
        "data": {"step_id": current_step_id, "content_chunk": content}
    }

if event_type == "TeamToolCallCompleted":
    step_id = ...  # Get from tracking
    step_data = active_steps.pop(step_id)
    
    # Combine buffered content
    full_content = ''.join(step_data['content_buffer'])
    
    # Detect type
    is_structured = isinstance(full_content, BaseModel)
    if is_structured:
        content_dict = full_content.model_dump()
    else:
        content_dict = full_content
    
    # Store for later DB write
    completed_steps.append({
        'agent_name': step_data['agent_name'],
        'content': content_dict,
        'is_structured': is_structured,
        'order': len(completed_steps)
    })
    
    # Emit completion to frontend
    yield {
        "type": "agent_step_complete",
        "data": {
            "step_id": step_id,
            "agent_name": step_data['agent_name'],
            "content": content_dict,
            "is_structured": is_structured
        }
    }

# After streaming completes, save all steps to DB
# Link to assistant message_id
for step in completed_steps:
    await ChatMessageStepRepository.create(
        db=db,
        message_id=assistant_message_id,
        agent_name=step['agent_name'],
        step_order=step['order'],
        tool_call=step['content'] if step['is_structured'] else None,
        prediction=step['content'] if not step['is_structured'] else None
    )
```

**Additional improvements:**

- Add timeout handling for stuck agent steps
- Log all events for debugging
- Validate agent_name is never None/empty
- Handle BaseModel serialization errors gracefully

### Update Agno Chat Service

Update `backend/app/services/agno_chat_service.py` if it references execution tree

## Backend: API Layer

### Update Chat API

Update `backend/app/api/v1/chat.py`:

- Remove execution_tree references from streaming response
- Remove tree_update events
- Add agent_step events to streaming
- Store steps when saving assistant message to DB
- Remove any execution tree metadata from responses

### Update API Router

Update `backend/app/api/v1/router.py`:

- Remove execution_tree endpoint registration

## Frontend: Hooks & Streaming

### Update Chat Stream Hook

Update `frontend/src/hooks/use-chat-stream.ts`:

- Remove execution tree state
- Add agent steps tracking: `currentSteps: Array<{agent_name, content, is_structured, timestamp}>`
- Handle new `agent_step` events
- Track which agent is currently active
- Store completed steps for display in message

### Add Types

Update `frontend/src/types/chat.ts`:

```typescript
interface AgentStep {
  agent_name: string
  content: any // BaseModel or string
  is_structured: boolean
  timestamp: string
}

interface EnhancedChatMessage {
  // ... existing fields
  agent_steps?: AgentStep[]
}
```

## Frontend: UI Components

### Update Chat View

Update `frontend/src/components/chat/chat-view.tsx`:

- Remove execution tree display logic
- Add real-time agent step timeline/progress indicator
- Show current agent name and status during streaming
- Display like: "🤖 [intent-detector] analyzing..." → "🤖 [answer-agent] responding..."

### Update Enhanced Message

Update `frontend/src/components/chat/enhanced-message.tsx`:

- Add collapsible "Execution Steps" section
- Display agent steps as expandable list
- Show structured outputs (BaseModel) as formatted JSON
- Show text outputs as readable text
- Format: "[Agent Name] → [Output Preview] (click to expand)"

### Clean Up

- Remove any execution tree related components
- Remove tree visualization UI
- Update any references to tree data structure

## Testing & Validation

### Backend Testing

- Test TeamToolCallStarted/Completed event handling
- Verify BaseModel detection and JSON serialization
- Verify text content storage
- Test step ordering and agent_name capture
- Test database persistence of steps

### Frontend Testing  

- Test real-time step updates during streaming
- Test collapsible step display in completed messages
- Verify agent names display correctly
- Test structured vs text output rendering

### Integration Testing

- Full flow: send message → see agent timeline → view completed steps
- Multiple agents in sequence
- Error handling in agent steps