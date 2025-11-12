# Product Review Analysis Workflow

This directory contains the multi-agent workflow system for analyzing product reviews.

## Components

### WorkflowOrchestrator

The central orchestration layer that manages execution plans, coordinates parallel agents, handles retries, and ensures thread-safe state updates.

**Key Features:**
- Dependency-based execution planning
- Parallel execution of independent steps
- Automatic retry with exponential backoff
- Thread-safe state management
- Real-time streaming event emission
- Graceful error handling

### Usage Example

```python
import asyncio
from app.core.llm.workflow import (
    WorkflowOrchestrator,
    PlanStep,
    ExecutionPlan,
)
from app.models.workflow import ExecutionContext, RetryConfig

# Create execution context
context = ExecutionContext(
    user_id="user_123",
    session_id="session_456",
    message_id="msg_789",
    query="What are my main product gaps?",
    user_datasets=[],
    lock=asyncio.Lock()
)

# Define execution plan
plan = ExecutionPlan(
    plan_id="plan_001",
    steps=[
        # Step 1: Get user datasets (no dependencies)
        PlanStep(
            step_id="step1",
            agent_type="data_retrieval",
            action="get_user_datasets_with_eda",
            parameters={"user_id": "user_123"},
            depends_on=[]
        ),
        # Step 2 & 3: Run sentiment and topic analysis in parallel
        PlanStep(
            step_id="step2",
            agent_type="sentiment",
            action="analyze_sentiment",
            parameters={"rating_filter": "<=2"},
            depends_on=["step1"],
            can_run_parallel_with=["step3"]
        ),
        PlanStep(
            step_id="step3",
            agent_type="topic_modeling",
            action="identify_topics",
            parameters={"num_topics": 5},
            depends_on=["step1"],
            can_run_parallel_with=["step2"]
        ),
        # Step 4: Synthesize results (depends on both analyses)
        PlanStep(
            step_id="step4",
            agent_type="synthesis",
            action="synthesize_response",
            parameters={"format": "markdown"},
            depends_on=["step2", "step3"]
        )
    ]
)

# Configure retry behavior
retry_config = RetryConfig(
    max_retries=3,
    backoff_factor=2.0,
    initial_delay_seconds=1.0,
    max_delay_seconds=30.0
)

# Optional: Define streaming callback
async def stream_callback(event):
    print(f"Event: {event['event_type']}")
    print(f"Data: {event['data']}")

# Create orchestrator
orchestrator = WorkflowOrchestrator(
    retry_config=retry_config,
    stream_callback=stream_callback
)

# Execute plan
result = await orchestrator.execute_plan(context, plan)

# Check results
if result.success:
    print(f"Plan completed successfully in {result.execution_time_ms}ms")
    print(f"Outputs: {result.outputs}")
    print(f"Insights: {result.insights}")
else:
    print(f"Plan failed with errors: {result.failed_steps}")
```

## Execution Flow

1. **Plan Analysis**: The orchestrator analyzes the execution plan and groups steps by dependency level
2. **Level Execution**: Each level is executed sequentially
3. **Parallel Execution**: Within each level, independent steps run in parallel using `asyncio.gather`
4. **State Updates**: Results are stored in the execution context with thread-safe locks
5. **Error Handling**: Failed steps are tracked but don't block other steps
6. **Streaming**: Events are emitted in real-time for UI updates

## Execution Levels Example

Given the plan above, the orchestrator creates these execution levels:

```
Level 0: [step1]                    # Get datasets
Level 1: [step2, step3]             # Sentiment + Topic (parallel)
Level 2: [step4]                    # Synthesis
```

## Event Types

The orchestrator emits the following events:

- `plan_start`: Plan execution started
- `plan_complete`: Plan execution completed successfully
- `plan_error`: Plan execution failed
- `parallel_execution_start`: Parallel execution batch started
- `parallel_execution_complete`: Parallel execution batch completed
- `agent_step_start`: Individual agent step started
- `agent_step_complete`: Individual agent step completed
- `agent_step_error`: Individual agent step failed
- `content`: Content chunk for streaming response

## Error Handling

The orchestrator implements robust error handling:

1. **Retry Logic**: Failed steps are retried up to `max_retries` times with exponential backoff
2. **Graceful Degradation**: Failed steps don't block other independent steps
3. **Error Tracking**: All failures are logged in `context.failed_steps`
4. **Partial Results**: Even if some steps fail, successful results are returned

## Thread Safety

The orchestrator uses `asyncio.Lock` to ensure thread-safe updates to the execution context:

```python
async with context.lock:
    context.agent_outputs[step_id] = result
    context.completed_steps.add(step_id)
```

## Testing

Comprehensive unit tests are available in `backend/tests/unit/test_workflow_orchestrator.py`:

```bash
pytest tests/unit/test_workflow_orchestrator.py -v
```

## Next Steps

The orchestrator is ready to integrate with:
- Coordinator Agent (task 4)
- Planner Agent (task 5)
- Data Retrieval Agent (task 6)
- Analysis Agents (tasks 7-10)
- Synthesis Agent (task 11)
- Visualization Agent (task 12)
