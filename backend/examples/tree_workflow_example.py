"""
Example: Tree-Based Workflow with Agno

Demonstrates the tree-based orchestration architecture inspired by Elysia,
implemented using Agno agents with streaming hooks.
"""

import asyncio
from app.agents.tree.workflows.multi_branch import create_multi_branch_workflow
from agno.models.openrouter import OpenRouter
from app.config import get_settings


async def stream_callback(update: dict):
    """
    Callback to handle streaming updates.
    
    In a real application, this would send updates via WebSocket.
    """
    update_type = update.get("type")
    data = update.get("data", {})
    
    if update_type == "agent_step_start":
        print(f"\n🤖 Agent Started: {data.get('agent_name')}")
        print(f"   Step: {data.get('step_order')}")
        print(f"   Time: {data.get('timestamp')}")
    
    elif update_type == "agent_step_content":
        # Streaming content from agent (for text output)
        content = data.get('content_chunk', '')
        if content:
            print(content, end='', flush=True)
    
    elif update_type == "agent_step_complete":
        print(f"\n✅ Agent Completed: {data.get('agent_name')}")
        print(f"   Step: {data.get('step_order')}")
        
        content = data.get('content')
        is_structured = data.get('is_structured', False)
        
        if is_structured:
            print(f"   Structured Output: {content}")
        else:
            print(f"   Text Output: {content[:100]}..." if len(str(content)) > 100 else f"   Text Output: {content}")


async def main():
    """Run tree workflow example."""
    print("=" * 80)
    print("Tree-Based Workflow Example")
    print("=" * 80)
    
    # Get settings
    settings = get_settings()
    
    # Create model
    api_key = settings.get_secret("openrouter_api_key")
    model = OpenRouter(
        id=settings.default_model,
        api_key=str(api_key),
        max_tokens=4096
    )
    
    # Create multi-branch workflow executor
    print("\n📋 Creating multi-branch workflow...")
    executor = create_multi_branch_workflow(
        name="Review Analysis Workflow",
        model=model,
        settings=settings
    )
    
    print(f"✓ Created workflow with {len(executor.tree.branches)} branches")
    print(f"✓ Registered {len(executor.tree.tools)} tools")
    
    # Example queries
    queries = [
        "What are the top complaints about our product?",
        "Show me the average rating across all reviews",
        "Create a chart showing sentiment trends over time",
    ]
    
    for i, query in enumerate(queries, 1):
        print(f"\n{'=' * 80}")
        print(f"Query {i}/{len(queries)}: {query}")
        print(f"{'=' * 80}")
        
        # Execute with streaming
        try:
            async for chunk in executor.run(
                user_prompt=query,
                stream_callback=stream_callback,
                user_id="example_user",
                session_id="example_session"
            ):
                # stream_callback handles the updates
                pass
        
        except Exception as e:
            print(f"\n❌ Error: {e}")
        
        print("\n" + "-" * 80)
        await asyncio.sleep(1)  # Brief pause between queries


async def example_direct_tree_usage():
    """
    Example of using Tree directly without executor.
    
    This shows the lower-level tree API.
    """
    from app.agents.tree.base import Tree
    from app.agents.tree.workflows.elysia_tools import QueryTool, CitedSummarizerTool
    
    print("\n" + "=" * 80)
    print("Direct Tree API Example")
    print("=" * 80)
    
    # Create tree
    tree = Tree(
        name="Simple Query Tree",
        description="Simple tree with query and response",
        style="Clear and concise",
        agent_description="Helpful assistant",
        end_goal="Answer user queries with data"
    )
    
    # Add root branch
    tree.add_branch(
        root=True,
        branch_id="root",
        instruction="Choose between querying data or responding directly",
        status="Processing query..."
    )
    
    # Add tools
    tree.add_tool(QueryTool(), branch_id="root")
    tree.add_tool(CitedSummarizerTool(), branch_id="root")
    
    print(f"✓ Created tree with {len(tree.branches)} branches and {len(tree.tools)} tools")
    
    # Execute tree
    print("\nExecuting tree...")
    
    async def simple_decision_callback(instruction, options, tree_data, **kwargs):
        """Simple decision: always choose first option."""
        print(f"  Decision: {instruction}")
        print(f"  Options: {options}")
        chosen = options[0]
        print(f"  Chosen: {chosen}")
        return chosen
    
    async for result in tree.run(
        user_prompt="What are the main features mentioned in reviews?",
        decision_callback=simple_decision_callback
    ):
        result_type = result.frontend_type
        print(f"  Result: {result_type}")
        
        if hasattr(result, 'message'):
            print(f"    {result.message}")
        elif hasattr(result, 'content'):
            print(f"    {result.content[:100]}...")


if __name__ == "__main__":
    print("\nRunning Tree Workflow Examples")
    print("=" * 80)
    
    # Run main example
    asyncio.run(main())
    
    # Run direct tree example
    asyncio.run(example_direct_tree_usage())
    
    print("\n" + "=" * 80)
    print("Examples completed!")
    print("=" * 80)

