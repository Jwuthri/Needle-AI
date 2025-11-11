"""
Test script to demonstrate both simple and medium agents.

This script runs example queries through both agent implementations
to showcase their capabilities and differences.
"""

import asyncio
from typing import List, Dict, Any

from app.utils.logging import get_logger
from app.optimal_workflow.simple_agent import SimpleAgent, run_simple_agent
from app.optimal_workflow.medium_agent import run_medium_agent

logger = get_logger(__name__)


def print_separator(title: str = ""):
    """Print a nice separator."""
    if title:
        print(f"\n{'='*80}")
        print(f"  {title}")
        print(f"{'='*80}\n")
    else:
        print(f"\n{'-'*80}\n")


async def test_simple_agent():
    """Test the simple agent with various queries."""
    print_separator("TESTING SIMPLE AGENT")
    
    agent = SimpleAgent(verbose=False)
    
    test_queries = [
        {
            "name": "SQL Query",
            "query": "Show me all products in the database",
            "description": "Basic database query"
        },
        {
            "name": "Calculator",
            "query": "What is 25 * 4 + 100?",
            "description": "Mathematical calculation"
        },
        {
            "name": "Weather Lookup",
            "query": "What's the weather like in San Francisco?",
            "description": "Utility tool usage"
        },
        {
            "name": "Complex Query",
            "query": "Get the products from the database, calculate the average price, and format the results as a markdown table",
            "description": "Multi-tool query requiring SQL + analysis + formatting"
        },
        {
            "name": "Search",
            "query": "Search for information about Python programming",
            "description": "Mock search functionality"
        }
    ]
    
    for i, test in enumerate(test_queries, 1):
        print(f"\n[Test {i}/{len(test_queries)}] {test['name']}")
        print(f"Description: {test['description']}")
        print(f"Query: {test['query']}")
        print_separator()
        
        try:
            response = await agent.run(test['query'])
            print(f"Response:\n{response}")
        except Exception as e:
            print(f"ERROR: {e}")
            logger.error(f"Test {i} failed", exc_info=True)
        
        print_separator()
        
        # Small delay between tests
        await asyncio.sleep(1)
    
    print("\n✅ Simple Agent tests completed\n")


async def test_medium_agent():
    """Test the medium agent workflow with various queries."""
    print_separator("TESTING MEDIUM AGENT WORKFLOW")
    
    test_queries = [
        {
            "name": "Greeting",
            "query": "Hello! How are you today?",
            "description": "Simple greeting - should route to direct handler"
        },
        {
            "name": "SQL Query",
            "query": "Show me all the sales data from the database",
            "description": "Database query - should route to SQL agent"
        },
        {
            "name": "Analysis Query",
            "query": "Calculate the statistics for these numbers: 10, 20, 30, 40, 50",
            "description": "Statistical analysis - should route to analysis agent"
        },
        {
            "name": "Format Query",
            "query": "Format this data as a markdown table: name=Alice age=30, name=Bob age=25",
            "description": "Formatting request - should route to writer agent"
        },
        {
            "name": "Complex SQL + Analysis",
            "query": "Query the products table and calculate the average price of all items",
            "description": "Multi-step: SQL agent → Analysis agent → Writer agent"
        },
        {
            "name": "Comparison",
            "query": "Compare the values 100 and 150, show me the percentage difference",
            "description": "Analysis with comparison tool"
        }
    ]
    
    for i, test in enumerate(test_queries, 1):
        print(f"\n[Test {i}/{len(test_queries)}] {test['name']}")
        print(f"Description: {test['description']}")
        print(f"Query: {test['query']}")
        print_separator()
        
        try:
            response = await run_medium_agent(test['query'])
            print(f"Response:\n{response}")
        except Exception as e:
            print(f"ERROR: {e}")
            logger.error(f"Test {i} failed", exc_info=True)
        
        print_separator()
        
        # Small delay between tests
        await asyncio.sleep(1)
    
    print("\n✅ Medium Agent tests completed\n")


async def test_conversation_memory():
    """Test conversation memory in both agents."""
    print_separator("TESTING CONVERSATION MEMORY")
    
    # Test Simple Agent Memory
    print("\n[Simple Agent] Testing conversation context...")
    agent = SimpleAgent(verbose=False)
    
    print("\nQuery 1: What is 50 + 50?")
    response1 = await agent.run("What is 50 + 50?")
    print(f"Response: {response1}")
    
    print("\nQuery 2: Now multiply that by 2")
    response2 = await agent.run("Now multiply that by 2")
    print(f"Response: {response2}")
    
    print_separator()
    
    # Test Medium Agent Memory
    print("\n[Medium Agent] Testing conversation context...")
    
    conversation_history = [
        {"role": "user", "content": "Get products from the database"},
        {"role": "assistant", "content": "Here are the products: Laptop Pro ($1299), Mouse ($29), Desk Chair ($199)"}
    ]
    
    print("\nPrevious conversation:")
    for msg in conversation_history:
        print(f"  {msg['role']}: {msg['content']}")
    
    print("\nQuery: What was the most expensive product?")
    response = await run_medium_agent(
        "What was the most expensive product?",
        conversation_history=conversation_history
    )
    print(f"Response: {response}")
    
    print("\n✅ Memory tests completed\n")


async def test_streaming():
    """Test streaming capabilities."""
    print_separator("TESTING STREAMING OUTPUT")
    
    print("\n[Simple Agent] Streaming a response...")
    agent = SimpleAgent(verbose=False)
    
    query = "Search for information about machine learning and explain what you find"
    print(f"Query: {query}\n")
    print("Response (streaming): ", end="", flush=True)
    
    async for chunk in agent.stream_run(query):
        print(chunk, end="", flush=True)
    
    print("\n\n✅ Streaming test completed\n")


async def compare_agents():
    """Compare simple vs medium agent on the same query."""
    print_separator("COMPARING SIMPLE VS MEDIUM AGENTS")
    
    query = "Get products from the database and calculate the average price"
    
    print(f"Query: {query}\n")
    
    # Simple Agent
    print("\n[SIMPLE AGENT]")
    print("-" * 40)
    simple_agent = SimpleAgent(verbose=False)
    simple_response = await simple_agent.run(query)
    print(f"{simple_response}\n")
    
    # Medium Agent
    print("\n[MEDIUM AGENT]")
    print("-" * 40)
    medium_response = await run_medium_agent(query)
    print(f"{medium_response}\n")
    
    print("\n✅ Comparison completed")
    print("\nKey Differences:")
    print("- Simple Agent: Single ReActAgent with all tools, direct reasoning loop")
    print("- Medium Agent: Multi-agent workflow with specialized agents and routing")
    print()


async def run_all_tests():
    """Run all test scenarios."""
    print("\n" + "="*80)
    print("  AGENT TESTING SUITE")
    print("  Testing Simple Agent and Medium Agent Workflow")
    print("="*80)
    
    try:
        # Run all test suites
        await test_simple_agent()
        await asyncio.sleep(2)
        
        await test_medium_agent()
        await asyncio.sleep(2)
        
        await test_conversation_memory()
        await asyncio.sleep(2)
        
        await test_streaming()
        await asyncio.sleep(2)
        
        await compare_agents()
        
        print_separator("ALL TESTS COMPLETED SUCCESSFULLY")
        
    except Exception as e:
        logger.error("Test suite failed", exc_info=True)
        print(f"\n❌ Test suite failed with error: {e}\n")
        raise


async def run_interactive():
    """Run an interactive session to test agents."""
    print_separator("INTERACTIVE AGENT TESTING")
    print("Choose an agent:")
    print("  1. Simple Agent")
    print("  2. Medium Agent")
    print("  3. Quit")
    
    choice = input("\nYour choice (1-3): ").strip()
    
    if choice == "3":
        print("Goodbye!")
        return
    
    agent_type = "simple" if choice == "1" else "medium"
    agent = SimpleAgent(verbose=False) if choice == "1" else None
    
    print(f"\n{'='*80}")
    print(f"  Interactive {agent_type.upper()} Agent Session")
    print(f"  Type 'quit' to exit")
    print(f"{'='*80}\n")
    
    while True:
        query = input("\nYou: ").strip()
        
        if query.lower() in ['quit', 'exit', 'q']:
            print("Goodbye!")
            break
        
        if not query:
            continue
        
        try:
            print(f"\n{agent_type.capitalize()} Agent: ", end="", flush=True)
            
            if agent_type == "simple":
                async for chunk in agent.stream_run(query):
                    print(chunk, end="", flush=True)
                print()
            else:
                response = await run_medium_agent(query)
                print(response)
                
        except Exception as e:
            print(f"\nError: {e}")
            logger.error("Interactive query failed", exc_info=True)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        asyncio.run(run_interactive())
    else:
        asyncio.run(run_all_tests())

