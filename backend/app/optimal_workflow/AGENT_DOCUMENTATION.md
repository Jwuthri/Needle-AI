# Simple and Medium Agents

This module provides two LlamaIndex-based agent implementations for different complexity levels of queries.

## Overview

### Simple Agent (`simple_agent.py`)
A single **ReActAgent** with access to all tools at once. Best for straightforward queries that may require multiple tool calls but don't need complex coordination.

**Architecture:**
- Single ReActAgent instance
- All tools available simultaneously
- Direct reasoning loop
- Conversation memory via ChatMemoryBuffer

**Use Cases:**
- Database queries
- Statistical calculations
- Weather/search lookups
- Formatting tasks
- Simple multi-step tasks

### Medium Agent (`medium_agent.py`)
A **multi-agent workflow** with specialized agents coordinated by a router. Best for complex queries requiring different types of expertise.

**Architecture:**
- Router Agent: Analyzes query and delegates to specialists
- SQL Agent: Database operations (execute_query, get_schema, count_rows)
- Analysis Agent: Statistics and calculations (stats, comparisons, trends)
- Writer Agent: Formatting and presentation (tables, charts, markdown)

**Workflow Flow:**
```
StartEvent → Router → [SQL | Analysis | Writer | Direct] → Writer → StopEvent
```

**Use Cases:**
- Complex multi-step queries
- Queries requiring specialized expertise
- Tasks needing data retrieval + analysis + formatting
- Scenarios where tool separation improves results

## Installation & Setup

The agents are already integrated into the existing codebase and use:
- Existing LLM configuration from `app.core.config.settings`
- Existing logging from `app.utils.logging`
- LlamaIndex framework (already installed)

No additional dependencies required.

## Usage

### Simple Agent

```python
from app.optimal_workflow.simple_agent import SimpleAgent, run_simple_agent

# Method 1: Using the convenience function
response = await run_simple_agent(
    query="Show me all products and calculate the average price",
    user_id="user_123",
    session_id="session_456"
)

# Method 2: Using the class directly
agent = SimpleAgent(
    user_id="user_123",
    session_id="session_456",
    verbose=True
)

# Regular response
response = await agent.run("What is 25 * 4 + 100?")

# Streaming response
async for chunk in agent.stream_run("Get products from database"):
    print(chunk, end="", flush=True)

# With conversation history
history = [
    {"role": "user", "content": "What is 50 + 50?"},
    {"role": "assistant", "content": "The result is 100"}
]
response = await agent.run("Multiply that by 2", conversation_history=history)
```

### Medium Agent

```python
from app.optimal_workflow.medium_agent import run_medium_agent, MediumAgentWorkflow

# Method 1: Using the convenience function
response = await run_medium_agent(
    query="Get products, calculate average price, and format as table",
    user_id="user_123",
    session_id="session_456"
)

# Method 2: Using the workflow directly
workflow = MediumAgentWorkflow(
    user_id="user_123",
    session_id="session_456",
    conversation_history=[...],
    timeout=120
)

result = await workflow.run(query="Your query here")
```

### With Streaming Events

Both agents support streaming callbacks:

```python
def stream_callback(event: dict):
    event_type = event['type']
    data = event['data']
    
    if event_type == "content":
        print(data['content'], end="", flush=True)
    elif event_type == "agent_step_start":
        print(f"\n[{data['agent']}] Starting...")
    elif event_type == "agent_step_complete":
        print(f"\n[{data['agent']}] Complete!")

response = await run_simple_agent(
    query="...",
    stream_callback=stream_callback
)
```

## Available Tools

### SQL Tools
- `execute_query(query: str)` - Execute SQL queries on mock database
- `get_schema(table_name: str)` - Get table schema information
- `count_rows(table_name: str, condition: str)` - Count rows with optional filter

**Mock Tables:** products, sales, users, orders

### Analysis Tools
- `calculate_stats(data: List[float], stat_type: str)` - Calculate mean, median, std, min, max
- `compare_values(value1: float, value2: float, comparison_type: str)` - Compare numbers
- `find_trends(data_points: List[Dict], x_key: str, y_key: str)` - Identify trends

### Utility Tools
- `calculator(expression: str)` - Evaluate math expressions
- `weather(location: str, date: str)` - Get mock weather data
- `search(query: str, num_results: int)` - Mock search results

### Format Tools
- `create_table(data: List[Dict], format_type: str)` - Format as markdown/html/ascii table
- `create_chart(data: List[Dict], chart_type: str, x_key: str, y_key: str)` - ASCII charts
- `format_markdown(content: str, style: str)` - Structured markdown formatting

## Testing

Run the comprehensive test suite:

```bash
# Run all tests
cd backend
python -m app.optimal_workflow.test_agents

# Interactive mode
python -m app.optimal_workflow.test_agents --interactive
```

Test categories:
1. **Simple Agent Tests** - Various query types using simple agent
2. **Medium Agent Tests** - Workflow routing and multi-agent coordination
3. **Memory Tests** - Conversation context handling
4. **Streaming Tests** - Streaming output functionality
5. **Comparison Tests** - Side-by-side comparison of both agents

## Example Queries

### Simple Agent Examples

```python
# SQL Query
"Show me all products in the database"

# Calculator
"What is 25 * 4 + 100?"

# Weather
"What's the weather in San Francisco?"

# Multi-tool
"Get products, calculate average price, format as table"

# Search
"Search for information about Python programming"
```

### Medium Agent Examples

```python
# Greeting (routes to direct handler)
"Hello! How are you?"

# SQL (routes to SQL agent)
"Show me all sales data from the database"

# Analysis (routes to analysis agent)
"Calculate statistics for 10, 20, 30, 40, 50"

# Format (routes to writer agent)
"Format this as a markdown table: name=Alice age=30"

# Complex (multi-agent: SQL → Analysis → Writer)
"Query products table and calculate average price"
```

## Architecture Details

### Simple Agent Flow

```
User Query
    ↓
ReActAgent (with all tools)
    ↓
[Thought → Action → Observation] loop
    ↓
Final Answer
```

### Medium Agent Flow

```
User Query
    ↓
Router Agent (analyzes & routes)
    ↓
┌─────────┬──────────┬─────────┬────────┐
│   SQL   │ Analysis │  Writer │ Direct │
│  Agent  │  Agent   │  Agent  │ Answer │
└─────────┴──────────┴─────────┴────────┘
    ↓
Writer Agent (formats results)
    ↓
Final Answer
```

## Memory & Context

Both agents use **ChatMemoryBuffer** for maintaining conversation context:

- Token limit: 3000 tokens
- Keeps recent conversation history
- Automatically manages context window
- Works with conversation_history parameter

## Streaming Support

Both agents support streaming output:

**Event Types:**
- `agent_start` - Agent begins processing
- `agent_step_start` - Step/agent starts
- `agent_step_complete` - Step/agent completes
- `content` - Streaming content chunk
- `agent_complete` - Agent finishes
- `agent_error` - Error occurred
- `workflow_complete` - Workflow finishes (medium agent)

## Performance Considerations

### Simple Agent
- **Pros:** Fast, direct, simple to understand
- **Cons:** All tools always available, may be less focused
- **Best for:** Quick queries, single-domain tasks

### Medium Agent
- **Pros:** Specialized agents, better tool separation, coordinated execution
- **Cons:** More complex, slight overhead from routing
- **Best for:** Complex multi-step tasks, queries needing different expertise

## Integration with Existing Workflow

These agents can be integrated into the existing routing system in `main.py`:

```python
from app.optimal_workflow.simple_agent import run_simple_agent
from app.optimal_workflow.medium_agent import run_medium_agent

# In run_workflow function:
if classification.complexity == QueryComplexity.SIMPLE:
    result = await run_simple_agent(...)
elif classification.complexity == QueryComplexity.MEDIUM:
    result = await run_medium_agent(...)
# ... existing complex workflow ...
```

## Extending the Agents

### Adding New Tools

1. Add tool function to `tools/mock_tools.py`
2. Create FunctionTool wrapper in agent file
3. Add to appropriate tool list (`_create_tools()`, `_create_sql_tools()`, etc.)

Example:
```python
# In mock_tools.py
def new_tool(param: str) -> Dict[str, Any]:
    """Tool description."""
    return {"result": "..."}

# In simple_agent.py or medium_agent.py
FunctionTool.from_defaults(
    fn=mock_tools.new_tool,
    name="new_tool_name",
    description="What the tool does and when to use it"
)
```

### Customizing Routing Logic

Edit `MediumAgentWorkflow.route_query()` to add new routing rules or change existing logic.

### Adding New Specialist Agents

1. Create tool set: `_create_specialist_tools()`
2. Add event class for the specialist
3. Add workflow step method with `@step` decorator
4. Update routing logic to include new specialist

## Debugging

Enable verbose logging:

```python
agent = SimpleAgent(verbose=True)  # Enables ReAct reasoning output

# Or use logger
from app.utils.logging import get_logger
logger = get_logger(__name__)
logger.setLevel(logging.DEBUG)
```

## References

- [LlamaIndex ReAct Agent Documentation](https://developers.llamaindex.ai/python/examples/agent/react_agent)
- [LlamaIndex Workflow Documentation](https://developers.llamaindex.ai/python/framework/module_guides/workflow/)
- [LlamaIndex Memory Documentation](https://developers.llamaindex.ai/python/framework/module_guides/deploying/agents/memory/)

## License

Part of the NeedleAI project.

