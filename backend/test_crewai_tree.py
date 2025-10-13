"""
Test Crew AI Tree-Based Workflow

This demonstrates how the tree architecture would work with Crew AI.
Note: This is a conceptual example - full implementation would require creating
a CrewAITreeExecutor class similar to AgnoTreeExecutor.

Usage:
    pip install crewai crewai-tools
    python test_crewai_tree.py
"""

import asyncio
from typing import Optional


def test_crewai_tree():
    """Test Crew AI tree workflow."""
    print("=" * 80)
    print("Testing Crew AI Tree-Based Workflow")
    print("=" * 80)
    
    try:
        from crewai import Agent, Task, Crew, Process
        from crewai.tools import tool
        from langchain_openai import ChatOpenAI
    except ImportError:
        print("\n❌ Error: Crew AI not installed")
        print("Install with: pip install crewai crewai-tools langchain-openai")
        return
    
    from app.config import get_settings
    settings = get_settings()
    
    # Get OpenAI API key
    api_key = settings.get_secret("openai_api_key")
    if not api_key:
        print("❌ Error: OpenAI API key not configured")
        print("Set OPENAI_API_KEY in your .env file")
        return
    
    print("\n✓ Crew AI imported successfully")
    
    # Define tools matching Elysia's pattern
    @tool("Query Knowledge Base")
    def query_knowledge_base(
        search_query: str,
        search_type: str = "hybrid",
        limit: int = 10
    ) -> dict:
        """
        Search knowledge base with semantic/keyword/hybrid search.
        
        Args:
            search_query: The search query text
            search_type: Type of search (hybrid, semantic, keyword)
            limit: Maximum number of results
        """
        print(f"  🔧 Executing query: {search_query} (type: {search_type})")
        
        # Mock response
        return {
            "objects": [
                {"id": "1", "content": "Customer complaint about slow performance", "rating": 2.0},
                {"id": "2", "content": "User frustrated with UI complexity", "rating": 2.5},
            ],
            "total": 2,
            "source": "vector_db"
        }
    
    @tool("Aggregate Data")
    def aggregate_data(
        operation: str,
        collection_names: Optional[list] = None
    ) -> dict:
        """
        Perform aggregation operations on data.
        
        Args:
            operation: Operation type (count, sum, average, min, max, group_by)
            collection_names: Collections to aggregate over
        """
        print(f"  🔧 Executing aggregation: {operation}")
        
        # Mock response
        return {
            "operation": operation,
            "result": 150,
            "metadata": {"collections": collection_names or []}
        }
    
    @tool("Visualize Data")
    def visualize_data(
        chart_type: str,
        x_axis: str,
        y_axis: str
    ) -> dict:
        """
        Create data visualizations.
        
        Args:
            chart_type: Type of chart (line, bar, scatter, pie)
            x_axis: X-axis field name
            y_axis: Y-axis field name
        """
        print(f"  🔧 Creating {chart_type} chart")
        
        # Mock response
        return {
            "chart_type": chart_type,
            "chart_url": "https://example.com/chart.png"
        }
    
    print("\n📋 Creating agents with tree workflow...")
    
    # Create LLM
    llm = ChatOpenAI(
        model="gpt-4-turbo-preview",
        api_key=str(api_key)
    )
    
    # BASE BRANCH - Coordinator Agent
    coordinator = Agent(
        role="Task Coordinator",
        goal="Decide the best high-level approach: search, visualize, or respond directly",
        backstory="""You are the root decision maker in a tree-based workflow.
        
Your job is to analyze the user's query and choose:
1. **search**: If we need to retrieve data from the knowledge base
2. **visualize**: If we need to create charts/visualizations  
3. **text_response**: If we can respond directly without data

Base your decision on:
- What the user is asking for
- What information is already available
- The intent behind the query

Explain your reasoning clearly.""",
        llm=llm,
        verbose=True
    )
    
    # SEARCH BRANCH - Search Specialist Agent
    search_specialist = Agent(
        role="Search Specialist",
        goal="Choose between semantic query or statistical aggregation",
        backstory="""You are a search strategy expert.
        
When the coordinator decides we need to search, you choose:
1. **query_knowledge_base**: For retrieving specific entries via semantic/keyword search
   - Use when: Need specific reviews, feedback, mentions
2. **aggregate_data**: For computing statistics and operations
   - Use when: Need counts, averages, summaries, groupings

Analyze the query carefully and pick the right approach.""",
        tools=[query_knowledge_base, aggregate_data],
        llm=llm,
        verbose=True
    )
    
    # Visualizer Agent
    visualizer = Agent(
        role="Visualization Specialist",
        goal="Create clear, informative visualizations",
        backstory="Expert at creating charts and graphs from data.",
        tools=[visualize_data],
        llm=llm,
        verbose=True
    )
    
    # Response Writer Agent
    writer = Agent(
        role="Response Writer",
        goal="Synthesize all information into a clear, cited response",
        backstory="""You are the final synthesizer.
        
Your job is to:
1. Review all previous agent outputs
2. Combine insights from tools and data
3. Generate a clear, well-structured response
4. Include proper citations for all data sources
5. Explain findings in user-friendly language""",
        llm=llm,
        verbose=True
    )
    
    print("✓ Created 4 agents (coordinator, search_specialist, visualizer, writer)")
    
    # Test queries
    queries = [
        "What are the top complaints about our product?",
        "Show me statistics on customer satisfaction ratings",
    ]
    
    for i, query in enumerate(queries, 1):
        print(f"\n{'=' * 80}")
        print(f"Query {i}/{len(queries)}: {query}")
        print(f"{'=' * 80}")
        
        # Define tasks for this query
        coordinate_task = Task(
            description=f"""Analyze this user query and decide the approach:
            
User Query: {query}

Decide:
- Do we need to search the knowledge base? (search)
- Do we need to create visualizations? (visualize)
- Can we respond directly? (text_response)

Provide your decision and reasoning.""",
            agent=coordinator,
            expected_output="A decision (search/visualize/text_response) with reasoning"
        )
        
        search_task = Task(
            description=f"""Based on the coordinator's decision, if search is needed:
            
User Query: {query}

Choose the right search approach:
- query_knowledge_base: For specific entries/mentions
- aggregate_data: For statistics/counts

Execute the appropriate tool and provide results.""",
            agent=search_specialist,
            expected_output="Search results from the appropriate tool"
        )
        
        write_task = Task(
            description=f"""Synthesize the final response:
            
User Query: {query}

Using all previous agent outputs:
1. Combine insights from tools and data
2. Generate a clear, comprehensive response
3. Include citations for data sources
4. Structure the response logically""",
            agent=writer,
            expected_output="A complete, well-cited response to the user"
        )
        
        # Create crew with hierarchical process
        crew = Crew(
            agents=[coordinator, search_specialist, visualizer, writer],
            tasks=[coordinate_task, search_task, write_task],
            process=Process.sequential,  # Sequential execution of tasks
            verbose=True
        )
        
        print("\n🚀 Starting crew execution...")
        
        try:
            result = crew.kickoff()
            
            print("\n💬 Final Response:")
            print("-" * 80)
            print(result)
            print("-" * 80)
            
            print(f"\n✓ Completed query {i}")
        
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
        
        if i < len(queries):
            print("\nWaiting 2 seconds before next query...\n")
            import time
            time.sleep(2)
    
    print("\n" + "=" * 80)
    print("✓ Crew AI tree workflow test completed!")
    print("=" * 80)
    print("\nNote: This is a simplified example. Full tree executor would:")
    print("  - Map tree branches to crew structure")
    print("  - Handle tool chaining automatically")
    print("  - Provide better streaming support")
    print("  - Save agent steps to database")


if __name__ == "__main__":
    test_crewai_tree()

