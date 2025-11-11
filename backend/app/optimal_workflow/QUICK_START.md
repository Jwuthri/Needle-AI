# Quick Start Guide

Get started with Simple and Medium Agents in 5 minutes.

## 1. Installation Check

Both agents use existing dependencies. Verify LlamaIndex is installed:

```bash
cd backend
python -c "import llama_index; print('LlamaIndex installed:', llama_index.__version__)"
```

## 2. Run the Test Suite

Test both agents with pre-built examples:

```bash
cd backend
python -m app.optimal_workflow.test_agents
```

You'll see:
- Simple Agent tests (5 examples)
- Medium Agent tests (6 examples)
- Memory tests
- Streaming tests
- Side-by-side comparison

## 3. Try Interactive Mode

Chat with the agents interactively:

```bash
python -m app.optimal_workflow.test_agents --interactive
```

Choose agent (1=Simple, 2=Medium), then type queries.

## 4. Use in Your Code

### Simple Agent

```python
from app.optimal_workflow.simple_agent import run_simple_agent

async def my_function():
    response = await run_simple_agent(
        query="Show me products and calculate average price",
        user_id="user_123",
        session_id="session_456"
    )
    print(response)
```

### Medium Agent

```python
from app.optimal_workflow.medium_agent import run_medium_agent

async def my_function():
    response = await run_medium_agent(
        query="Get sales data, analyze trends, format as report",
        user_id="user_123",
        session_id="session_456"
    )
    print(response)
```

## 5. Try Example Queries

### For Simple Agent

```python
# SQL Query
"Show me all products in the database"

# Calculator
"What is 25 * 4 + 100?"

# Weather
"What's the weather in San Francisco?"

# Multi-tool
"Get products from database and format as table"
```

### For Medium Agent

```python
# Simple greeting (routes to direct)
"Hello! How are you?"

# SQL query (routes to SQL agent)
"Show me all sales data"

# Analysis (routes to analysis agent)
"Calculate statistics for 10, 20, 30, 40, 50"

# Complex multi-step
"Query products, calculate average price, show as chart"
```

## 6. Enable Streaming

```python
def stream_callback(event):
    if event['type'] == 'content':
        print(event['data']['content'], end='', flush=True)

response = await run_simple_agent(
    query="Your query here",
    stream_callback=stream_callback
)
```

## 7. Use Conversation Memory

```python
history = [
    {"role": "user", "content": "What is 50 + 50?"},
    {"role": "assistant", "content": "The result is 100"}
]

# Agent remembers context
response = await run_simple_agent(
    query="Now multiply that by 2",
    conversation_history=history
)
# Returns: 200
```

## Common Patterns

### Pattern 1: Database + Analysis
```python
query = "Get products and calculate average price"
response = await run_simple_agent(query)
```

### Pattern 2: Multi-Step with Coordination
```python
query = "Query sales, find trends, format as report"
response = await run_medium_agent(query)
```

### Pattern 3: Streaming with Events
```python
from app.optimal_workflow.simple_agent import SimpleAgent

agent = SimpleAgent()

async for chunk in agent.stream_run(query):
    print(chunk, end='', flush=True)
```

## Debugging

Enable verbose mode to see agent reasoning:

```python
from app.optimal_workflow.simple_agent import SimpleAgent

agent = SimpleAgent(verbose=True)
response = await agent.run("Your query")
```

You'll see the ReAct loop:
```
Thought: I need to use a tool...
Action: sql_query
Action Input: {"query": "SELECT * FROM products"}
Observation: [results]
Thought: Now I can answer...
Answer: [final answer]
```

## Next Steps

1. **Read Full Docs:** `AGENT_DOCUMENTATION.md`
2. **Compare Agents:** `AGENT_COMPARISON.md`
3. **Check Implementation:** `IMPLEMENTATION_SUMMARY.md`
4. **Explore Tools:** `tools/mock_tools.py`

## Need Help?

- Check the test file for examples: `test_agents.py`
- Review tool descriptions in: `simple_agent.py` (lines 21-82)
- See workflow steps in: `medium_agent.py` (lines 223-500)

## Available Tools

**SQL:** execute_query, get_schema, count_rows
**Analysis:** calculate_stats, compare_values, find_trends, calculator
**Utility:** weather, search
**Format:** create_table, create_chart, format_markdown

All tools use mock data - perfect for testing without database setup!

## Tips

1. Start with Simple Agent for most queries
2. Use Medium Agent when you need specialized coordination
3. Enable verbose mode to debug tool selection
4. Use streaming for better UX
5. Leverage conversation memory for multi-turn chat

## That's It!

You're ready to use the agents. Run the tests and start experimenting! 🚀

