# Tree-Based Orchestration Architecture

## Overview

This implementation brings Elysia's tree-based decision architecture to NeedleAI, using Agno agents for execution. The tree structure provides explicit, transparent decision-making with step-by-step agent streaming and database persistence.

## Key Concepts

### 1. Tree Structure

A `Tree` organizes agents and tools in a hierarchical decision structure:

- **Branches**: Decision points where an agent chooses the next action
- **Tools**: Executable actions that yield structured results
- **Environment**: Shared state accessible by all agents/tools
- **TreeData**: Central context object passed through execution

### 2. Decision Flow

```
Root Branch (Base)
├── Tool: CitedSummarizer (end=True)
├── Tool: TextResponse (end=True)
├── Tool: Visualize
└── Branch: Search
    ├── Tool: Query
    │   └── Tool: SummarizeItems (chained, runs after Query)
    └── Tool: Aggregate
```

At each branch, an agent decides which option to execute based on:
- User's query
- Current environment state
- Available tools
- Previous results

### 3. Streaming Architecture

The tree executor uses Agno's `pre_hooks` and `post_hooks` to capture agent execution:

**Pre-hook** (before agent executes):
```python
async def pre_hook(agent, *args, **kwargs):
    # Emit agent_step_start
    yield {
        "type": "agent_step_start",
        "data": {
            "agent_name": agent.name,
            "step_id": step_id,
            "step_order": step_counter
        }
    }
```

**Post-hook** (after agent executes):
```python
async def post_hook(agent, result, step_id, *args, **kwargs):
    # Extract content
    content = extract_content(result)
    
    # Emit agent_step_complete
    yield {
        "type": "agent_step_complete",
        "data": {
            "agent_name": agent.name,
            "content": content,
            "is_structured": is_structured
        }
    }
    
    # Save to database
    await save_step_to_db(...)
```

### 4. Structured Returns

Tools yield structured `Return` objects:

- **Status**: Progress updates ("Searching knowledge base...")
- **Result**: Data results (query results, statistics)
- **Retrieval**: Retrieved objects from databases
- **Response**: Text responses to user
- **Error**: Errors with recovery info
- **Completed**: Task completion signals

## Architecture

```
app/agents/tree/
├── __init__.py              # Public API
├── base.py                  # Tree, DecisionNode, Branch
├── environment.py           # TreeData, Environment, CollectionData
├── tool.py                  # TreeTool, @tool decorator
├── returns.py               # Return types (Status, Result, etc.)
├── executors/
│   ├── __init__.py
│   └── agno_executor.py    # Agno implementation with hooks
└── workflows/
    ├── __init__.py
    ├── elysia_tools.py     # Tool implementations
    └── multi_branch.py     # Multi-branch workflow

app/services/
└── tree_orchestrator_service.py  # Service integration

app/api/v1/
└── chat.py                 # New /tree/stream endpoint
```

## Usage

### 1. Using the Tree Orchestrator Service

```python
from app.services.tree_orchestrator_service import TreeOrchestratorService

# Initialize service
service = TreeOrchestratorService(settings)
await service.initialize()

# Process message with streaming
async for update in service.process_message_stream(
    request=chat_request,
    user_id=user_id,
    db=db_session
):
    if update["type"] == "agent_step_start":
        print(f"Agent started: {update['data']['agent_name']}")
    
    elif update["type"] == "agent_step_complete":
        print(f"Agent completed: {update['data']['content']}")
    
    elif update["type"] == "content":
        print(update["data"]["content"], end="")
```

### 2. Using the Multi-Branch Workflow Directly

```python
from app.agents.tree.workflows.multi_branch import create_multi_branch_workflow
from agno.models.openrouter import OpenRouter

# Create workflow
model = OpenRouter(id="anthropic/claude-3.5-sonnet", api_key=api_key)
executor = create_multi_branch_workflow(model=model)

# Execute with streaming callback
async def stream_callback(update):
    # Handle updates in real-time
    await send_to_frontend(update)

async for chunk in executor.run(
    user_prompt="What are complaints about our product?",
    stream_callback=stream_callback,
    db_session=db,
    message_id=message_id
):
    # Process team chunks
    pass
```

### 3. Creating Custom Trees

```python
from app.agents.tree.base import Tree
from app.agents.tree.tool import TreeTool, tool
from app.agents.tree.returns import Status, Result

# Define custom tool
@tool(name="custom_tool", description="My custom tool")
async def my_tool(tree_data: TreeData, param: str):
    yield Status("Processing...")
    result = await process(param)
    yield Result(
        data=result,
        summary="Processing complete",
        display_type="json"
    )

# Build tree
tree = Tree(name="Custom Workflow")

tree.add_branch(
    root=True,
    branch_id="root",
    instruction="Choose the best action",
    status="Analyzing query..."
)

tree.add_tool(my_tool, branch_id="root")

# Execute with Agno
from app.agents.tree.executors.agno_executor import AgnoTreeExecutor

executor = AgnoTreeExecutor(tree, model=model)
async for update in executor.run(
    user_prompt="User's query",
    stream_callback=callback
):
    yield update
```

## API Endpoint

### POST /api/v1/chat/tree/stream

Stream chat responses using tree-based orchestration.

**Request:**
```json
{
  "message": "What are the top complaints about our product?",
  "session_id": "optional-session-id",
  "company_id": "optional-company-id"
}
```

**Response Stream (SSE):**

```
data: {"type": "agent_step_start", "data": {"agent_name": "Base", "step_id": "...", "step_order": 0}}

data: {"type": "agent_step_complete", "data": {"agent_name": "Base", "content": {"decision": "search"}, "is_structured": true}}

data: {"type": "agent_step_start", "data": {"agent_name": "Search", "step_id": "...", "step_order": 1}}

data: {"type": "agent_step_complete", "data": {"agent_name": "Search", "content": {"decision": "query"}, "is_structured": true}}

data: {"type": "content", "data": {"content": "Based on the analysis..."}}

data: {"type": "complete", "data": {"message": "...", "metadata": {...}}}
```

## Frontend Integration

The frontend receives real-time updates:

```typescript
const eventSource = new EventSource('/api/v1/chat/tree/stream');

eventSource.onmessage = (event) => {
  const update = JSON.parse(event.data);
  
  switch (update.type) {
    case 'agent_step_start':
      // Show agent started UI
      showAgentStart(update.data.agent_name);
      break;
    
    case 'agent_step_complete':
      // Show agent completed with content
      showAgentComplete(update.data.agent_name, update.data.content);
      break;
    
    case 'content':
      // Stream final response
      appendContent(update.data.content);
      break;
    
    case 'complete':
      // Finalize UI
      markComplete();
      break;
  }
};
```

## Database Persistence

Agent steps are automatically saved to the `chat_message_steps` table:

```sql
CREATE TABLE chat_message_steps (
    id VARCHAR PRIMARY KEY,
    message_id VARCHAR REFERENCES chat_messages(id),
    agent_name VARCHAR(255) NOT NULL,
    step_order INTEGER NOT NULL,
    tool_call JSON,          -- For structured outputs
    prediction TEXT,         -- For text outputs
    created_at TIMESTAMP DEFAULT NOW()
);
```

This allows:
- Replay of agent execution
- Debugging decision paths
- Performance analysis
- UI visualization of agent flow

## Comparison: Tree vs. Current Orchestrator

| Feature | Current Orchestrator | Tree Orchestrator |
|---------|---------------------|-------------------|
| **Structure** | Implicit coordination | Explicit decision tree |
| **Decisions** | Hidden in team logic | Visible at each branch |
| **Flow Control** | Agent-driven | Tree-driven with decisions |
| **Branching** | Limited | Full tree branching support |
| **Tool Chaining** | Manual | Automatic (`from_tool_ids`) |
| **Environment** | Per-agent state | Shared persistent environment |
| **Transparency** | Black box | Full execution visibility |
| **Debugging** | Difficult | Tree structure makes it clear |

## Multi-Branch Workflow

The default workflow replicates Elysia's multi-branch pattern:

### Base Branch (Root)
**Instruction**: "Choose between search, visualize, or direct response"

**Options**:
- `search` → Go to Search Branch
- `visualize` → Create visualizations
- `text_response` → Respond directly (ends tree)
- `cited_summarizer` → Synthesize with citations (ends tree)

### Search Branch
**Instruction**: "Choose between semantic query or statistical aggregation"

**Options**:
- `query_knowledge_base` → Retrieve specific entries
  - Automatically chains to `summarize_items`
- `aggregate_data` → Compute statistics

### Example Flow

Query: "What are the top complaints about our product?"

1. **Base Agent** decides: Need data → chooses `search`
2. **Search Agent** decides: Need specific reviews → chooses `query_knowledge_base`
3. **Query Tool** retrieves reviews → stores in environment
4. **Summarizer Tool** (chained) summarizes reviews
5. **Base Agent** (returns to base) decides: Have data → chooses `cited_summarizer`
6. **Cited Summarizer** generates final response with citations

## Benefits

1. **Transparency**: Every decision is explicit and logged
2. **Debuggability**: Clear execution path through tree
3. **Flexibility**: Easy to add/remove/reorder tools
4. **Reusability**: Same tree structure works with different executors
5. **Control**: Explicit branching vs implicit coordination
6. **Testing**: Can mock individual nodes
7. **Streaming**: Real-time agent step updates
8. **Persistence**: All steps saved to database

## Next Steps

1. ✅ Core tree infrastructure implemented
2. ✅ Agno executor with streaming hooks
3. ✅ Multi-branch workflow
4. ✅ API endpoint integration
5. ✅ Database persistence
6. 🔲 Frontend tree visualization component
7. 🔲 Additional workflows (one-branch, custom)
8. 🔲 Crew AI executor
9. 🔲 OpenAI Agent SDK executor
10. 🔲 Performance optimization

## Examples

See:
- `backend/examples/tree_workflow_example.py` - Comprehensive examples
- `backend/app/agents/tree/workflows/multi_branch.py` - Multi-branch workflow
- `backend/app/services/tree_orchestrator_service.py` - Service integration

## Resources

- **Elysia Inspiration**: [https://github.com/weaviate/elysia](https://github.com/weaviate/elysia)
- **Agno Documentation**: [https://docs.agno.com](https://docs.agno.com)
- **Plan Document**: `/elysia-tree-architecture.plan.md`

