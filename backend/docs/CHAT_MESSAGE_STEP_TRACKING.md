# Chat Message Step Tracking Implementation

## Overview

This document describes the comprehensive Chat Message Step tracking system implemented across all workflows in the Product Review Analysis platform. The system provides complete visibility into agent execution, enabling debugging, auditing, and user transparency.

## Architecture

### Database Model

The `ChatMessageStep` model tracks individual agent execution steps:

```python
class ChatMessageStep(Base):
    id: str  # UUID
    message_id: str  # FK to chat_messages
    agent_name: str  # Name of the agent
    step_order: int  # Sequential order (0-indexed)
    
    # The "Thinking" part
    thought: Optional[str]  # Agent's reasoning before action
    
    # The "Action" or "Output" part (one populated)
    tool_call: Optional[Dict]  # Tool calls with parameters and results
    structured_output: Optional[Dict]  # Structured data (Pydantic models)
    prediction: Optional[str]  # Text outputs
    
    created_at: datetime
```

### Key Principles

1. **Immediate Persistence**: Steps are saved to the database immediately after execution
2. **Comprehensive Tracking**: Every agent action is tracked, including thoughts and tool calls
3. **Sequential Ordering**: Steps are numbered sequentially to enable flow reconstruction
4. **Separation of Concerns**: Thoughts (reasoning) are separate from actions (outputs)

## Implementation Across Workflows

### 1. Simple Workflow (gpt-5-nano)

**Tracks:**
- Workflow start with classification reasoning
- Final response generation

**Example:**
```python
# Step 0: Workflow Start
{
    "agent_name": "SimpleWorkflow",
    "step_order": 0,
    "thought": "Query classified as simple - generating direct response using gpt-5-nano",
    "structured_output": {
        "workflow_type": "simple",
        "model": "gpt-5-nano"
    }
}

# Step 1: Response Complete
{
    "agent_name": "SimpleWorkflow",
    "step_order": 1,
    "prediction": "Hello! How can I help you today?",
    "structured_output": {
        "status": "completed",
        "response_length": 32,
        "model": "gpt-5-nano"
    }
}
```

### 2. Medium Workflow (gpt-5-mini)

**Tracks:**
- Workflow start with conversation history context
- Final response generation with history usage

**Example:**
```python
# Step 0: Workflow Start
{
    "agent_name": "MediumWorkflow",
    "step_order": 0,
    "thought": "Query classified as medium complexity - using conversation history with gpt-5-mini",
    "structured_output": {
        "workflow_type": "medium",
        "model": "gpt-5-mini",
        "history_messages": 4
    }
}

# Step 1: Response Complete
{
    "agent_name": "MediumWorkflow",
    "step_order": 1,
    "prediction": "Based on our previous discussion...",
    "structured_output": {
        "status": "completed",
        "response_length": 450,
        "model": "gpt-5-mini",
        "history_used": 4
    }
}
```

### 3. Complex Workflow (ProductGapWorkflow)

**Tracks:**
- Query analysis
- Format detection
- Retrieval planning
- Data retrieval with tool calls
- NLP analysis
- Answer generation

**Example:**
```python
# Step 0: Query Analysis
{
    "agent_name": "Query Analyzer",
    "step_order": 0,
    "thought": "Analyzing query to determine data needs and complexity",
    "structured_output": {
        "needs_data_retrieval": true,
        "query_type": "product_gaps",
        "complexity": "high"
    }
}

# Step 1: Format Detection
{
    "agent_name": "Format Detector",
    "step_order": 1,
    "thought": "Determining optimal response format",
    "structured_output": {
        "format": "markdown_with_visualizations",
        "requires_charts": true
    }
}

# Step 2: Retrieval Planning
{
    "agent_name": "Retrieval Planner",
    "step_order": 2,
    "thought": "Planning data retrieval strategy based on query requirements",
    "structured_output": {
        "tables_needed": ["user_123_reviews"],
        "filters": {"rating": "<=2"},
        "analysis_types": ["topic_modeling", "sentiment"]
    }
}

# Step 3: Data Retrieval (Tool Call)
{
    "agent_name": "DataRetrieval",
    "step_order": 3,
    "thought": "Querying reviews with filters: {'rating': '<=2'}",
    "tool_call": {
        "tool_name": "query_reviews",
        "parameters": {
            "user_id": "user_123",
            "rating_filter": "<=2",
            "limit": 1000
        },
        "result": {
            "review_count": 45
        }
    }
}

# Step 4: NLP Analysis
{
    "agent_name": "NLP Analyzer",
    "step_order": 4,
    "thought": "Analyzing 45 reviews for topics and sentiment",
    "structured_output": {
        "topics_identified": 3,
        "sentiment_scores": {...},
        "insights_generated": 5
    }
}

# Step 5: Answer Generation
{
    "agent_name": "Answer Generator",
    "step_order": 5,
    "thought": "Synthesizing insights into comprehensive response",
    "prediction": "Based on analysis of 45 negative reviews...",
    "structured_output": {
        "response_length": 1250,
        "visualizations_included": 2,
        "insights_used": 5
    }
}
```

### 4. Product Review Analysis Workflow (Multi-Agent)

**Tracks:**
- Coordinator classification
- Planner decisions (iterative ReAct)
- Data retrieval tool calls
- Analysis agent executions (Sentiment, Topic, Anomaly, Summary)
- Synthesis with visualization embedding

**Example:**
```python
# Step 0: Coordinator
{
    "agent_name": "Coordinator",
    "step_order": 0,
    "thought": "Analyzing query complexity and determining routing strategy",
    "structured_output": {
        "complexity": "complex",
        "needs_data": true,
        "route": "planner"
    }
}

# Step 1: Planner (First Action)
{
    "agent_name": "Planner",
    "step_order": 1,
    "thought": "Need to understand available data first. Will retrieve user datasets with EDA metadata.",
    "structured_output": {
        "action_id": "action_1",
        "agent_type": "data_retrieval",
        "action": "get_user_datasets_with_eda",
        "is_final": false
    }
}

# Step 2: Data Retrieval (Tool Call)
{
    "agent_name": "DataRetrieval",
    "step_order": 2,
    "thought": "Retrieving user datasets with EDA metadata to understand available data",
    "tool_call": {
        "tool_name": "get_user_datasets_with_eda",
        "parameters": {"user_id": "user_123"},
        "result": {"dataset_count": 1}
    }
}

# Step 3: Planner (Second Action)
{
    "agent_name": "Planner",
    "step_order": 3,
    "thought": "Found 45 reviews. Will run topic modeling on negative reviews to identify gaps.",
    "structured_output": {
        "action_id": "action_2",
        "agent_type": "topic_modeling",
        "parameters": {"rating_filter": "<=2", "num_topics": 5},
        "is_final": false
    }
}

# Step 4: Topic Modeling
{
    "agent_name": "TopicModeling",
    "step_order": 4,
    "thought": "Identifying topics in 18 negative reviews",
    "structured_output": {
        "insights_generated": 3
    }
}

# Step 5: Planner (Final Action)
{
    "agent_name": "Planner",
    "step_order": 5,
    "thought": "Have sufficient insights. Proceeding to synthesis.",
    "structured_output": {
        "action_id": "action_3",
        "agent_type": "synthesis",
        "is_final": true
    }
}

# Step 6: Synthesis
{
    "agent_name": "Synthesis",
    "step_order": 6,
    "thought": "Synthesizing insights into coherent narrative response",
    "structured_output": {
        "insights_used": ["insight_1", "insight_2", "insight_3"],
        "insights_omitted": [],
        "response_length": 1800,
        "sections": ["Executive Summary", "Top 3 Gaps", "Recommendations"]
    }
}
```

## Helper Methods

### `_track_step_in_db`

Core method for tracking steps across all workflows:

```python
async def _track_step_in_db(
    self,
    agent_name: str,
    step_order: int,
    content: Any = None,
    is_structured: bool = False,
    thought: Optional[str] = None,
    tool_call: Optional[Dict[str, Any]] = None
):
    """
    Track workflow step in database immediately.
    
    Handles:
    - Thoughts (reasoning traces)
    - Tool calls (with parameters and results)
    - Structured outputs (dicts, Pydantic models)
    - Text predictions (LLM responses)
    """
```

### `_track_tool_call`

Specialized method for tracking tool calls (ProductReviewAnalysisWorkflow):

```python
async def _track_tool_call(
    self,
    agent_name: str,
    tool_name: str,
    parameters: Dict[str, Any],
    result: Any,
    thought: Optional[str] = None
):
    """
    Track a tool call as a workflow step.
    
    Emits streaming events and saves to database.
    """
```

## Streaming Events

Steps are also emitted as streaming events for real-time UI updates:

```python
# Step Start
{
    "type": "agent_step_start",
    "data": {
        "agent_name": "Planner",
        "step_id": "uuid-here",
        "timestamp": "2025-11-12T10:30:00Z",
        "step_order": 1
    }
}

# Step Complete
{
    "type": "agent_step_complete",
    "data": {
        "step_id": "uuid-here",
        "agent_name": "Planner",
        "content": {...},
        "is_structured": true,
        "step_order": 1
    }
}

# Tool Call
{
    "type": "tool_call",
    "data": {
        "agent_name": "DataRetrieval",
        "tool_name": "query_reviews",
        "parameters": {...},
        "step_order": 2
    }
}

# Tool Call Complete
{
    "type": "tool_call_complete",
    "data": {
        "agent_name": "DataRetrieval",
        "tool_name": "query_reviews",
        "step_order": 2
    }
}
```

## API Endpoints

### Get Chat Message Steps

```http
GET /api/v1/chat/steps/{message_id}
```

Returns all steps for a message in chronological order:

```json
{
  "steps": [
    {
      "id": "step-uuid-1",
      "message_id": "msg-123",
      "agent_name": "Coordinator",
      "step_order": 0,
      "thought": "Analyzing query complexity...",
      "structured_output": {...},
      "created_at": "2025-11-12T10:30:00Z"
    },
    {
      "id": "step-uuid-2",
      "message_id": "msg-123",
      "agent_name": "Planner",
      "step_order": 1,
      "thought": "Determining next action...",
      "structured_output": {...},
      "created_at": "2025-11-12T10:30:01Z"
    }
  ]
}
```

## Benefits

1. **Debugging**: Complete visibility into workflow execution for troubleshooting
2. **Auditing**: Full audit trail of all agent actions and decisions
3. **User Transparency**: Users can see how the system arrived at conclusions
4. **Learning**: Historical data for improving agent performance
5. **Monitoring**: Track execution patterns and identify bottlenecks

## Best Practices

1. **Always Track Thoughts**: Include reasoning for every agent action
2. **Immediate Persistence**: Save steps to database immediately, don't batch
3. **Sequential Ordering**: Maintain strict step_order sequence
4. **Meaningful Names**: Use descriptive agent names (e.g., "DataRetrieval" not "Agent1")
5. **Structured Data**: Prefer structured_output over prediction for machine-readable data
6. **Tool Call Details**: Include full parameters and results for tool calls
7. **Error Handling**: Track failed steps with error information

## Future Enhancements

1. **Step Visualization**: Frontend UI to display execution flow as a graph
2. **Performance Metrics**: Track execution time per step
3. **Feedback Integration**: Link user feedback to specific steps
4. **Replay Capability**: Ability to replay workflow execution from steps
5. **Step Comparison**: Compare execution paths for similar queries
