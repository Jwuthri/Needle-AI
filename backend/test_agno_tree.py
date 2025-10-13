"""
Test Agno Tree-Based Workflow

Run this to test the Agno implementation of tree-based orchestration.

Usage:
    python test_agno_tree.py
"""

import asyncio
from app.agents.tree.workflows.multi_branch import create_multi_branch_workflow
from app.config import get_settings
from agno.models.openrouter import OpenRouter


async def test_agno_tree():
    """Test Agno tree workflow with streaming."""
    print("=" * 80)
    print("Testing Agno Tree-Based Workflow")
    print("=" * 80)
    
    # Get settings
    settings = get_settings()
    
    # Create model
    api_key = settings.get_secret("openrouter_api_key")
    if not api_key:
        print("❌ Error: OpenRouter API key not configured")
        print("Set OPENROUTER_API_KEY in your .env file")
        return
    
    model = OpenRouter(
        id=settings.default_model,
        api_key=str(api_key),
        max_tokens=4096
    )
    
    print("\n✓ OpenRouter model created")
    
    # Create multi-branch workflow executor
    print("\n📋 Creating multi-branch workflow...")
    executor = create_multi_branch_workflow(
        name="Agno Test Workflow",
        model=model,
        settings=settings
    )
    
    print(f"✓ Created workflow with {len(executor.tree.branches)} branches")
    print(f"✓ Registered {len(executor.tree.tools)} tools")
    
    # Print tree structure
    print("\n🌲 Tree Structure:")
    for branch_id, branch in executor.tree.branches.items():
        print(f"  Branch: {branch_id}")
        print(f"    Instruction: {branch.instruction[:80]}...")
        print(f"    Tools: {[t.name for t in branch.tools]}")
        if branch.child_branches:
            print(f"    Child Branches: {[b.branch_id for b in branch.child_branches]}")
    
    # Test queries
    queries = [
        "What are the top complaints about our product?",
        "Show me statistics on customer satisfaction",
    ]
    
    for i, query in enumerate(queries, 1):
        print(f"\n{'=' * 80}")
        print(f"Query {i}/{len(queries)}: {query}")
        print(f"{'=' * 80}")
        
        # Stream callback for real-time updates
        async def stream_callback(update: dict):
            """Handle streaming updates."""
            update_type = update.get("type")
            data = update.get("data", {})
            
            if update_type == "agent_step_start":
                print(f"\n🤖 [{data.get('step_order')}] Agent Started: {data.get('agent_name')}")
            
            elif update_type == "agent_step_complete":
                print(f"✅ [{data.get('step_order')}] Agent Completed: {data.get('agent_name')}")
                
                content = data.get('content')
                is_structured = data.get('is_structured', False)
                
                if is_structured:
                    print(f"   Structured Output: {str(content)[:100]}...")
                else:
                    print(f"   Text Output: {str(content)[:100]}...")
        
        try:
            # Execute with streaming
            chunk_count = 0
            async for chunk in executor.run(
                user_prompt=query,
                stream_callback=stream_callback,
                user_id="test_user",
                session_id="test_session"
            ):
                chunk_count += 1
                
                # Log team events
                event_type = getattr(chunk, 'event', 'unknown')
                if event_type == "TeamRunContent":
                    if hasattr(chunk, 'content'):
                        print(chunk.content, end='', flush=True)
            
            print(f"\n\n✓ Completed with {chunk_count} chunks")
        
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n" + "-" * 80)
        
        if i < len(queries):
            print("\nWaiting 2 seconds before next query...\n")
            await asyncio.sleep(2)
    
    print("\n" + "=" * 80)
    print("✓ Agno tree workflow test completed!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_agno_tree())

