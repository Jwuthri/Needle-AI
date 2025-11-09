# Agent Comparison Quick Reference

## At a Glance

| Feature | Simple Agent | Medium Agent |
|---------|-------------|--------------|
| **Architecture** | Single ReActAgent | Multi-agent workflow |
| **Tool Organization** | All tools at once | Tools separated by specialist |
| **Routing** | None (agent decides) | Router agent delegates |
| **Complexity** | Low | Medium |
| **Best For** | Direct queries | Multi-step tasks |
| **Execution** | Single reasoning loop | Multi-step coordination |
| **Overhead** | Minimal | Slight (routing) |

## When to Use Which?

### Use Simple Agent When:
- ✅ Query is straightforward
- ✅ All needed tools are available
- ✅ Single domain (e.g., just SQL or just math)
- ✅ Speed is priority
- ✅ Context switching not needed

**Examples:**
- "Show me products in database"
- "Calculate 25 * 4 + 100"
- "What's the weather in NYC?"
- "Search for Python tutorials"

### Use Medium Agent When:
- ✅ Query requires multiple steps
- ✅ Different types of expertise needed
- ✅ Data retrieval + analysis + formatting
- ✅ Tool separation improves focus
- ✅ Complex coordination needed

**Examples:**
- "Get sales data, analyze trends, format as report"
- "Query database for products, calculate average, show as table"
- "Compare two datasets and visualize the results"

## Code Examples

### Simple Agent
```python
from app.optimal_workflow.simple_agent import run_simple_agent

response = await run_simple_agent("Get products and calculate average price")
# Single agent decides which tools to use in sequence
```

### Medium Agent
```python
from app.optimal_workflow.medium_agent import run_medium_agent

response = await run_medium_agent("Get products and calculate average price")
# Router → SQL Agent → Analysis Agent → Writer Agent
```

## Tool Access

### Simple Agent Tools (All Available)
- **SQL:** execute_query, get_schema, count_rows
- **Analysis:** calculate_stats, compare_values, find_trends
- **Utility:** calculator, weather, search
- **Format:** create_table, create_chart, format_markdown

### Medium Agent Tools (Separated by Specialist)

**Router Agent:** No tools (routing logic only)

**SQL Agent:**
- execute_query
- get_schema
- count_rows

**Analysis Agent:**
- calculate_stats
- compare_values
- find_trends
- calculator

**Writer Agent:**
- create_table
- create_chart
- format_markdown

## Performance

### Simple Agent
- ⚡ Fast startup
- ⚡ Direct execution
- ⚡ Low latency
- 📊 ~1-3 reasoning iterations typically

### Medium Agent
- 🐢 Slightly slower (routing overhead)
- 🎯 Better tool focus
- 🔄 Multi-step coordination
- 📊 Multiple agent calls in sequence

## Memory & Context

Both agents support conversation memory:

```python
history = [
    {"role": "user", "content": "Previous question"},
    {"role": "assistant", "content": "Previous answer"}
]

# Works with both agents
response = await run_simple_agent(query, conversation_history=history)
response = await run_medium_agent(query, conversation_history=history)
```

## Streaming

Both agents support streaming:

```python
def callback(event):
    if event['type'] == 'content':
        print(event['data']['content'], end='')

await run_simple_agent(query, stream_callback=callback)
await run_medium_agent(query, stream_callback=callback)
```

## Testing

```bash
# Test both agents
python -m app.optimal_workflow.test_agents

# Interactive mode
python -m app.optimal_workflow.test_agents --interactive
```

## Decision Tree

```
Query received
    │
    ├─ Simple greeting/question? → Simple Agent (direct)
    │
    ├─ Single tool needed? → Simple Agent
    │
    ├─ Multiple tools, same domain? → Simple Agent
    │
    └─ Multiple steps, different domains? → Medium Agent
         │
         ├─ Needs SQL? → SQL Agent
         ├─ Needs Analysis? → Analysis Agent
         ├─ Needs Formatting? → Writer Agent
         └─ Simple answer? → Direct Handler
```

## Common Patterns

### Pattern 1: Database Query Only
```python
# Both work well, Simple is faster
await run_simple_agent("Show me all products")
```

### Pattern 2: Calculation Only
```python
# Both work well, Simple is faster
await run_simple_agent("Calculate average of 10, 20, 30")
```

### Pattern 3: Multi-Step (SQL + Analysis)
```python
# Medium Agent better for coordination
await run_medium_agent("Get products, calculate stats, format report")
```

### Pattern 4: Format Existing Data
```python
# Simple Agent is fine
await run_simple_agent("Format this as markdown table: ...")
```

## Implementation Notes

### Simple Agent
- Uses `ReActAgent.from_tools()`
- Single memory buffer
- All tools registered at initialization
- Agent autonomously selects tools

### Medium Agent
- Uses `Workflow` class with `@step` decorators
- Creates specialized agents per step
- Router analyzes and delegates
- Sequential execution with events

## Tips

1. **Start with Simple Agent** for most queries
2. **Use Medium Agent** when you need explicit coordination
3. **Enable verbose mode** for debugging: `SimpleAgent(verbose=True)`
4. **Use streaming** for better UX on long responses
5. **Leverage memory** for multi-turn conversations
6. **Check tool descriptions** if agent makes wrong tool choice

## Next Steps

- Read full documentation: `AGENT_DOCUMENTATION.md`
- Run tests: `python -m app.optimal_workflow.test_agents`
- Try interactive mode: `--interactive` flag
- Check workflow diagram: `backend/app/optimal_workflow/ARCHITECTURE_DIAGRAM.md`

