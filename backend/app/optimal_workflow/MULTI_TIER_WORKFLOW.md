# Multi-Tier Workflow System

## Overview

The workflow system now intelligently routes queries to one of three workflows based on complexity, optimizing both cost and latency:

1. **Simple Workflow** (gpt-5-nano) - For general queries and casual conversation
2. **Medium Workflow** (gpt-5-mini) - For follow-up questions using conversation history
3. **Complex Workflow** (full pipeline) - For queries requiring data retrieval and deep analysis

## Architecture

```
User Query → Query Classifier → Route to Appropriate Workflow
                                    ↓
                    ┌───────────────┴───────────────┐
                    ↓               ↓               ↓
              Simple          Medium           Complex
           (gpt-5-nano)    (gpt-5-mini)    (Full Pipeline)
                    ↓               ↓               ↓
                  Response        Response        Response
```

## Components

### 1. Query Classifier (`query_classifier.py`)

- Uses **gpt-5-nano** for fast classification (cost-effective)
- Analyzes query complexity and context
- Considers conversation history to detect follow-ups
- Returns: `QueryComplexity.SIMPLE`, `MEDIUM`, or `COMPLEX`

### 2. Simple Workflow (`simple_workflow.py`)

**When Used:**
- Greetings: "Hello", "How are you?"
- General knowledge: "Who is Taylor Swift?", "What is AI?"
- Casual conversation: "Thanks", "Goodbye"
- Non-data questions

**Characteristics:**
- **Model:** gpt-5-nano
- **Speed:** Very fast (~1-2 seconds)
- **Cost:** Minimal
- **Features:** 
  - No data retrieval
  - No conversation history
  - Conversational tone
  - Markdown formatted responses

### 3. Medium Workflow (`medium_workflow.py`)

**When Used:**
- Follow-up questions: "Can you explain that more?"
- Clarifications: "What did you mean by X?"
- References to previous conversation: "Tell me more about the previous point"
- Questions answerable with context

**Characteristics:**
- **Model:** gpt-5-mini
- **Speed:** Fast (~2-4 seconds)
- **Cost:** Low
- **Features:**
  - Uses last 10 messages (5 exchanges) for context
  - Context-aware responses
  - References previous messages
  - Markdown formatted responses

### 4. Complex Workflow (`workflow.py`)

**When Used:**
- Product analysis: "What are the product gaps for Netflix?"
- Data queries: "Show me sentiment trends"
- Company analytics: "Analyze reviews for Company X"
- Questions requiring data retrieval

**Characteristics:**
- **Model:** Various (as configured in workflow)
- **Speed:** Slower (~10-30 seconds depending on query)
- **Cost:** Higher
- **Features:**
  - Full multi-agent pipeline
  - Data retrieval from database
  - NLP analysis
  - Complex reasoning
  - Comprehensive reports

## Usage

### From Chat API

The workflow routing is automatic. Just call the chat endpoint:

```python
POST /api/v1/chat/stream
{
    "message": "Your query here",
    "session_id": "optional-session-id"
}
```

The system will:
1. Retrieve conversation history from the session
2. Classify the query
3. Route to appropriate workflow
4. Return streaming response

### Direct Usage

```python
from app.optimal_workflow.main import run_workflow

# Automatic routing based on query complexity
result = await run_workflow(
    query="How are you?",
    user_id="user_123",
    session_id="session_456",
    conversation_history=[
        {"role": "user", "content": "Previous message"},
        {"role": "assistant", "content": "Previous response"}
    ]
)
```

### Streaming Usage

```python
from app.optimal_workflow.main import run_workflow_streaming

async for event in run_workflow_streaming(
    query="Your query",
    user_id="user_123",
    session_id="session_456",
    conversation_history=history
):
    if event["type"] == "workflow_routed":
        print(f"Routed to {event['complexity']} workflow")
    elif event["type"] == "content":
        print(event["data"]["content"], end="")
```

## Event Types

### New Events

- **`workflow_routed`**: Emitted after classification
  ```json
  {
    "type": "workflow_routed",
    "complexity": "simple|medium|complex",
    "reasoning": "Brief explanation",
    "session_id": "session_id"
  }
  ```

### Workflow-Specific Events

- **Simple/Medium Workflows:**
  - `step_start`: Response generation started
  - `step_complete`: Response generated
  - `step_error`: Error occurred

- **Complex Workflow:**
  - All existing step events (query analysis, data retrieval, etc.)

## Configuration

### Model Configuration

Edit `app/optimal_workflow/agents/base.py`:

```python
def get_llm(model: str = None) -> OpenAI:
    model_name = model or settings.default_model
    # ...
```

### Classification Tuning

Edit `app/optimal_workflow/query_classifier.py` to adjust classification logic:

- Add/modify examples in the prompt
- Adjust classification criteria
- Change history window size

### Workflow Tuning

Each workflow can be independently configured:

**Simple:** Edit `simple_workflow.py`
- Adjust temperature for more/less creative responses
- Modify system prompt for different tone
- Change max_tokens limit

**Medium:** Edit `medium_workflow.py`
- Adjust history window (default: last 10 messages)
- Modify context formatting
- Tune temperature and max_tokens

**Complex:** Edit `workflow.py`
- Configure agents and steps
- Adjust timeout settings
- Modify data retrieval logic

## Benefits

### Performance
- **Simple queries:** 5-10x faster (1-2s vs 10-30s)
- **Medium queries:** 3-5x faster (2-4s vs 10-30s)
- **Complex queries:** Same performance, but only when needed

### Cost Optimization
- **Simple queries:** ~90% cost reduction (gpt-5-nano vs full pipeline)
- **Medium queries:** ~70% cost reduction (gpt-5-mini vs full pipeline)
- **Complex queries:** Cost justified by comprehensive analysis

### User Experience
- Instant responses for greetings and simple questions
- Fast context-aware follow-ups
- Comprehensive analysis when data is needed
- Smooth streaming with progress indicators

## Testing

### Test Different Complexities

```python
# Test simple
result = await run_workflow("Hello, how are you?")

# Test medium (requires history)
result = await run_workflow(
    "Tell me more about that",
    conversation_history=[
        {"role": "user", "content": "What is AI?"},
        {"role": "assistant", "content": "AI is..."}
    ]
)

# Test complex
result = await run_workflow("Analyze product gaps for Netflix")
```

### Monitor Classification

Check logs for classification decisions:

```
📊 Query classified as: SIMPLE
   └─ Reasoning: Greeting message, no data required
```

## Troubleshooting

### Query Misclassified

If queries are being routed incorrectly:

1. Check the classification prompt in `query_classifier.py`
2. Add more examples to the prompt
3. Adjust classification logic
4. Consider context window size

### Performance Issues

- **Simple workflow too slow:** Check gpt-5-nano availability
- **Medium workflow not using history:** Verify history is being passed
- **Complex workflow not triggering:** Check classification criteria

### Missing Context

If medium workflow isn't using context:

1. Verify conversation history is being retrieved in `workflow_orchestrator_service.py`
2. Check session_id is being passed correctly
3. Verify database has message history

## Future Enhancements

- [ ] Add caching for repeated simple queries
- [ ] Implement query complexity confidence scores
- [ ] Add user feedback on routing decisions
- [ ] Create analytics dashboard for workflow distribution
- [ ] Add ability to force specific workflow via API
- [ ] Implement adaptive routing based on usage patterns

