# Running Tree Workflow Tests

Quick guide to test each framework implementation.

## Prerequisites

1. **Environment Setup**:
   ```bash
   cd backend
   source .venv/bin/activate  # or `.\venv\Scripts\activate` on Windows
   ```

2. **API Keys** (in `.env`):
   ```
   OPENROUTER_API_KEY=sk-or-v1-...     # For Agno
   OPENAI_API_KEY=sk-...                # For OpenAI and Crew AI
   ```

## Test Commands

### 1. Agno Tree Workflow ✅ (Fully Implemented)

**Command:**
```bash
python test_agno_tree.py
```

**What it does:**
- Creates multi-branch workflow with Agno executor
- Tests 2 sample queries
- Shows real-time agent step streaming
- Demonstrates tree structure navigation

**Expected Output:**
```
================================================================================
Testing Agno Tree-Based Workflow
================================================================================

✓ OpenRouter model created

📋 Creating multi-branch workflow...
✓ Created workflow with 2 branches
✓ Registered 6 tools

🌲 Tree Structure:
  Branch: base
    Instruction: Choose a base-level task based on the user's prompt...
    Tools: ['cited_summarizer', 'text_response', 'visualize']
    Child Branches: ['search']
  Branch: search
    Instruction: Choose between querying or aggregating data...
    Tools: ['query_knowledge_base', 'aggregate_data', 'summarize_items']

================================================================================
Query 1/2: What are the top complaints about our product?
================================================================================

🤖 [0] Agent Started: Base
✅ [0] Agent Completed: Base
   Structured Output: {...}

🤖 [1] Agent Started: Search
✅ [1] Agent Completed: Search
   Text Output: Retrieved 10 results...

...
```

**Key Features Demonstrated:**
- ✅ Tree branch navigation
- ✅ Agent step streaming via hooks
- ✅ Structured vs text output handling
- ✅ Real-time progress updates

---

### 2. OpenAI Agent SDK Tree Workflow 🔄 (Example/Conceptual)

**Command:**
```bash
python test_openai_tree.py
```

**What it does:**
- Creates OpenAI Assistant with tree-based instructions
- Demonstrates function calling for tools
- Shows how tree decisions map to OpenAI's agent model
- Polls for tool execution steps

**Expected Output:**
```
================================================================================
Testing OpenAI Agent SDK Tree-Based Workflow
================================================================================

✓ OpenAI client created

📋 Creating assistant with tree workflow...
✓ Created assistant: asst_xxx

================================================================================
Query 1/2: What are the top complaints about our product?
================================================================================

🤖 Assistant thinking...

📍 Step 1: Tool calls required

  → Tool: query_knowledge_base
  🔧 Executing tool: query_knowledge_base
     Arguments: {
        "collection_names": ["reviews"],
        "search_query": "complaints problems issues",
        "search_type": "hybrid"
     }
  ✓ Result: {...}

💬 Assistant Response:
--------------------------------------------------------------------------------
Based on the reviews, the top complaints are:

1. **Slow Performance** - Multiple users reported...
2. **UI Complexity** - Users find the interface...
...
--------------------------------------------------------------------------------

✓ Completed with 1 tool execution steps
```

**Key Features Demonstrated:**
- Function calling with tree-based tools
- Tool execution steps
- Assistant reasoning with tree instructions
- Response synthesis

---

### 3. Crew AI Tree Workflow 🔄 (Example/Conceptual)

**Prerequisites:**
```bash
pip install crewai crewai-tools langchain-openai
```

**Command:**
```bash
python test_crewai_tree.py
```

**What it does:**
- Creates Crew AI agents matching tree branches
- Maps tree structure to hierarchical crew
- Demonstrates sequential task execution
- Shows agent coordination

**Expected Output:**
```
================================================================================
Testing Crew AI Tree-Based Workflow
================================================================================

✓ Crew AI imported successfully

📋 Creating agents with tree workflow...
✓ Created 4 agents (coordinator, search_specialist, visualizer, writer)

================================================================================
Query 1/2: What are the top complaints about our product?
================================================================================

🚀 Starting crew execution...

[Coordinator] Working on task: Analyze this user query...
> Decision: We need to SEARCH the knowledge base...

[Search Specialist] Working on task: Choose search approach...
  🔧 Executing query: complaints problems issues (type: hybrid)
> Using query_knowledge_base to retrieve specific complaints...

[Response Writer] Working on task: Synthesize final response...
> Combining search results into final response...

💬 Final Response:
--------------------------------------------------------------------------------
Based on our analysis of customer reviews, the top complaints are:

1. **Performance Issues** (mentioned in 45% of negative reviews)
   - Slow loading times
   - Frequent crashes

2. **User Interface Complexity** (mentioned in 32%)
...

Sources:
- Review Database (150 reviews analyzed)
- Sentiment Analysis Results
--------------------------------------------------------------------------------

✓ Completed query 1
```

**Key Features Demonstrated:**
- Hierarchical agent coordination
- Tool execution by specialized agents
- Sequential task flow matching tree branches
- Agent backstories providing tree-like instructions

---

## Comparison

| Feature | Agno | OpenAI | Crew AI |
|---------|------|--------|---------|
| **Implementation** | ✅ Complete | 🔄 Example | 🔄 Example |
| **Streaming** | ✅ Pre/Post Hooks | ✅ SSE | ⚠️ Limited |
| **Agent Steps** | ✅ Real-time | ✅ Polled | ✅ Sequential |
| **DB Persistence** | ✅ Automatic | ⚠️ Manual | ⚠️ Manual |
| **Tree Structure** | ✅ Explicit | ⚠️ Instructions | ⚠️ Hierarchy |
| **Tool Chaining** | ✅ Native | ⚠️ Manual | ⚠️ Task-based |

**Legend:**
- ✅ = Fully implemented/supported
- 🔄 = Conceptual example (needs full executor)
- ⚠️ = Requires additional work

---

## Quick Test All

Run all three tests in sequence:

```bash
# Test Agno (fully working)
python test_agno_tree.py

# Test OpenAI (example)
python test_openai_tree.py

# Test Crew AI (example, requires installation)
python test_crewai_tree.py
```

---

## Troubleshooting

**Issue: "OpenRouter API key not configured"**
```bash
# Add to backend/.env
echo "OPENROUTER_API_KEY=sk-or-v1-your-key-here" >> .env
```

**Issue: "OpenAI API key not configured"**
```bash
# Add to backend/.env
echo "OPENAI_API_KEY=sk-your-key-here" >> .env
```

**Issue: "crewai not found"**
```bash
pip install crewai crewai-tools langchain-openai
```

**Issue: Import errors**
```bash
# Make sure you're in the backend directory
cd backend

# Ensure PYTHONPATH includes the backend
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Or run with module syntax
python -m test_agno_tree
```

---

## Next Steps

After testing:

1. **Agno** is production-ready - use `/api/v1/chat/tree/stream` endpoint
2. **OpenAI** - Implement `OpenAITreeExecutor` for full integration
3. **Crew AI** - Implement `CrewAITreeExecutor` for full integration

See `TREE_ARCHITECTURE_README.md` for full documentation.

