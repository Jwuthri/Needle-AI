"""
Test OpenAI Agent SDK Tree-Based Workflow

This demonstrates how the tree architecture would work with OpenAI's Agent SDK.
Note: This is a conceptual example - full implementation would require creating
an OpenAITreeExecutor class similar to AgnoTreeExecutor.

Usage:
    python test_openai_tree.py
"""

import asyncio
import json
from typing import AsyncGenerator
from openai import AsyncOpenAI
from app.config import get_settings


# Define tools matching Elysia's multi-branch pattern
QUERY_TOOL = {
    "type": "function",
    "function": {
        "name": "query_knowledge_base",
        "description": "Search knowledge base with semantic/keyword/hybrid search for specific information",
        "parameters": {
            "type": "object",
            "properties": {
                "collection_names": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Collections to search (e.g., ['reviews', 'feedback'])"
                },
                "search_query": {
                    "type": "string",
                    "description": "Search query text"
                },
                "search_type": {
                    "type": "string",
                    "enum": ["hybrid", "semantic", "keyword", "filter_only"],
                    "description": "Type of search to perform",
                    "default": "hybrid"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results",
                    "default": 10
                }
            },
            "required": ["collection_names", "search_query"]
        }
    }
}

AGGREGATE_TOOL = {
    "type": "function",
    "function": {
        "name": "aggregate_data",
        "description": "Compute statistics and aggregations (count, sum, average, min, max, group_by)",
        "parameters": {
            "type": "object",
            "properties": {
                "collection_names": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Collections to aggregate"
                },
                "operation": {
                    "type": "string",
                    "enum": ["count", "sum", "average", "min", "max", "group_by"],
                    "description": "Aggregation operation to perform"
                },
                "grouping_properties": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Properties to group by (for group_by operation)"
                }
            },
            "required": ["collection_names", "operation"]
        }
    }
}

VISUALIZE_TOOL = {
    "type": "function",
    "function": {
        "name": "visualize_data",
        "description": "Create charts and visualizations (line, bar, scatter, pie)",
        "parameters": {
            "type": "object",
            "properties": {
                "chart_type": {
                    "type": "string",
                    "enum": ["line", "bar", "scatter", "pie"],
                    "description": "Type of chart to create"
                },
                "x_axis": {
                    "type": "string",
                    "description": "X-axis field name"
                },
                "y_axis": {
                    "type": "string",
                    "description": "Y-axis field name"
                }
            },
            "required": ["chart_type", "x_axis", "y_axis"]
        }
    }
}


async def execute_tool(tool_name: str, arguments: dict) -> dict:
    """Mock tool execution - replace with actual implementations."""
    print(f"  🔧 Executing tool: {tool_name}")
    print(f"     Arguments: {json.dumps(arguments, indent=6)}")
    
    # Mock responses
    if tool_name == "query_knowledge_base":
        return {
            "objects": [
                {"id": "1", "content": "Customer complaint about slow performance", "rating": 2.0},
                {"id": "2", "content": "User frustrated with UI complexity", "rating": 2.5},
            ],
            "total": 2,
            "source": "vector_db"
        }
    
    elif tool_name == "aggregate_data":
        return {
            "operation": arguments["operation"],
            "result": 150,
            "metadata": {"collections": arguments["collection_names"]}
        }
    
    elif tool_name == "visualize_data":
        return {
            "chart_type": arguments["chart_type"],
            "chart_url": "https://example.com/chart.png",
            "metadata": arguments
        }
    
    return {"status": "completed"}


async def test_openai_tree():
    """Test OpenAI Agent SDK with tree-based workflow."""
    print("=" * 80)
    print("Testing OpenAI Agent SDK Tree-Based Workflow")
    print("=" * 80)
    
    # Get settings
    settings = get_settings()
    
    # Get OpenAI API key
    api_key = settings.get_secret("openai_api_key")
    if not api_key:
        print("❌ Error: OpenAI API key not configured")
        print("Set OPENAI_API_KEY in your .env file")
        return
    
    # Create client
    client = AsyncOpenAI(api_key=str(api_key))
    
    print("\n✓ OpenAI client created")
    
    # Create assistant with tree-based instructions
    print("\n📋 Creating assistant with tree workflow...")
    
    assistant = await client.beta.assistants.create(
        name="Tree Workflow Assistant",
        instructions="""You are an AI assistant using a tree-based decision architecture inspired by Elysia.

Your workflow follows this decision tree:

**BASE BRANCH (Root Decision)**:
Choose the best high-level approach:
1. **search**: Need to retrieve data from knowledge base
   - Leads to SEARCH BRANCH
2. **visualize**: Need to create charts/visualizations
3. **text_response**: Can respond directly without data

**SEARCH BRANCH** (if search chosen):
Choose specific search strategy:
1. **query_knowledge_base**: Retrieve specific entries via semantic/keyword search
   - Use when: Need specific reviews, feedback, or entries
   - After query: Automatically summarize results
2. **aggregate_data**: Compute statistics and operations
   - Use when: Need counts, averages, summaries, groupings

**Decision Making**:
- Base decisions on user's query intent
- Consider what information is already available
- Use environment state (previous tool results)
- Maintain context across all decisions

**Response Style**:
- Clear and informative
- Include citations from tool results
- Explain your reasoning
- Structure responses logically""",
        model="gpt-4-turbo-preview",
        tools=[QUERY_TOOL, AGGREGATE_TOOL, VISUALIZE_TOOL]
    )
    
    print(f"✓ Created assistant: {assistant.id}")
    
    # Test queries
    queries = [
        "What are the top complaints about our product?",
        "Show me statistics on how many reviews mention pricing",
    ]
    
    for i, query in enumerate(queries, 1):
        print(f"\n{'=' * 80}")
        print(f"Query {i}/{len(queries)}: {query}")
        print(f"{'=' * 80}")
        
        # Create thread
        thread = await client.beta.threads.create()
        
        # Add user message
        await client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=query
        )
        
        print("\n🤖 Assistant thinking...\n")
        
        # Run with streaming
        try:
            run = await client.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=assistant.id,
                stream=False  # We'll poll for simplicity in this example
            )
            
            # Poll for completion
            step_count = 0
            while run.status in ["queued", "in_progress", "requires_action"]:
                await asyncio.sleep(1)
                run = await client.beta.threads.runs.retrieve(
                    thread_id=thread.id,
                    run_id=run.id
                )
                
                # Handle tool calls
                if run.status == "requires_action":
                    step_count += 1
                    print(f"\n📍 Step {step_count}: Tool calls required")
                    
                    tool_outputs = []
                    for tool_call in run.required_action.submit_tool_outputs.tool_calls:
                        print(f"\n  → Tool: {tool_call.function.name}")
                        
                        # Parse arguments
                        arguments = json.loads(tool_call.function.arguments)
                        
                        # Execute tool
                        result = await execute_tool(tool_call.function.name, arguments)
                        
                        tool_outputs.append({
                            "tool_call_id": tool_call.id,
                            "output": json.dumps(result)
                        })
                        
                        print(f"  ✓ Result: {json.dumps(result, indent=6)}")
                    
                    # Submit tool outputs
                    run = await client.beta.threads.runs.submit_tool_outputs(
                        thread_id=thread.id,
                        run_id=run.id,
                        tool_outputs=tool_outputs
                    )
            
            if run.status == "completed":
                # Get messages
                messages = await client.beta.threads.messages.list(
                    thread_id=thread.id
                )
                
                # Get assistant's response
                for message in messages.data:
                    if message.role == "assistant":
                        print("\n💬 Assistant Response:")
                        print("-" * 80)
                        for content in message.content:
                            if hasattr(content, 'text'):
                                print(content.text.value)
                        print("-" * 80)
                        break
                
                print(f"\n✓ Completed with {step_count} tool execution steps")
            
            else:
                print(f"\n❌ Run ended with status: {run.status}")
        
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
        
        # Cleanup
        await client.beta.threads.delete(thread.id)
        
        if i < len(queries):
            print("\nWaiting 2 seconds before next query...\n")
            await asyncio.sleep(2)
    
    # Cleanup
    await client.beta.assistants.delete(assistant.id)
    
    print("\n" + "=" * 80)
    print("✓ OpenAI tree workflow test completed!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_openai_tree())

