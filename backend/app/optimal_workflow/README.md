# LlamaIndex Workflow Implementation

This directory contains a reimplementation of the product gap detection workflow using [LlamaIndex Workflows](https://developers.llamaindex.ai/python/llamaagents/workflows/).

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Architecture](#architecture)
- [Workflow Steps](#workflow-steps)
- [Key Features](#key-features)
- [Usage Examples](#usage-examples)
- [NLP Analysis](#nlp-analysis)
- [Configuration](#configuration)
- [File Structure](#file-structure)
- [Comparison with Agno](#comparison-with-agno)
- [Testing](#testing)
- [Migration Guide](#migration-guide)
- [Debugging](#debugging)
- [Contributing](#contributing)

## Overview

The workflow analyzes product gaps using a multi-step process with conditional execution:

1. **Query Analysis** - Determines what steps are needed
2. **Format Detection** - Identifies desired output format
3. **Retrieval Planning** (conditional) - Plans data retrieval
4. **Data Retrieval** (conditional) - Fetches relevant data from database
5. **NLP Analysis** (conditional) - Performs text analysis on reviews
6. **Answer Generation** - Creates final formatted response

## Quick Start

```python
from app.workflow.main import run_workflow

# Run the workflow
result = await run_workflow("What are the main product gaps for Netflix?", user_id=1)
print(result)
```

### Streaming Mode

```python
from app.workflow.main import run_workflow_streaming

async for event in run_workflow_streaming("Your query", user_id=1):
    print(f"Event: {event}")
```

### Direct Workflow Control

```python
from app.workflow.workflow import ProductGapWorkflow

workflow = ProductGapWorkflow(user_id=1, verbose=True, timeout=600)
result = await workflow.run(query="Your question here")
```

## Installation

Install LlamaIndex dependencies:

```bash
pip install llama-index llama-index-llms-openai
```

Or add to `pyproject.toml`:

```toml
[tool.poetry.dependencies]
llama-index = "^0.10.0"
llama-index-llms-openai = "^0.1.0"
```

## Architecture

### Core Concepts

#### Events
Lightweight triggers that activate workflow steps. Events are typed and used for inter-step communication.

```python
class QueryAnalysisEvent(Event):
    """Trigger event for query analysis step."""
    pass
```

#### Steps
Methods decorated with `@step` that process events and optionally emit new events.

```python
@step
async def analyze_query_step(self, ctx: Context, ev: QueryAnalysisEvent):
    query = await ctx.get("query")
    analysis = await analyze_query(query)
    await ctx.set("query_analysis", analysis)
    
    if analysis.needs_data_retrieval:
        ctx.send_event(RetrievalPlanEvent())
```

#### Context
Shared state store that persists across all steps in a workflow run.

```python
# Store data
await ctx.set("key", value)

# Retrieve data
value = await ctx.get("key")

# With default
value = await ctx.get("key", default=None)
```

### Workflow Flow

```
┌─────────────────────────────────────────────────────────────┐
│                        StartEvent                           │
│                     (query: string)                         │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ├──────────────────┬─────────────────┐
                        │                  │                 │
                        ▼                  ▼                 │
              ┌──────────────────┐ ┌──────────────────┐      │
              │ Query Analysis   │ │ Format Detection │      │
              └────────┬─────────┘ └────────┬─────────┘      │
                       │                    │                │
                       │ (if needs data)    │                │
                       ▼                    │                │
              ┌──────────────────┐          │                │
              │ Retrieval Plan   │          │                │
              └────────┬─────────┘          │                │
                       │                    │                │
                       ▼                    │                │
              ┌──────────────────┐          │                │
              │ Data Retrieval   │          │                │
              └────────┬─────────┘          │                │
                       │                    │                │
                       │ (if needs NLP)     │                │
                       ▼                    │                │
              ┌──────────────────┐          │                │
              │  NLP Analysis    │          │                │
              └────────┬─────────┘          │                │
                       │                    │                │
                       └────────┬───────────┘                │
                                │                            │
                                ▼                            │
                       ┌──────────────────┐                  │
                       │ Prepare Context  │◄─────────────────┘
                       └────────┬─────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │ Generate Answer  │
                       └────────┬─────────┘
                                │
                                ▼
                         ┌─────────────┐
                         │  StopEvent  │
                         │  (result)   │
                         └─────────────┘
```

## Workflow Steps

### Step 1: Start
**Trigger:** `StartEvent(query=str)`  
**Actions:**
- Stores query in context
- Emits `QueryAnalysisEvent` and `FormatDetectionEvent` in parallel

### Step 2: Query Analysis
**Trigger:** `QueryAnalysisEvent`  
**Actions:**
- Analyzes query using LLM
- Determines if data retrieval is needed
- Determines if NLP analysis is needed
- Conditionally emits `RetrievalPlanEvent`

### Step 3: Format Detection
**Trigger:** `FormatDetectionEvent`  
**Actions:**
- Detects desired output format using LLM
- Stores format information

### Step 4: Retrieval Planning
**Trigger:** `RetrievalPlanEvent`  
**Actions:**
- Creates SQL queries based on query and available schemas
- Emits `DataRetrievalEvent`

### Step 5: Data Retrieval
**Trigger:** `DataRetrievalEvent`  
**Actions:**
- Executes SQL queries
- Formats results
- Emits `WriterContextEvent`

### Step 6: NLP Analysis (Conditional)
**Trigger:** `DataRetrievedEvent`  
**Actions:**
- Performs text analysis if `needs_nlp_analysis=True`
- Selects appropriate NLP tool(s)
- Adds NLP results to event data

### Step 7: Generate Answer
**Trigger:** `WriterContextEvent`  
**Actions:**
- Gathers all context (query, format, data, analysis)
- Generates final answer using LLM
- Returns `StopEvent` with result

## Key Features

✅ **Event-driven architecture** - Flexible routing based on conditions  
✅ **Conditional step execution** - Steps execute only when needed  
✅ **Parallel step execution** - Query analysis and format detection run in parallel  
✅ **Context-based state management** - Shared state across all steps  
✅ **Built-in streaming support** - Native support for streaming events  
✅ **Comprehensive logging** - Track workflow progress  
✅ **Type-safe events** - Typed events reduce errors  
✅ **Easy to extend** - Add new steps by defining events and methods  

## Usage Examples

### Basic Usage

```python
from app.workflow.main import run_workflow

result = await run_workflow(
    query="What are the main product gaps for Netflix?",
    user_id=1
)
```

### Streaming Mode

```python
from app.workflow.main import run_workflow_streaming

async for event in run_workflow_streaming(query="...", user_id=1):
    print(f"Event: {event}")
```

### Direct Workflow Control

```python
from app.workflow.workflow import ProductGapWorkflow

workflow = ProductGapWorkflow(user_id=1, verbose=True, timeout=600)
result = await workflow.run(query="...")
```

### Enable Verbose Logging

```python
workflow = ProductGapWorkflow(user_id=1, verbose=True)
result = await workflow.run(query="...")
```

## NLP Analysis

The workflow includes conditional NLP analysis capabilities for text-based queries.

### Available NLP Tools

1. **compute_tfidf** - Find most important terms
   - Use for: key terms, important words, topics
   - Parameters: `dataset_name`, `text_column`, `top_n`, `min_df`, `max_df`, `ngram_range`

2. **cluster_reviews** - Group similar text by theme
   - Use for: themes, topics, patterns, grouping
   - Parameters: `dataset_name`, `text_column`, `num_clusters`, `method`, `id_column`, `include_metadata`

3. **analyze_sentiment** - Analyze sentiment and ratings
   - Use for: sentiment, ratings, satisfaction
   - Parameters: `dataset_name`, `text_column`, `rating_column`, `include_distribution`, `group_by`

4. **identify_features** - Extract feature requests and pain points
   - Use for: gaps, missing features, requests
   - Parameters: `dataset_name`, `text_column`, `min_frequency`, `rating_column`, `id_column`, `extract_pain_points`, `extract_product_gaps`

### NLP Tool Selection

The NLP agent automatically selects appropriate tools based on query intent:

| Query Intent | Analysis Type | Selected Tool |
|-------------|---------------|---------------|
| Product gaps, missing features | `gap_detection` | `identify_features` |
| Sentiment, ratings | `sentiment` | `analyze_sentiment` |
| Themes, topics, patterns | `clustering` | `cluster_reviews` |
| Key terms, important words | `tfidf` | `compute_tfidf` |

### Example NLP Queries

```python
# Product gap detection
result = await run_workflow("Find product gaps for Netflix", user_id=1)

# Sentiment analysis
result = await run_workflow("Analyze sentiment in Spotify reviews", user_id=1)

# Theme clustering
result = await run_workflow("What are the main themes in Notion reviews?", user_id=1)
```

## Configuration

Set these environment variables:

```bash
OPENAI_API_KEY=your_key_here
DATABASE_URL=postgresql://user:pass@localhost/db
```

### Custom LLM Configuration

```python
# In agents.py
def get_llm() -> OpenAI:
    return OpenAI(
        model="gpt-4o-mini",
        api_key=SETTINGS.OPENAI_API_KEY,
        temperature=0.1
    )
```

## File Structure

```
workflow/
├── __init__.py              # Package initialization
├── workflow.py              # Main workflow definition with all steps
├── events.py                # Event definitions for inter-step communication
├── agents.py                # LLM agent configurations
├── services.py              # Data retrieval and processing services
├── validation_models.py     # Pydantic models for validation
├── main.py                  # Entry point and execution logic
├── example.py               # Usage examples
├── nlp_example.py           # NLP usage examples
├── README.md                # This file
├── agents/
│   ├── __init__.py
│   ├── base.py              # Base agent classes
│   ├── query_analyzer.py    # Query analysis agent
│   ├── format_detector.py   # Format detection agent
│   ├── retrieval_planner.py # Retrieval planning agent
│   ├── nlp_agent.py         # NLP analysis agent
│   ├── report_coordinator.py # Report coordination
│   └── writer_team.py       # Writer agents (markdown, json, table, chart)
├── tools/
│   ├── __init__.py
│   └── nlp_tools.py         # NLP analysis tools
└── tests/
    ├── __init__.py
    ├── conftest.py          # Test fixtures
    └── test_services.py     # Service tests
```

## Comparison with Agno

### Key Differences

| Feature | Agno | LlamaIndex |
|---------|------|------------|
| Architecture | Declarative | Event-driven |
| Step Definition | `Step` objects | `@step` methods |
| Data Passing | `StepInput`/`StepOutput` | Events + Context |
| Conditionals | `Condition` wrapper | Event emission |
| Parallel | `Parallel` wrapper | Multiple events |
| Flexibility | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

### Agno Workflow
```python
from agno.workflow.workflow import Workflow
from agno.workflow.step import Step

workflow = Workflow(
    steps=[
        Parallel(step1, step2),
        Condition(evaluator=func, steps=[step3]),
        step4
    ]
)
```

### LlamaIndex Workflow
```python
from llama_index.core.workflow import Workflow, step, Context

class MyWorkflow(Workflow):
    @step
    async def step1(self, ctx: Context, ev: Event1) -> Event2:
        # Logic here
        return Event2(data=result)
```

### When to Use Each

**Use Agno When:**
- You need tight integration with Agno agents and teams
- You prefer declarative workflow definitions
- Your workflow has a clear linear structure

**Use LlamaIndex When:**
- You need complex event routing logic
- You want better integration with LlamaIndex tools
- You prefer event-driven architecture
- Your workflow has dynamic branching

## Testing

### Unit Testing Steps

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from llama_index.core.workflow import Context

@pytest.mark.asyncio
async def test_analyze_query_step():
    workflow = ProductGapWorkflow(user_id=1)
    
    ctx = MagicMock(spec=Context)
    ctx.get = AsyncMock(return_value="What are the product gaps?")
    ctx.set = AsyncMock()
    
    event = QueryAnalysisEvent()
    await workflow.analyze_query_step(ctx, event)
    
    ctx.set.assert_called_once()
```

### Run Tests

```bash
# Run all tests
pytest backend/app/workflow/tests/

# Run with coverage
pytest --cov=app.workflow backend/app/workflow/tests/

# Run specific test
pytest backend/app/workflow/tests/test_services.py::test_execute_sql_query
```

## Migration Guide

### Converting from Agno

#### 1. Convert Workflow Class

**Before (Agno):**
```python
workflow = Workflow(
    name="My Workflow",
    steps=[step1, step2, step3]
)
```

**After (LlamaIndex):**
```python
class MyWorkflow(Workflow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
```

#### 2. Convert Steps

**Before (Agno):**
```python
def my_executor(step_input: StepInput) -> StepOutput:
    data = step_input.previous_step_outputs.get("previous_step")
    result = process(data)
    return StepOutput(content=result)

my_step = Step(name="MyStep", executor=my_executor)
```

**After (LlamaIndex):**
```python
@step
async def my_step(self, ctx: Context, ev: MyStepEvent):
    data = await ctx.get("previous_data")
    result = process(data)
    await ctx.set("my_result", result)
    ctx.send_event(NextStepEvent())
```

#### 3. Convert Conditional Execution

**Before (Agno):**
```python
Condition(
    evaluator=needs_data,
    steps=[data_retrieval_step]
)
```

**After (LlamaIndex):**
```python
@step
async def check_needs_data(self, ctx: Context, ev: CheckEvent):
    analysis = await ctx.get("analysis")
    
    if analysis.needs_data:
        ctx.send_event(DataRetrievalEvent())
    else:
        ctx.send_event(SkipDataEvent())
```

## Debugging

### Enable Verbose Mode

```python
workflow = ProductGapWorkflow(verbose=True)
```

### Stream Events

```python
async for event in workflow.stream_events(query="..."):
    print(f"Event: {type(event).__name__}")
```

### Check Context

```python
@step
async def debug_step(self, ctx: Context, ev: DebugEvent):
    logger.info(f"Context: {ctx._data}")
```

### Common Issues

**Issue: Step Not Executing**  
Solution: Check if event is emitted
```python
ctx.send_event(MyStepEvent())  # Don't forget this!
```

**Issue: Context Data Missing**  
Solution: Verify key and that data was stored
```python
await ctx.set("my_key", data)  # Store first
data = await ctx.get("my_key")  # Then retrieve
```

**Issue: Workflow Hangs**  
Solution: Ensure final step returns StopEvent
```python
return StopEvent(result=final_result)
```

## Contributing

When adding new features:

1. Define new events in `events.py`
2. Add step methods in `workflow.py`
3. Update documentation
4. Add tests
5. Update examples

### Adding a New Step

1. Define an event:
```python
class MyNewEvent(Event):
    pass
```

2. Create a step:
```python
@step
async def my_new_step(self, ctx: Context, ev: MyNewEvent):
    result = do_something()
    await ctx.set("my_result", result)
    ctx.send_event(NextEvent())
```

3. Emit the event from another step:
```python
@step
async def previous_step(self, ctx: Context, ev: PreviousEvent):
    ctx.send_event(MyNewEvent())
```

## Best Practices

1. **Keep Events Simple** - Events should be lightweight triggers, not data carriers
2. **Use Context for Data** - Store all data in context, not in events
3. **Handle Errors Gracefully** - Catch exceptions and store error info in context
4. **Log Extensively** - Use logger to track workflow progress
5. **Type Hints** - Use type hints for better IDE support
6. **Async All the Way** - Keep all steps async for better performance
7. **Test Steps Independently** - Each step should be testable in isolation

## License

Same as parent project.
