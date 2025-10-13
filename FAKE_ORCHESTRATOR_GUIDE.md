# Fake Orchestrator Guide

## Overview

The fake orchestrator is a testing/development tool that simulates multi-agent execution without requiring actual Agno or n8n integration. It generates realistic-looking agent steps with proper streaming and database storage.

## When to Use

- **Development**: Test frontend agent step display without backend dependencies
- **Demo Mode**: Show the UI working perfectly for presentations
- **Debugging**: Isolate frontend issues from backend AI orchestration problems
- **CI/CD**: Run integration tests without external AI services

## How It Works

The fake orchestrator:
1. Receives user messages from the frontend
2. Simulates 4 agents running sequentially:
   - `query-planner`
   - `research-agent`
   - `data-analyzer`
   - `response-writer`
3. Each agent:
   - Takes 1-2.5 seconds to "think"
   - Generates either structured (JSON) or unstructured (text) output
   - Emits proper stream events (`agent_step_start`, `agent_step_complete`)
4. Stores all steps in the `chat_message_steps` table
5. Returns a realistic final answer based on the query type

## Configuration

### Enable Fake Orchestrator (Default)

```bash
export USE_FAKE_ORCHESTRATOR=true
```

Or in your `.env` file:
```
USE_FAKE_ORCHESTRATOR=true
```

### Disable Fake Orchestrator (Use Real Agno)

```bash
export USE_FAKE_ORCHESTRATOR=false
```

Or in your `.env` file:
```
USE_FAKE_ORCHESTRATOR=false
```

## Response Types

The fake orchestrator detects query intent and returns different response types:

### Default Response
General queries get a generic analysis response with:
- Overview section
- Key findings
- Recommendations
- Conclusion

### Competitor Analysis
Queries containing "competitor" get:
- Top competitors list with market share
- Strengths/weaknesses analysis
- Competitive positioning
- Strategic recommendations

### Product Gap Analysis
Queries containing "gap", "missing", or "feature" get:
- Critical missing features
- Performance issues
- User experience gaps
- Prioritized recommendations

## Frontend Integration

The frontend automatically works with the fake orchestrator because it uses the same stream event format:

- `agent_step_start` - Agent begins work
- `agent_step_content` - Agent outputs content (for text)
- `agent_step_complete` - Agent finishes with final output
- `content` - Streaming response chunks
- `complete` - Final message with metadata

## Database Storage

All fake agent steps are stored in the `chat_message_steps` table with:
- `agent_name` - The simulated agent name
- `step_order` - Sequential step number (0-indexed)
- `tool_call` - Structured output (JSONB) if applicable
- `prediction` - Text output if not structured
- `message_id` - Links to the assistant's chat message

## Testing the Frontend

1. **Start the backend with fake orchestrator enabled:**
   ```bash
   cd backend
   export USE_FAKE_ORCHESTRATOR=true
   python -m uvicorn app.main:app --reload
   ```

2. **Start the frontend:**
   ```bash
   cd frontend
   npm run dev
   ```

3. **Test different query types:**
   - "What are the main features?" → Default response
   - "Which competitors are mentioned most?" → Competitor analysis
   - "What product gaps exist?" → Gap analysis

4. **Verify the UI shows:**
   - ✅ Purple "Agent Execution Pipeline" box during streaming
   - ✅ Real-time agent step updates with step numbers
   - ✅ Collapsible execution steps above each answer
   - ✅ Step details with timestamps and copy buttons
   - ✅ Steps persist after page reload

## Switching Back to Real Orchestrator

When your Agno/n8n integration is fixed:

1. Set environment variable:
   ```bash
   export USE_FAKE_ORCHESTRATOR=false
   ```

2. Restart the backend

3. The frontend will work exactly the same way!

## File Locations

- **Fake Orchestrator**: `backend/app/services/fake_orchestrator_service.py`
- **Orchestrator Switch**: `backend/app/dependencies.py` (line ~56)
- **Chat API**: `backend/app/api/v1/chat.py` (uses same interface)

## Customization

To customize the fake agents or responses, edit:
```python
# backend/app/services/fake_orchestrator_service.py

FAKE_AGENTS = [
    "your-agent-1",
    "your-agent-2",
    # ... add more
]

FAKE_RESPONSES = {
    "your_query_type": """Your fake response here..."""
}
```

## Benefits

✅ **No Dependencies**: Works without Agno, n8n, or any AI services  
✅ **Fast Development**: Test UI without waiting for real AI  
✅ **Reliable**: No API rate limits or service outages  
✅ **Realistic**: Generates authentic-looking data with timing  
✅ **Database Integration**: Properly stores steps for testing persistence  

---

**Default Mode**: The fake orchestrator is **enabled by default** so you can start testing immediately!

