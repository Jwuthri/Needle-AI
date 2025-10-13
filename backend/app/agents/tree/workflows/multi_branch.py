"""
Multi-branch workflow matching Elysia's architecture.

This workflow implements Elysia's multi_branch_init pattern:

1. Base Branch (root):
   - Choose between: search, visualize, or text_response
   - Tools: CitedSummarizer, TextResponse, Visualize

2. Search Branch (from base):
   - Choose between: query or aggregate
   - Tools: Query, Aggregate
   - After query: SummarizeItems runs (chained tool)

This creates a decision tree where the agent:
- First decides the high-level approach
- If searching, decides query vs aggregate
- If querying, automatically summarizes results
- Finally synthesizes a response
"""

from typing import Optional, Any
from app.agents.tree.base import Tree
from app.agents.tree.workflows.elysia_tools import (
    QueryTool,
    AggregateTool,
    VisualizeTool,
    SummarizeItemsTool,
    CitedSummarizerTool,
    TextResponseTool
)
from app.agents.tree.executors.agno_executor import AgnoTreeExecutor
from app.utils.logging import get_logger

logger = get_logger("multi_branch_workflow")


def create_multi_branch_workflow(
    name: str = "Multi-Branch Workflow",
    model: Optional[Any] = None,
    db: Optional[Any] = None,
    settings: Optional[Any] = None
) -> AgnoTreeExecutor:
    """
    Create multi-branch workflow matching Elysia's pattern.
    
    Args:
        name: Workflow name
        model: Agno model instance
        db: Agno database instance
        settings: Application settings
        
    Returns:
        AgnoTreeExecutor configured with multi-branch tree
    """
    # Create tree
    tree = Tree(
        name=name,
        description="Multi-branch decision tree for query handling",
        style="Clear and informative",
        agent_description="Expert at analyzing queries and coordinating specialized agents",
        end_goal="Provide accurate, well-cited responses based on available data"
    )
    
    # ===== BASE BRANCH (Root) =====
    tree.add_branch(
        root=True,
        branch_id="base",
        instruction="""Choose a base-level task based on the user's prompt and available information.
        
You can:
- **search**: Search the knowledge base (for data retrieval)
- **visualize**: Create charts and visualizations
- **text_response**: Respond directly with text (no data needed)
- **cited_summarizer**: Generate a well-cited response from available data

Base your decision on:
- What information is available
- What the user is asking for
- Whether you need to retrieve data first

You can search multiple times if needed.""",
        status="Choosing base-level task...",
        description="Decide the high-level approach to answering the query"
    )
    
    # Add tools to base branch
    tree.add_tool(CitedSummarizerTool(), branch_id="base")
    tree.add_tool(TextResponseTool(), branch_id="base")
    tree.add_tool(VisualizeTool(), branch_id="base")
    
    # ===== SEARCH BRANCH (Sub-branch from base) =====
    tree.add_branch(
        root=False,
        branch_id="search",
        from_branch_id="base",
        instruction="""Choose between querying or aggregating data.

**query_knowledge_base**: Retrieve specific information via semantic/keyword search
- Use when: Need to find specific entries, reviews, feedback
- Examples: "Show me reviews about X", "Find mentions of Y"

**aggregate_data**: Perform operations like count, sum, average, grouping
- Use when: Need statistics, summaries, counts
- Examples: "How many reviews mention X?", "Average rating for Y"

Choose based on whether you need specific entries (query) or statistics (aggregate).""",
        status="Searching knowledge base...",
        description="Decide between semantic search or statistical aggregation"
    )
    
    # Add tools to search branch
    tree.add_tool(QueryTool(), branch_id="search")
    tree.add_tool(AggregateTool(), branch_id="search")
    
    # Add chained summarizer (runs after query)
    tree.add_tool(
        SummarizeItemsTool(),
        branch_id="search",
        from_tool_ids=["query_knowledge_base"]  # Runs after query
    )
    
    logger.info(f"Created multi-branch workflow with {len(tree.branches)} branches and {len(tree.tools)} tools")
    
    # Create executor
    executor = AgnoTreeExecutor(
        tree=tree,
        model=model,
        db=db,
        settings=settings
    )
    
    return executor


# Example usage documentation
USAGE_EXAMPLE = """
# Example: Using Multi-Branch Workflow

```python
from app.agents.tree.workflows.multi_branch import create_multi_branch_workflow
from agno.models.openrouter import OpenRouter

# Create model
model = OpenRouter(
    id="anthropic/claude-3.5-sonnet",
    api_key="your-key"
)

# Create workflow
executor = create_multi_branch_workflow(
    name="Review Analysis Workflow",
    model=model
)

# Execute with streaming
async for update in executor.run(
    user_prompt="What are the top complaints about our product?",
    stream_callback=stream_to_frontend,
    db_session=db,
    message_id=message_id,
    user_id=user_id,
    session_id=session_id
):
    # Each update contains agent steps or content
    print(update)
```

Expected Flow:
1. Base agent decides: "need to search for complaints" → chooses 'search' branch
2. Search agent decides: "need specific reviews" → chooses 'query_knowledge_base'
3. Query tool retrieves reviews
4. Summarizer tool automatically summarizes (chained from query)
5. Base agent decides: "have data, can synthesize" → chooses 'cited_summarizer'
6. Cited Summarizer generates final response with citations

Frontend receives:
- agent_step_start: Base agent
- agent_step_complete: Base agent (chose 'search')
- agent_step_start: Search agent
- agent_step_complete: Search agent (chose 'query')
- agent_step_start: Query tool
- agent_step_complete: Query tool (with results)
- agent_step_start: Summarizer
- agent_step_complete: Summarizer (with summary)
- agent_step_start: Cited Summarizer
- agent_step_complete: Cited Summarizer (final response)
- content: Final response text streaming
```
"""

