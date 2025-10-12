# Orchestrator & Agno Team Examples

This directory contains example scripts for testing the orchestrator service and Agno team functionality.

## Prerequisites

1. Ensure you have the required environment variables set:
   ```bash
   export OPENROUTER_API_KEY="your_key_here"
   ```

2. Install dependencies (from backend directory):
   ```bash
   uv sync
   ```

## Available Examples

### 1. Simple Agno Team Test (`test_agno_team_simple.py`)

**Recommended for initial testing** - Tests basic Agno Team streaming without the full orchestrator setup.

```bash
cd backend
python -m examples.test_agno_team_simple
```

**What it does:**
- Creates a simple team with one agent
- Sends a test query
- Streams the response in real-time
- Shows `TeamRunContent` events

**Expected output:**
```
🚀 Testing Agno Team Streaming

📦 Creating OpenRouter model...
✅ Model: anthropic/claude-3.5-sonnet

🤖 Creating agent...
👥 Creating team with streaming...

💬 Query: Explain what product analytics is in 2 sentences.

============================================================

🔄 Streaming Response:

Product analytics is the process of collecting and analyzing data about how users interact with a product...

============================================================
✅ Streaming complete!
📊 Chunks received: 15
📝 Total length: 245 characters
```

### 2. Full Orchestrator Test (`test_orchestrator.py`)

Tests the complete orchestrator service with all agents and tools.

```bash
cd backend
python -m examples.test_orchestrator
```

**What it does:**
- Initializes the full orchestrator with all 4 agents
- Registers all tools (query planner, RAG, web search, analytics, NLP, visualization, citations)
- Processes a test query through the multi-agent team
- Shows status updates and streaming content
- Displays execution tree updates

**Expected output:**
```
🚀 Starting Orchestrator Test

📦 Initializing orchestrator...
✅ Orchestrator initialized successfully

💬 Test Query: What are the top 3 features customers are requesting?

============================================================

🔄 Streaming Response:

📊 Status: [starting] Initializing...
📊 Status: [context_ready] Analyzing query...

Based on the analysis of customer feedback...
[streaming content here]

============================================================
✅ Response Complete!
📝 Message ID: abc-123
📅 Timestamp: 2025-10-12T00:00:00
🤖 Model: anthropic/claude-3.5-sonnet
🔧 Provider: agno_team
```

## Troubleshooting

### "OPENROUTER_API_KEY not configured"
Make sure you have the API key in your environment:
```bash
export OPENROUTER_API_KEY="your_key_here"
```

Or add it to your `.env` file in the backend directory.

### "Failed to initialize orchestrator"
Check your database connection settings if using the full orchestrator test. The simple test doesn't require a database.

### Import errors
Make sure you're running from the backend directory:
```bash
cd backend
python -m examples.test_agno_team_simple
```

## Testing with Database

To test with database integration (for LLM call logging and chat history), modify the scripts to pass a database session:

```python
from app.database.session import get_session

async with get_session() as db:
    async for update in orchestrator.process_message_stream(
        request=request,
        user_id="test_user",
        db=db  # Pass the db session
    ):
        # Handle updates...
```

## Adding Your Own Tests

Create a new script following this pattern:

```python
"""Your test script description."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# Your imports here

async def main():
    # Your test code here
    pass

if __name__ == "__main__":
    asyncio.run(main())
```

Then run it:
```bash
python -m examples.your_script_name
```

