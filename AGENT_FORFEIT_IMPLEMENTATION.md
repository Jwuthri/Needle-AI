# Agent Forfeit Mechanism Implementation

## Overview
Implemented a graceful forfeit mechanism that allows agents to admit when they cannot answer a question, providing clear explanations to users instead of failing silently or looping indefinitely.

## Problem Solved
Previously, when agents couldn't answer a question due to:
- Missing data
- Incompatible data formats
- Repeated tool failures
- Questions outside their capabilities

They would either:
- Loop endlessly trying different approaches
- Fail with cryptic error messages
- Return unhelpful responses

## Solution

### 1. Forfeit Tool (`forfeit_tool.py`)
Created a dedicated tool that agents can call to gracefully exit:

```python
async def forfeit_request(
    ctx: Context,
    reason: str,
    attempted_actions: list[str]
) -> Dict[str, Any]:
    """
    Forfeit the current request with clear explanation.
    
    Parameters:
        reason: Clear explanation of why the agent cannot answer
        attempted_actions: List of what was tried before forfeiting
    """
```

**Key Features:**
- Raises `ForfeitException` to stop workflow execution
- Stores forfeit information in context
- Requires clear reason and attempted actions from agent

### 2. Updated All Agents
Added forfeit tool to all 9 agents with specific guidance on when to forfeit:

#### Coordinator Agent
- If specialists repeatedly fail
- If question is outside capabilities

#### Data Discovery Agent
- No datasets available for user
- Required data columns don't exist
- SQL queries repeatedly fail
- Data format incompatible

#### Gap Analysis Agent
- No cluster data available
- Data quality too poor

#### Sentiment Analysis Agent
- No sentiment data available
- Data lacks required text fields

#### Trend Analysis Agent
- No temporal/date data available
- Insufficient data points

#### Clustering Agent
- No embeddings available
- Dataset too small

#### Visualization Agent
- (Already had forfeit capability via error handling)

#### Report Writer Agent
- No analysis results available
- All previous agents failed

#### General Assistant Agent
- Question requires specialized knowledge
- Request outside capabilities

### 3. Workflow Service Integration
Updated `simple_workflow_service.py` to catch and handle `ForfeitException`:

```python
except ForfeitException as forfeit_err:
    forfeit_message = f"""I apologize, but I'm unable to complete this request.

**Reason:** {forfeit_err.reason}

**What I tried:**
- {action1}
- {action2}
...

Please try rephrasing your question or ensure your data contains the necessary information."""
```

**Handling:**
1. Catches `ForfeitException` from workflow
2. Formats user-friendly message with:
   - Clear reason for forfeit
   - List of attempted actions
   - Helpful suggestions
3. Saves forfeit message to database
4. Yields `forfeit` event type for frontend
5. Yields `complete` event with `forfeited: true` flag

### 4. Event Types
Added new event type for streaming:

```typescript
{
  type: "forfeit",
  data: {
    reason: string,
    attempted_actions: string[],
    message: string
  }
}
```

And updated complete event:
```typescript
{
  type: "complete",
  data: {
    ...
    forfeited: boolean,
    metadata: {
      forfeit_reason?: string
    }
  }
}
```

## Example Scenarios

### Scenario 1: Missing Data
**User:** "Show me price trends over time"

**Agent Response:**
```
I apologize, but I'm unable to complete this request.

**Reason:** The dataset doesn't contain pricing information needed to analyze cost trends

**What I tried:**
- Searched for price-related columns in the dataset
- Checked for alternative pricing metrics
- Looked for related financial data

Please try rephrasing your question or ensure your data contains the necessary information.
```

### Scenario 2: Insufficient Data Points
**User:** "Analyze trends in my data"

**Agent Response:**
```
I apologize, but I'm unable to complete this request.

**Reason:** Insufficient data points for meaningful trend analysis (only 3 records found, need at least 10)

**What I tried:**
- Loaded available dataset
- Checked for temporal columns
- Attempted basic trend calculation

Please try rephrasing your question or ensure your data contains the necessary information.
```

### Scenario 3: No Datasets Available
**User:** "Analyze my customer reviews"

**Agent Response:**
```
I apologize, but I'm unable to complete this request.

**Reason:** No datasets available for your account

**What I tried:**
- Searched for user datasets
- Checked for uploaded files
- Looked for default data sources

Please try rephrasing your question or ensure your data contains the necessary information.
```

## Files Modified

1. **`backend/app/core/llm/simple_workflow/tools/forfeit_tool.py`** (NEW)
   - Created forfeit tool and ForfeitException

2. **`backend/app/core/llm/simple_workflow/agents/coordinator_agent.py`**
   - Added forfeit tool
   - Updated system prompt with forfeit guidance

3. **`backend/app/core/llm/simple_workflow/agents/data_discovery_agent.py`**
   - Added forfeit tool
   - Specified when to forfeit (no datasets, SQL failures, etc.)

4. **`backend/app/core/llm/simple_workflow/agents/gap_analysis_agent.py`**
   - Added forfeit tool
   - Specified forfeit conditions

5. **`backend/app/core/llm/simple_workflow/agents/sentiment_analysis_agent.py`**
   - Added forfeit tool
   - Specified forfeit conditions

6. **`backend/app/core/llm/simple_workflow/agents/trend_analysis_agent.py`**
   - Added forfeit tool
   - Specified forfeit conditions

7. **`backend/app/core/llm/simple_workflow/agents/clustering_agent.py`**
   - Added forfeit tool
   - Specified forfeit conditions

8. **`backend/app/core/llm/simple_workflow/agents/report_writer_agent.py`**
   - Added forfeit tool
   - Specified forfeit conditions

9. **`backend/app/core/llm/simple_workflow/agents/general_assistant_agent.py`**
   - Added forfeit tool
   - Specified forfeit conditions

10. **`backend/app/services/simple_workflow_service.py`**
    - Import ForfeitException
    - Catch and handle forfeit gracefully
    - Format user-friendly messages
    - Yield forfeit events

## Benefits

1. **Better User Experience**
   - Clear explanations instead of cryptic errors
   - Transparency about what was attempted
   - Actionable suggestions

2. **Reduced Resource Usage**
   - Agents stop early instead of looping
   - No wasted API calls
   - Faster response times

3. **Improved Debugging**
   - Forfeit reasons logged
   - Attempted actions tracked
   - Easier to identify data issues

4. **Honest Communication**
   - Agents admit limitations
   - Users understand constraints
   - Builds trust

## Frontend Integration (TODO)

The frontend should handle the `forfeit` event type:

```typescript
if (event.type === 'forfeit') {
  // Show forfeit message with special styling
  // Maybe add icon indicating forfeit
  // Display attempted actions in expandable section
}
```

## Testing

Test forfeit mechanism with:
1. Questions about non-existent data
2. Requests requiring missing columns
3. Trend analysis with insufficient data points
4. Clustering with no embeddings
5. Sentiment analysis with no text fields

The agents should forfeit gracefully with clear explanations.

