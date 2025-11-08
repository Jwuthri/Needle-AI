"""
Example demonstrating the NLP analysis step in the workflow.

This shows how the NLP agent selects and configures tools based on the query.
"""

import asyncio
from app.workflow.agents import QueryAnalysis, perform_nlp_analysis
from app import get_logger

logger = get_logger(__name__)


async def example_nlp_analysis():
    """Demonstrate NLP analysis with different query types."""
    
    # Example 1: Product gaps analysis
    print("\n" + "="*80)
    print("Example 1: Product Gaps Analysis")
    print("="*80)
    
    query1 = "Find product gaps for Netflix based on user reviews"
    analysis1 = QueryAnalysis(
        needs_data_retrieval=True,
        needs_nlp_analysis=True,
        company="Netflix",
        query_type="analysis",
        reasoning="User wants to find missing features",
        analysis_type="gap_detection"
    )
    
    retrieved_data1 = {
        "total_rows": 1500,
        "data": {
            "user_reviews": [
                {"id": 1, "review_text": "Would love to see offline downloads", "rating": 4, "date": "2024-01-15"},
                {"id": 2, "review_text": "Missing parental controls", "rating": 3, "date": "2024-01-16"},
                {"id": 3, "review_text": "Please add download feature", "rating": 4, "date": "2024-01-17"},
            ]
        }
    }
    
    result1 = await perform_nlp_analysis(query1, analysis1, retrieved_data1)
    print(f"\nQuery: {query1}")
    print(f"Analysis Type: {analysis1.analysis_type}")
    print(f"Tool Calls: {result1.get('tool_calls', [])}")
    print(f"Agent Response: {result1.get('agent_response', '')[:200]}...")
    
    # Example 2: Sentiment analysis
    print("\n" + "="*80)
    print("Example 2: Sentiment Analysis")
    print("="*80)
    
    query2 = "Analyze sentiment patterns in Spotify user feedback"
    analysis2 = QueryAnalysis(
        needs_data_retrieval=True,
        needs_nlp_analysis=True,
        company="Spotify",
        query_type="analysis",
        reasoning="User wants sentiment analysis",
        analysis_type="sentiment"
    )
    
    retrieved_data2 = {
        "total_rows": 2000,
        "data": {
            "feedback_data": [
                {"feedback_id": 1, "comment": "Love the new UI!", "score": 5, "category": "UI"},
                {"feedback_id": 2, "comment": "App crashes frequently", "score": 2, "category": "Performance"},
                {"feedback_id": 3, "comment": "Great music recommendations", "score": 5, "category": "Features"},
            ]
        }
    }
    
    result2 = await perform_nlp_analysis(query2, analysis2, retrieved_data2)
    print(f"\nQuery: {query2}")
    print(f"Analysis Type: {analysis2.analysis_type}")
    print(f"Tool Calls: {result2.get('tool_calls', [])}")
    print(f"Agent Response: {result2.get('agent_response', '')[:200]}...")
    
    # Example 3: Theme clustering
    print("\n" + "="*80)
    print("Example 3: Theme Clustering")
    print("="*80)
    
    query3 = "What are the main themes in Notion user reviews?"
    analysis3 = QueryAnalysis(
        needs_data_retrieval=True,
        needs_nlp_analysis=True,
        company="Notion",
        query_type="analysis",
        reasoning="User wants to identify themes",
        analysis_type="clustering"
    )
    
    retrieved_data3 = {
        "total_rows": 1200,
        "data": {
            "reviews": [
                {"review_id": 1, "text": "Great for collaboration", "stars": 5, "user_type": "team"},
                {"review_id": 2, "text": "Templates are very useful", "stars": 4, "user_type": "individual"},
                {"review_id": 3, "text": "Love the database features", "stars": 5, "user_type": "team"},
            ]
        }
    }
    
    result3 = await perform_nlp_analysis(query3, analysis3, retrieved_data3)
    print(f"\nQuery: {query3}")
    print(f"Analysis Type: {analysis3.analysis_type}")
    print(f"Tool Calls: {result3.get('tool_calls', [])}")
    print(f"Agent Response: {result3.get('agent_response', '')[:200]}...")


if __name__ == "__main__":
    print("\n🔬 NLP Analysis Examples")
    print("This demonstrates how the NLP agent selects tools based on query type\n")
    
    asyncio.run(example_nlp_analysis())
