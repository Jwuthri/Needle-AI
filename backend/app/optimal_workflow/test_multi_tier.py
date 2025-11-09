"""
Test script for multi-tier workflow system.

Run with: python -m app.optimal_workflow.test_multi_tier
"""

import asyncio
from app.optimal_workflow.main import run_workflow


async def test_workflows():
    """Test all three workflow tiers."""
    
    print("=" * 80)
    print("TESTING MULTI-TIER WORKFLOW SYSTEM")
    print("=" * 80)
    
    # Test 1: Simple query (should use gpt-5-nano)
    print("\n\n1️⃣  TESTING SIMPLE WORKFLOW")
    print("-" * 80)
    simple_query = "Hello! How are you today?"
    print(f"Query: {simple_query}")
    print("-" * 80)
    
    result = await run_workflow(
        query=simple_query,
        user_id="test_user",
        session_id="test_session_1"
    )
    
    print("\nResult:")
    print(result)
    print("\n" + "=" * 80)
    
    # Test 2: Medium query with history (should use gpt-5-mini)
    print("\n\n2️⃣  TESTING MEDIUM WORKFLOW")
    print("-" * 80)
    medium_query = "Can you explain that in more detail?"
    print(f"Query: {medium_query}")
    print("-" * 80)
    
    conversation_history = [
        {"role": "user", "content": "What is artificial intelligence?"},
        {"role": "assistant", "content": "Artificial intelligence (AI) is the simulation of human intelligence by machines."}
    ]
    
    result = await run_workflow(
        query=medium_query,
        user_id="test_user",
        session_id="test_session_2",
        conversation_history=conversation_history
    )
    
    print("\nResult:")
    print(result)
    print("\n" + "=" * 80)
    
    # Test 3: Complex query (should use full workflow)
    print("\n\n3️⃣  TESTING COMPLEX WORKFLOW")
    print("-" * 80)
    complex_query = "What are the main product gaps for Netflix based on customer reviews?"
    print(f"Query: {complex_query}")
    print("-" * 80)
    
    result = await run_workflow(
        query=complex_query,
        user_id="test_user",
        session_id="test_session_3"
    )
    
    print("\nResult:")
    print(result)
    print("\n" + "=" * 80)
    
    print("\n\n✅ ALL TESTS COMPLETED")
    print("=" * 80)


async def test_classification_only():
    """Test just the query classifier."""
    from app.optimal_workflow.query_classifier import classify_query
    
    print("\n\nTESTING QUERY CLASSIFIER")
    print("=" * 80)
    
    test_queries = [
        ("Hello!", None),
        ("Who is Taylor Swift?", None),
        ("Tell me more about that", [
            {"role": "user", "content": "What is AI?"},
            {"role": "assistant", "content": "AI is..."}
        ]),
        ("What are the product gaps for Netflix?", None),
    ]
    
    for query, history in test_queries:
        print(f"\nQuery: {query}")
        classification = await classify_query(query, history)
        print(f"  Complexity: {classification.complexity}")
        print(f"  Reasoning: {classification.reasoning}")
        print(f"  Requires Data: {classification.requires_data}")
        print(f"  Requires History: {classification.requires_history}")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--classifier-only":
        asyncio.run(test_classification_only())
    else:
        asyncio.run(test_workflows())

