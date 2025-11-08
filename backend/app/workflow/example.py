"""
Example usage of the LlamaIndex workflow.

This demonstrates different ways to use the workflow.
"""

import asyncio
from app.workflow.main import run_workflow, run_workflow_streaming
from app import get_logger

logger = get_logger(__name__)


async def example_basic():
    """Basic workflow execution."""
    print("\n" + "=" * 80)
    print("EXAMPLE 1: Basic Workflow Execution")
    print("=" * 80 + "\n")
    
    query = "What are the main product gaps for Netflix based on customer reviews?"
    result = await run_workflow(query, user_id=1)
    
    print("\n" + "=" * 80)
    print("RESULT:")
    print("=" * 80)
    print(result)


async def example_streaming():
    """Streaming workflow execution."""
    print("\n" + "=" * 80)
    print("EXAMPLE 2: Streaming Workflow Execution")
    print("=" * 80 + "\n")
    
    query = "Analyze customer sentiment for Netflix"
    
    async for event in run_workflow_streaming(query, user_id=1):
        print(f"📡 Received event: {type(event).__name__}")


async def example_direct():
    """Direct workflow usage with custom configuration."""
    print("\n" + "=" * 80)
    print("EXAMPLE 3: Direct Workflow Usage")
    print("=" * 80 + "\n")
    
    from app.workflow.workflow import ProductGapWorkflow
    
    # Create workflow with custom settings
    workflow = ProductGapWorkflow(
        user_id=1,
        timeout=600,  # 10 minutes
        verbose=True
    )
    
    query = "Show me the top 10 negative reviews for Netflix"
    result = await workflow.run(query=query)
    
    print("\n" + "=" * 80)
    print("RESULT:")
    print("=" * 80)
    print(result)


async def example_multiple_queries():
    """Run multiple queries in sequence."""
    print("\n" + "=" * 80)
    print("EXAMPLE 4: Multiple Queries")
    print("=" * 80 + "\n")
    
    queries = [
        "What are the main product gaps?",
        "Show me sentiment analysis",
        "List top 5 feature requests"
    ]
    
    for i, query in enumerate(queries, 1):
        print(f"\n--- Query {i}/{len(queries)} ---")
        print(f"Q: {query}")
        
        result = await run_workflow(query, user_id=1)
        
        print(f"A: {result[:200]}...")  # Show first 200 chars


async def example_error_handling():
    """Demonstrate error handling."""
    print("\n" + "=" * 80)
    print("EXAMPLE 5: Error Handling")
    print("=" * 80 + "\n")
    
    try:
        # This might fail if no data is available
        result = await run_workflow(
            "Show me data for a non-existent company",
            user_id=999
        )
        print(result)
    except Exception as e:
        logger.error(f"Workflow failed: {e}")
        print(f"❌ Error: {e}")


async def main():
    """Run all examples."""
    examples = [
        ("Basic Execution", example_basic),
        ("Streaming", example_streaming),
        ("Direct Usage", example_direct),
        ("Multiple Queries", example_multiple_queries),
        ("Error Handling", example_error_handling),
    ]
    
    print("\n" + "=" * 80)
    print("LlamaIndex Workflow Examples")
    print("=" * 80)
    print("\nAvailable examples:")
    for i, (name, _) in enumerate(examples, 1):
        print(f"  {i}. {name}")
    
    print("\nRunning all examples...\n")
    
    for name, example_func in examples:
        try:
            await example_func()
        except Exception as e:
            logger.error(f"Example '{name}' failed: {e}", exc_info=True)
            print(f"\n❌ Example '{name}' failed: {e}\n")
        
        # Pause between examples
        await asyncio.sleep(1)
    
    print("\n" + "=" * 80)
    print("All examples completed!")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    # Run a single example
    # asyncio.run(example_basic())
    
    # Or run all examples
    asyncio.run(main())
