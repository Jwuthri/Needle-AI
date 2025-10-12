# Multi-Agent Chat Orchestration System

## Architecture Overview

Replace the current rigid routing (`if company_id: use RAG, else: use regular chat`) with a dynamic multi-agent system where:

1. **Query Planner Agent** analyzes the query and determines:

   - Output format (markdown/text, visualization, cited summary)
   - Intent (Summarization, Aggregation, Filtering, Ranking, Trend Analysis, Gap Analysis, Competitive Analysis)

2. **Orchestrator Agent** coordinates specialized agents to:

   - Retrieve data (RAG and/or web search)
   - Process data (statistics, NLP features like TF-IDF)
   - Generate visualizations (charts, tables, timelines)
   - Synthesize final response with citations

3. **Execution Tree** tracks all steps for UI visualization

## Implementation Steps

### 1. Create Tool System (`backend/app/agents/tools/`)

Build reusable tools that agents can invoke:

**Base Tool Interface** (`base_tool.py`):

```python
class BaseTool:
    name: str
    description: str
    async def execute(**kwargs) -> Dict[str, Any]
```

**Core Tools to Implement**:

- `query_planner_tool.py` - Analyzes query, returns format + intent
- `rag_retrieval_tool.py` - Vector search on reviews (wrap existing VectorService)
- `web_search_tool.py` - Brave/DuckDuckGo search (free APIs)
- `data_analysis_tool.py` - Stats operations (sum, mean, aggregations, groupby)
- `nlp_tool.py` - TF-IDF, keyword extraction on text columns
- `visualization_tool.py` - Generate chart configs (bar, line, pie, table)
- `citation_tool.py` - Format sources and create cited summaries

Each tool returns structured data including execution metadata for the tree.

### 2. Create Agent System (`backend/app/agents/`)

**Orchestrator Agent** (`orchestrator_agent.py`):

- Coordinates the workflow
- Manages execution tree
- Has access to all tools
- Uses Agno's Agent with tools parameter
- Instructions: "Break down queries into steps, invoke appropriate tools, synthesize results"

**Specialized Agents** (optional, if orchestrator gets complex):

- `data_agent.py` - Handles RAG + web search decisions
- `analysis_agent.py` - Handles statistical and NLP operations
- `synthesis_agent.py` - Generates final formatted response

Use Agno's team functionality if using multiple agents, otherwise a single orchestrator with tools is cleaner.

### 3. Execution Tree Tracker (`backend/app/agents/execution_tree.py`)

Track each step in a tree structure:

```python
class ExecutionNode:
    id: str
    name: str  # e.g., "Query Planning", "RAG Retrieval"
    type: str  # "agent", "tool", "decision"
    status: str  # "pending", "running", "completed", "failed"
    input: Dict
    output: Dict
    duration_ms: int
    children: List[ExecutionNode]
    metadata: Dict

class ExecutionTree:
    root: ExecutionNode
    def add_node(parent_id, node)
    def to_dict() -> Dict  # For API response
```

### 4. Create Orchestrator Service (`backend/app/services/orchestrator_service.py`)

Main service that replaces current chat routing logic:

```python
class OrchestratorService:
    async def initialize():
        # Create Agno orchestrator agent with all tools
        # Use PostgresDb for persistence
        # Configure with OpenRouter model
        
    async def process_message(request: ChatRequest, user_id, db) -> ChatResponse:
        # 1. Initialize execution tree
        tree = ExecutionTree()
        
        # 2. Start orchestrator agent with query
        # Agent will automatically:
        #    - Call query_planner_tool to determine format/intent
        #    - Decide whether to use RAG, web search, or both
        #    - Apply analytics/NLP if needed
        #    - Generate visualization configs
        #    - Synthesize final response
        
        # 3. Track each tool call in execution tree
        # 4. Return response with tree in metadata
```

Key: Use Agno's tool calling feature - agent automatically decides which tools to invoke based on query.

### 5. Update Chat Endpoint (`backend/app/api/v1/chat.py`)

Simplify the endpoint dramatically:

```python
@router.post("/", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    orchestrator = Depends(get_orchestrator_dep),
    current_user = Depends(get_current_user),
    db = Depends(get_db)
):
    # Save user message
    # Call orchestrator.process_message()
    # Save assistant response
    # Return response with execution_tree in metadata
```

Remove all the if/else logic, RAG service instantiation, title generation inline code.

### 6. Enhance Response Models (`backend/app/models/chat.py`)

Add execution tree support:

```python
class ExecutionStep(BaseModel):
    id: str
    name: str
    type: str
    status: str
    duration_ms: int
    input_summary: Optional[str]
    output_summary: Optional[str]
    children: List["ExecutionStep"]

class ChatResponse(BaseModel):
    message: str
    session_id: str
    message_id: str
    output_format: str  # "text", "visualization", "cited_summary"
    visualization: Optional[Dict]  # Chart config if applicable
    sources: Optional[List[Dict]]  # Citations
    metadata: Dict
    execution_tree: Optional[ExecutionStep]  # NEW
```

### 7. Web Search Integration (`backend/app/agents/tools/web_search_tool.py`)

Implement free search APIs:

- **Brave Search API** - 2000 free queries/month
- **DuckDuckGo** - Use `duckduckgo-search` Python library (completely free, no API key)

Start with DuckDuckGo (easier, no signup), optionally add Brave for better results.

### 8. Data Processing Tools

**Analytics Tool** (`data_analysis_tool.py`):

- Input: tabular data (list of dicts)
- Operations: sum, mean, median, count, groupby, filter
- Output: processed data + summary statistics

**NLP Tool** (`nlp_tool.py`):

- Input: text column from data
- Features: TF-IDF, keyword extraction, text similarity
- Use sklearn for TF-IDF
- Output: keywords, scores, insights

### 9. Visualization Tool (`visualization_tool.py`)

Generate visualization configurations (not actual images):

```python
def generate_chart_config(data: List[Dict], chart_type: str) -> Dict:
    return {
        "type": chart_type,  # "bar", "line", "pie", "table"
        "data": data,
        "axes": {...},
        "labels": {...}
    }
```

Frontend will render based on config using Chart.js or similar.

### 10. Frontend Integration

**Update ChatResponse Display** (`frontend/src/components/chat/`):

- Detect `output_format` in response
- Render markdown/text as normal
- Render visualizations using chart library
- Show cited sources in expandable section

**Execution Tree Viewer** (`frontend/src/components/chat/execution-tree.tsx`):

- Display hierarchical tree of steps
- Show duration, status, input/output for each step
- Collapsible nodes
- Color-coded by status (success/error)

Similar to Langfuse or LangSmith trace views.

### 11. Configuration & Dependencies

**Add to `pyproject.toml`**:

```toml
duckduckgo-search = "^6.0.0"  # Free web search
scikit-learn = "^1.5.0"  # For TF-IDF and analytics
pandas = "^2.2.0"  # Data manipulation
```

**Environment Variables** (`.env`):

```
BRAVE_SEARCH_API_KEY=optional_if_using_brave
ORCHESTRATOR_MODEL=openai/gpt-5-nano  # Fast, cheap for tool calling
SYNTHESIS_MODEL=anthropic/claude-sonnet-4.5  # Better for final responses
```

## Key Files to Modify

- `backend/app/api/v1/chat.py` - Simplify to use orchestrator
- `backend/app/services/rag_chat_service.py` - Convert to tool
- `backend/app/models/chat.py` - Add execution tree fields
- `backend/app/dependencies.py` - Add orchestrator dependency

## Key Files to Create

- `backend/app/agents/orchestrator_agent.py`
- `backend/app/agents/execution_tree.py`
- `backend/app/agents/tools/*.py` (7 tool files)
- `backend/app/services/orchestrator_service.py`
- `frontend/src/components/chat/execution-tree.tsx`

## Additional Improvements

1. **Streaming Support**: Agno supports streaming, enable for real-time updates
2. **Caching**: Cache query plans and RAG results for common queries
3. **Cost Tracking**: Log token usage per tool call for cost analysis
4. **A/B Testing**: Test different agent instructions to optimize tool selection
5. **User Feedback**: Add thumbs up/down on responses to improve orchestration
6. **Query Rewriting**: Add tool to rephrase ambiguous queries before processing
7. **Multi-company Analysis**: Extend RAG tool to compare across multiple companies
8. **Export Results**: Allow exporting visualizations and data as CSV/PNG