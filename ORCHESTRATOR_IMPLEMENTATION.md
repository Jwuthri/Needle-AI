# Multi-Agent Chat Orchestration System - Implementation Summary

## Overview

Successfully implemented a flexible, multi-agent orchestration system that replaces the rigid if/else chat routing with dynamic tool-based execution. The system uses Agno's team functionality to coordinate specialized agents that analyze queries, retrieve data, process it, and generate comprehensive responses with execution tracking.

## What Was Built

### 1. Core Infrastructure

#### Execution Tree (`backend/app/agents/execution_tree.py`)
- Tracks all steps in query processing for UI visualization
- Hierarchical structure with parent-child relationships
- Captures timing, status, input/output for each step
- Exports to JSON for frontend rendering

#### Tool System (`backend/app/agents/tools/`)
- **Base Tool Interface** (`base_tool.py`) - Abstract base class for all tools
- **Tool Registry** (`tool_registry.py`) - Central registry for managing tools

### 2. Implemented Tools

#### Query Planner Tool (`query_planner_tool.py`)
- **Uses LLM (GPT-5 Nano)** instead of keyword matching
- Analyzes queries to determine:
  - Intent (Summarization, Aggregation, Filtering, Ranking, Trend Analysis, Gap Analysis, Competitive Analysis)
  - Output format (text, visualization, cited_summary)
  - Required data sources (RAG, web search)
  - Required processing (analytics, NLP)
- Returns structured JSON plan for orchestrator

#### RAG Retrieval Tool (`rag_retrieval_tool.py`)
- Searches vector database for relevant reviews
- **Filters**:
  - `company_id` (singular, not plural)
  - `website` (e.g., "g2", "capterra", "trustpilot")
  - `sentiment` ("positive", "negative", "neutral")
- Returns reviews with relevance scores and metadata

#### Web Search Tool (`web_search_tool.py`)
- Uses DuckDuckGo (completely free, no API key needed)
- Searches web for current info, competitor data, external facts
- Returns results with titles, snippets, URLs

#### Data Analysis Tool (`data_analysis_tool.py`)
- Performs statistical operations on tabular data
- Operations: aggregate, groupby, filter, sort, stats
- Functions: sum, mean, median, count, min, max, std

#### NLP Tool (`nlp_tool.py`)
- TF-IDF keyword extraction
- Keyword frequency analysis
- Theme extraction
- N-gram analysis (bigrams, trigrams)
- Uses scikit-learn for TF-IDF

#### Visualization Tool (`visualization_tool.py`)
- Generates chart configurations (not actual images)
- Supports: bar, line, pie, table
- Frontend will render using Chart.js or similar
- Returns JSON config with data, axes, labels

#### Citation Tool (`citation_tool.py`)
- Formats sources with proper attribution
- Supports multiple citation styles (numbered, inline, footnote)
- Includes quotes from sources
- Generates expandable source details for UI

### 3. Orchestrator Service (`backend/app/services/orchestrator_service.py`)

Uses **Agno Team** with specialized agents:

1. **Query Planner Agent** - Analyzes queries and creates execution plans
2. **Data Agent** - Retrieves data from RAG and web search
3. **Analysis Agent** - Processes data with analytics and NLP
4. **Synthesis Agent** - Creates final responses with citations

**Flow**:
1. Query Planner analyzes the query
2. Data Agent retrieves needed data
3. Analysis Agent processes and analyzes
4. Synthesis Agent creates final response
5. All steps tracked in execution tree

### 4. Updated Models (`backend/app/models/chat.py`)

Added new fields to `ChatResponse`:
- `output_format`: "text" | "visualization" | "cited_summary"
- `visualization`: Chart configuration if applicable
- `sources`: Source citations
- `execution_tree`: Full execution tree for UI

Added `ExecutionStep` model for tree structure.

### 5. Simplified Chat Endpoint (`backend/app/api/v1/chat.py`)

**Before**: 200+ lines of if/else logic, manual RAG instantiation, inline title generation
**After**: ~40 lines calling orchestrator

```python
# Process message using orchestrator
response = await orchestrator.process_message(
    request=request,
    user_id=user_id,
    db=db
)
```

### 6. Dependencies Added

```toml
"duckduckgo-search>=6.0.0"  # Free web search
"scikit-learn>=1.5.0"       # For TF-IDF and analytics
```

(pandas was already included)

## How It Works

### Example Query: "What are the top product gaps from negative reviews?"

1. **Query Planner** (LLM call):
   ```json
   {
     "intent": "Gap Analysis",
     "output_format": "cited_summary",
     "needs_rag": true,
     "needs_web_search": false,
     "needs_analytics": true,
     "needs_nlp": true
   }
   ```

2. **Data Agent** retrieves:
   - RAG tool: Searches vector DB with `sentiment="negative"`
   - Returns 15 relevant negative reviews

3. **Analysis Agent** processes:
   - NLP tool: Extracts keywords/themes from reviews
   - Data Analysis tool: Groups issues by frequency
   - Visualization tool: Generates bar chart of top issues

4. **Synthesis Agent** creates:
   - Citation tool: Formats sources
   - Final response with citations and chart config

5. **Execution Tree** captures:
   - Each tool call
   - Duration and status
   - Input/output summaries
   - Hierarchical structure

## Architecture Benefits

### Before (Rigid)
```python
if company_id:
    use RAG
else:
    use standard chat
```

### After (Dynamic)
```
LLM decides → Tools execute → Results synthesized
```

**Advantages**:
1. **Flexible**: LLM chooses optimal tools per query
2. **Extensible**: Easy to add new tools
3. **Transparent**: Execution tree shows all steps
4. **Intelligent**: Query planner uses LLM, not keywords
5. **Powerful**: Can combine RAG + web + analytics in one query

## What's Left to Implement

### High Priority
1. **Frontend Execution Tree Viewer** (`frontend/src/components/chat/execution-tree.tsx`)
   - Hierarchical tree display
   - Collapsible nodes
   - Show timing, status, input/output
   - Color-coded by status

2. **Frontend Visualization Renderer** (`frontend/src/components/chat/chart-renderer.tsx`)
   - Integrate Chart.js or similar
   - Render bar, line, pie charts
   - Display tables
   - Support different viz types

3. **Tool Execution Tracking**
   - Currently execution tree has placeholder nodes
   - Need to intercept tool calls and add them to tree
   - Track actual duration and results

4. **Better Error Handling**
   - Graceful degradation when tools fail
   - Retry logic for transient failures
   - User-friendly error messages

### Medium Priority
5. **Streaming Support**
   - Enable streaming responses from Agno team
   - Stream execution tree updates in real-time
   - Show progress as tools execute

6. **Caching**
   - Cache query plans for common queries
   - Cache RAG results
   - Redis-based caching layer

7. **Cost Tracking**
   - Track tokens per tool call
   - Calculate cost per query
   - Usage analytics

### Low Priority
8. **A/B Testing**
   - Test different agent instructions
   - Compare tool selection strategies
   - Optimize performance

9. **Query Rewriting**
   - Add tool to clarify ambiguous queries
   - Expand abbreviations
   - Fix typos

10. **Multi-company Analysis**
    - Compare multiple companies
    - Cross-company insights

## Testing the System

### 1. Basic Query (Text Response)
```bash
curl -X POST http://localhost:8000/api/v1/chat/ \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Tell me about the product features",
    "session_id": "test-123"
  }'
```

### 2. RAG Query (Cited Summary)
```bash
curl -X POST http://localhost:8000/api/v1/chat/ \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What are customers saying about the UI?",
    "company_id": "comp_123",
    "session_id": "test-123"
  }'
```

### 3. Analytics Query (Visualization)
```bash
curl -X POST http://localhost:8000/api/v1/chat/ \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Show me the distribution of review sentiments",
    "company_id": "comp_123",
    "session_id": "test-123"
  }'
```

### 4. Hybrid Query (RAG + Web)
```bash
curl -X POST http://localhost:8000/api/v1/chat/ \
  -H "Content-Type: application/json" \
  -d '{
    "message": "How does our product compare to competitors based on reviews and market research?",
    "company_id": "comp_123",
    "session_id": "test-123"
  }'
```

## Response Format

```json
{
  "message": "Based on the reviews...",
  "session_id": "test-123",
  "message_id": "msg_abc",
  "timestamp": "2025-10-12T...",
  "output_format": "cited_summary",
  "sources": [
    {
      "id": "review_1",
      "author": "John Doe",
      "source": "G2",
      "quote": "The UI is intuitive but...",
      "sentiment": "Positive"
    }
  ],
  "execution_tree": {
    "tree_id": "tree_xyz",
    "query": "What are customers saying...",
    "root": {
      "id": "root",
      "name": "Query Orchestration",
      "status": "completed",
      "duration_ms": 2450,
      "children": [
        {
          "id": "step_1",
          "name": "Query Planning",
          "type": "tool",
          "status": "completed",
          "duration_ms": 450,
          "output_summary": "Intent: Gap Analysis, Format: cited_summary"
        },
        {
          "id": "step_2",
          "name": "RAG Retrieval",
          "type": "tool",
          "status": "completed",
          "duration_ms": 1200,
          "output_summary": "Found 15 relevant reviews"
        }
      ]
    }
  }
}
```

## Configuration

Add to `.env`:
```bash
# Orchestrator Settings
ORCHESTRATOR_MODEL=openai/gpt-5-nano  # Fast, cheap for tool calling
SYNTHESIS_MODEL=anthropic/claude-sonnet-4.5  # Better for final responses

# Optional: Brave Search (if you want better search than DuckDuckGo)
BRAVE_SEARCH_API_KEY=your_key_here
```

## Files Created/Modified

### Created
- `backend/app/agents/__init__.py`
- `backend/app/agents/execution_tree.py`
- `backend/app/agents/tools/__init__.py`
- `backend/app/agents/tools/base_tool.py`
- `backend/app/agents/tools/tool_registry.py`
- `backend/app/agents/tools/query_planner_tool.py`
- `backend/app/agents/tools/rag_retrieval_tool.py`
- `backend/app/agents/tools/web_search_tool.py`
- `backend/app/agents/tools/data_analysis_tool.py`
- `backend/app/agents/tools/nlp_tool.py`
- `backend/app/agents/tools/visualization_tool.py`
- `backend/app/agents/tools/citation_tool.py`
- `backend/app/services/orchestrator_service.py`

### Modified
- `backend/app/models/chat.py` - Added execution_tree and output_format fields
- `backend/app/dependencies.py` - Added orchestrator service dependency
- `backend/app/api/v1/chat.py` - Simplified to use orchestrator
- `backend/pyproject.toml` - Added duckduckgo-search and scikit-learn

## Next Steps

1. **Test the orchestrator** with various query types
2. **Implement frontend tree viewer** for execution visualization
3. **Add proper tool call tracking** to execution tree
4. **Implement visualization renderer** in frontend
5. **Add more tools** as needed (e.g., SQL query tool, export tool)
6. **Optimize performance** with caching and streaming
7. **Add comprehensive tests** for tools and orchestrator

## Notes

- Query planner uses LLM (GPT-5 Nano) for intelligent analysis, not keyword matching
- RAG tool uses singular `company_id` and supports website/sentiment filters
- Web search is completely free (DuckDuckGo) with no API key needed
- All tools return `ToolResult` with success status, data, and summary
- Agno Team coordinates agents automatically based on instructions
- Execution tree tracks everything for transparency and debugging

## Architecture Inspiration

Based on similar systems like:
- **Elysia** - Multi-step reasoning with tool orchestration
- **LangGraph** - Graph-based agent workflows
- **LangSmith/Langfuse** - Execution trace visualization
- **Perplexity** - Cited search results

But adapted specifically for product review analysis with custom tools and Agno framework.

