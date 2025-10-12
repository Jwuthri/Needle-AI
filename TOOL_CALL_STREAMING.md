# Tool Call Streaming Implementation

Real-time tool call tracking and visualization for the Agno Team orchestrator.

## Overview

The system now captures and streams tool call events from all agents in real-time, showing:
- When an agent calls a tool (ToolCallStarted)
- What tool is being called with what parameters
- When the tool completes and its result (ToolCallCompleted)
- All tool calls are tracked in the execution tree

## Backend Implementation

### Orchestrator Service (`backend/app/services/orchestrator_service.py`)

Added handling for two new Agno Team events:

#### 1. ToolCallStarted Event
Fired when an agent starts calling a tool:

```python
if event_type == "ToolCallStarted":
    agent_id = getattr(chunk, 'agent_id', 'unknown')
    tool_name = getattr(getattr(chunk, 'tool', None), 'tool_name', 'unknown')
    tool_args = getattr(getattr(chunk, 'tool', None), 'tool_args', {})
    
    # Add to execution tree
    node_id = tree.start_node(
        name=f"{agent_id}: {tool_name}",
        node_type=NodeType.TOOL,
        input_summary=str(tool_args)[:200]
    )
    
    # Stream to frontend
    yield {
        "type": "tool_call_started",
        "data": {
            "agent_id": agent_id,
            "tool_name": tool_name,
            "tool_args": tool_args,
            "node_id": node_id
        }
    }
```

#### 2. ToolCallCompleted Event
Fired when a tool finishes executing:

```python
if event_type == "ToolCallCompleted":
    tool_name = getattr(getattr(chunk, 'tool', None), 'tool_name', 'unknown')
    tool_result = getattr(getattr(chunk, 'tool', None), 'result', None)
    
    # Complete node in execution tree
    tree.complete_node(node_id, output_summary=str(tool_result)[:200])
    
    # Stream to frontend
    yield {
        "type": "tool_call_completed",
        "data": {
            "tool_name": tool_name,
            "result": str(tool_result)[:500]
        }
    }
```

### Team Configuration

The team must be configured with streaming parameters:

```python
team = Team(
    name="Query Orchestration Team",
    members=[planner_agent, data_agent, analysis_agent, synthesis_agent],
    model=model,
    db=db,
    stream=True,                          # Enable streaming
    stream_intermediate_steps=True,       # Stream tool calls
    stream_member_events=True,           # Stream member events
)
```

And called with `stream_intermediate_steps=True`:

```python
stream = self.team.arun(
    context_message,
    user_id=user_id,
    session_id=session_id,
    stream=True,
    stream_intermediate_steps=True  # Required for tool call events
)
```

## Frontend Implementation

### Hook Updates (`frontend/src/hooks/use-chat-stream.ts`)

Added new event types and handlers:

```typescript
interface ToolCallStarted {
  agent_id: string;
  tool_name: string;
  tool_args: Record<string, any>;
  node_id: string;
}

interface ToolCallCompleted {
  tool_name: string;
  result: string | null;
}

// In the streaming hook:
case 'tool_call_started':
  const toolStarted = update.data as ToolCallStarted;
  options.onToolCallStarted?.(toolStarted);
  setStatus({
    status: 'tool_call',
    message: `🔧 ${toolStarted.agent_id} calling ${toolStarted.tool_name}...`
  });
  break;

case 'tool_call_completed':
  const toolCompleted = update.data as ToolCallCompleted;
  options.onToolCallCompleted?.(toolCompleted);
  break;
```

### Chat View Usage

The chat view can now react to tool calls:

```typescript
const { sendMessage, isStreaming, currentContent, status } = useChatStream({
  onToolCallStarted: (data) => {
    console.log(`Tool started: ${data.tool_name} by ${data.agent_id}`);
    // Update UI to show tool is running
  },
  onToolCallCompleted: (data) => {
    console.log(`Tool completed: ${data.tool_name}`);
    // Update UI to show tool finished
  },
  onComplete: (response) => {
    // Handle final response
  }
});
```

## SSE Event Stream

The backend sends Server-Sent Events in this order:

1. **status** - Initial status (starting, context_ready)
2. **tool_call_started** - Agent begins calling a tool
3. **tree_update** - Execution tree updated with new node
4. **tool_call_completed** - Tool finishes
5. **tree_update** - Tree node marked as complete
6. **content** - Streaming response text (multiple chunks)
7. **complete** - Final response with full metadata

## Example Output

When running the test script:

```bash
cd backend
python -m examples.test_orchestrator
```

You'll see output like:

```
🚀 Starting Orchestrator Test

📦 Initializing orchestrator...
✅ Orchestrator initialized successfully

💬 Test Query: What is machine learning? Give me an answer with max 300 words

============================================================

🔄 Streaming Response:

📊 Status: [starting] Initializing...
📊 Status: [context_ready] Analyzing query...

🔧 Tool Call Started:
   Agent: Query Planner
   Tool: query_planner
   Args: {'query': 'What is machine learning?', 'context': {...}}

✅ Tool Call Completed: query_planner
   Result: {"output_format": "markdown", "requires_rag": false, ...}

🔧 Tool Call Started:
   Agent: Synthesis Agent
   Tool: citation
   Args: {'sources': [...]}

✅ Tool Call Completed: citation

# Machine Learning

Machine learning is a subset of artificial intelligence...

============================================================
✅ Response Complete!
📝 Message ID: abc-123
🌲 Tree nodes: 5
```

## Execution Tree Structure

The execution tree now includes:

```
Root
├── Query Planner: query_planner (completed)
│   Input: {"query": "...", ...}
│   Output: {"output_format": "markdown", ...}
├── Data Agent: rag_retrieval (completed)
│   Input: {"query": "...", ...}
│   Output: [{"content": "...", ...}]
├── LLM Call: anthropic/claude-3.5-sonnet (completed)
│   Input: Tool call
│   Output: Tokens: 1234
└── Synthesis Agent: citation (completed)
    Input: {"sources": [...]}
    Output: Formatted citations
```

## Benefits

1. **Full Transparency** - See exactly what each agent is doing
2. **Real-time Progress** - Know which tools are running at any moment
3. **Debugging** - Identify slow tools or failures immediately
4. **User Experience** - Show meaningful progress to users
5. **Execution History** - Complete tree of all operations in the session

## Testing

### Simple Test (No Database)
```bash
cd backend
python -m examples.test_agno_team_simple
```

### Full Orchestrator Test
```bash
cd backend
python -m examples.test_orchestrator
```

### Frontend Test
Start the backend and frontend, then send a message through the chat interface. Watch the browser console and UI for tool call updates.

## Future Enhancements

- [ ] Add tool call timing/duration in the tree
- [ ] Show tool call results in a collapsible UI
- [ ] Add filtering to show only specific tool types
- [ ] Implement tool call retry logic with status tracking
- [ ] Add tool call performance metrics

