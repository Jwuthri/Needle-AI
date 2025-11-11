"""
Multi-Agent Product Review Analysis System using LlamaIndex Workflow
====================================================================

This implements an advanced multi-agent product review analysis system with:
- Multiple specialized agents (Coordinator, General Assistant, Data Discovery, Gap Analysis, etc.)
- Agent handoffs between specialists
- Tool calling capabilities for data access, analysis, and visualization
- Streaming support to see each agent's actions
- PNG graph generation with plotly
- State management with Context

Install required packages:
pip install llama-index-core llama-index-llms-openai llama-index-agent-openai plotly kaleido
"""

import asyncio
from typing import Any, Dict, List, Optional

from app.core.config.settings import get_settings
from app.core.llm.workflow.tools import review_analysis_tools
from llama_index.core.agent.workflow import AgentWorkflow, FunctionAgent
from llama_index.core.tools import FunctionTool
from llama_index.core.workflow import Event, StartEvent, StopEvent, Workflow, step, Context
from llama_index.llms.openai import OpenAI

settings = get_settings()

# Get API key from settings
api_key = settings.get_secret("openai_api_key")


# ============================================================================
# Create Agent Workflow with Multiple Specialized Agents
# ============================================================================


def create_product_review_workflow(llm: OpenAI) -> AgentWorkflow:
    """
    Create a multi-agent product review analysis workflow with specialized agents.
    
    Each agent has:
    - Specific tools for their domain
    - A system prompt defining their role
    - Ability to hand off to other agents
    """
    
    # ========================================================================
    # Create Tools
    # ========================================================================
    
    # Data Access Tools
    get_user_datasets_tool = FunctionTool.from_defaults(fn=review_analysis_tools.get_user_datasets)
    get_table_eda_tool = FunctionTool.from_defaults(fn=review_analysis_tools.get_table_eda)
    query_user_reviews_tool = FunctionTool.from_defaults(fn=review_analysis_tools.query_user_reviews_table)
    semantic_search_tool = FunctionTool.from_defaults(fn=review_analysis_tools.semantic_search_reviews)
    get_review_stats_tool = FunctionTool.from_defaults(fn=review_analysis_tools.get_review_statistics)
    
    # Analysis Tools
    detect_gaps_tool = FunctionTool.from_defaults(fn=review_analysis_tools.detect_product_gaps)
    analyze_sentiment_tool = FunctionTool.from_defaults(fn=review_analysis_tools.analyze_sentiment_patterns)
    detect_trends_tool = FunctionTool.from_defaults(fn=review_analysis_tools.detect_trends)
    cluster_reviews_tool = FunctionTool.from_defaults(fn=review_analysis_tools.cluster_reviews)
    extract_keywords_tool = FunctionTool.from_defaults(fn=review_analysis_tools.extract_keywords)
    
    # Visualization Tools
    generate_bar_chart_tool = FunctionTool.from_defaults(fn=review_analysis_tools.generate_bar_chart)
    generate_line_chart_tool = FunctionTool.from_defaults(fn=review_analysis_tools.generate_line_chart)
    generate_pie_chart_tool = FunctionTool.from_defaults(fn=review_analysis_tools.generate_pie_chart)
    generate_heatmap_tool = FunctionTool.from_defaults(fn=review_analysis_tools.generate_heatmap)
    
    # Utility Tools
    get_current_time_tool = FunctionTool.from_defaults(fn=review_analysis_tools.get_current_time)
    format_date_tool = FunctionTool.from_defaults(fn=review_analysis_tools.format_date)
    
    # ========================================================================
    # Coordinator Agent - Routes queries to appropriate specialists
    # ========================================================================
    coordinator_agent = FunctionAgent(
        name="coordinator",
        description="First point of contact. Analyzes query intent and routes to appropriate specialist.",
        system_prompt="""You are an intelligent coordinator for product review analysis. Your role is to:
1. Analyze the user's query to understand their intent
2. Determine if the query requires data analysis or is a general question
3. Route to the appropriate specialist:
   - General Assistant: for simple questions (time, date, general info), greetings, non-data queries
   - Data Discovery Agent: for queries about product reviews, gaps, sentiment, trends, or any data analysis

IMPORTANT: Use your judgment to determine query type. Do NOT use rule-based text matching.
- If the query asks about time, date, or general knowledge → General Assistant
- If the query asks about reviews, gaps, sentiment, trends, or requires data → Data Discovery Agent

When handing off, explain which specialist will help them.
Be concise and helpful.""",
        tools=[get_user_datasets_tool, get_current_time_tool],
        llm=llm,
    )
    
    # ========================================================================
    # General Assistant Agent - Handles non-data queries
    # ========================================================================
    general_assistant_agent = FunctionAgent(
        name="general_assistant",
        description="Handles general questions, time queries, and non-data questions",
        system_prompt="""You are a helpful general assistant. You handle:
1. Time and date queries
2. General questions that don't require data analysis
3. Greetings and casual conversation
4. Questions about how the system works

Be friendly, concise, and helpful.
You do NOT need to hand off to other agents - you can answer directly.""",
        tools=[get_current_time_tool, format_date_tool],
        llm=llm,
    )
    
    # ========================================================================
    # Data Discovery Agent - Discovers datasets and determines data sources
    # ========================================================================
    data_discovery_agent = FunctionAgent(
        name="data_discovery",
        description="Discovers available datasets, retrieves EDA metadata, determines optimal data sources",
        system_prompt="""You are a data discovery specialist. Your role is to:
1. Discover all available datasets for the user
2. Analyze EDA metadata to understand data structure
3. Determine which datasets and tables are relevant for the query
4. Route to appropriate analysis agents:
   - Gap Analysis Agent: for product gaps, unmet needs, feature requests
   - Sentiment Analysis Agent: for sentiment patterns, positive/negative trends
   - Trend Analysis Agent: for temporal trends, patterns over time
   - Clustering Agent: for grouping similar reviews, identifying themes

IMPORTANT: When calling tools that require user_id, get it from workflow context/initial_state.
Always check available datasets first, then analyze EDA metadata to understand the data structure.
Based on the query, determine which analysis agents should be involved.""",
        tools=[get_user_datasets_tool, get_table_eda_tool, query_user_reviews_tool],
        llm=llm,
    )
    
    # ========================================================================
    # Gap Analysis Agent - Identifies product gaps and unmet needs
    # ========================================================================
    gap_analysis_agent = FunctionAgent(
        name="gap_analysis",
        description="Specialist in identifying product gaps, unmet needs, and feature requests",
        system_prompt="""You are a product gap analysis specialist. You help identify:
1. Product gaps and unmet customer needs
2. Feature requests and improvement opportunities
3. Common pain points across reviews
4. Areas where competitors might have advantages

Use semantic search to find relevant reviews, extract keywords, and detect patterns.
After analysis, hand off to Visualization Agent for charts, then to Report Writer for final formatting.
Be thorough and evidence-based in your analysis.""",
        tools=[detect_gaps_tool, semantic_search_tool, extract_keywords_tool, query_user_reviews_tool],
        llm=llm,
    )
    
    # ========================================================================
    # Sentiment Analysis Agent - Analyzes sentiment patterns
    # ========================================================================
    sentiment_analysis_agent = FunctionAgent(
        name="sentiment_analysis",
        description="Specialist in analyzing sentiment patterns and positive/negative trends",
        system_prompt="""You are a sentiment analysis specialist. You analyze:
1. Overall sentiment distribution (positive, neutral, negative)
2. Sentiment by source/platform
3. Sentiment by rating
4. Sentiment trends over time
5. Key positive and negative themes

Use sentiment analysis tools and review statistics.
After analysis, hand off to Visualization Agent for charts, then to Report Writer.
Provide actionable insights about sentiment patterns.""",
        tools=[analyze_sentiment_tool, get_review_stats_tool, query_user_reviews_tool],
        llm=llm,
    )
    
    # ========================================================================
    # Trend Analysis Agent - Detects temporal trends
    # ========================================================================
    trend_analysis_agent = FunctionAgent(
        name="trend_analysis",
        description="Specialist in detecting temporal trends and patterns over time",
        system_prompt="""You are a trend analysis specialist. You detect:
1. Temporal trends in ratings, sentiment, or review volume
2. Patterns over time (daily, weekly, monthly)
3. Seasonal variations
4. Trend direction (improving, declining, stable)

Use trend detection tools and time-series analysis.
After analysis, hand off to Visualization Agent for line charts showing trends.
Provide insights about what trends mean for the product.""",
        tools=[detect_trends_tool, query_user_reviews_tool, get_review_stats_tool],
        llm=llm,
    )
    
    # ========================================================================
    # Clustering Agent - Groups similar reviews
    # ========================================================================
    clustering_agent = FunctionAgent(
        name="clustering",
        description="Specialist in grouping similar reviews and identifying themes",
        system_prompt="""You are a review clustering specialist. You:
1. Group similar reviews into clusters
2. Identify common themes and topics
3. Extract representative reviews for each cluster
4. Analyze keyword patterns within clusters

Use clustering tools and keyword extraction.
After analysis, hand off to Visualization Agent for visualizations, then to Report Writer.
Help users understand the main themes in their review data.""",
        tools=[cluster_reviews_tool, extract_keywords_tool, semantic_search_tool],
        llm=llm,
    )
    
    # ========================================================================
    # Visualization Agent - Generates charts and graphs
    # ========================================================================
    visualization_agent = FunctionAgent(
        name="visualization",
        description="Specialist in generating charts, graphs, and visualizations",
        system_prompt="""You are a data visualization specialist. You create:
1. Bar charts for categorical comparisons
2. Line charts for trends over time
3. Pie charts for distributions
4. Heatmaps for correlation analysis

Choose the appropriate chart type based on the data and analysis needs.
Generate PNG files and return the image paths.

IMPORTANT: 
- When calling visualization tools, you MUST include the user_id parameter (from workflow context/initial_state)
- Visualization tools can automatically access data from previous analysis agents via context_key parameter
- Use context_key to reference stored data (this avoids passing large datasets through tool calls):
  * "gap_analysis_data" for gap analysis bar charts
  * "trend_data" or "sentiment_trend_data" for trend line charts  
  * "sentiment_distribution_data" for sentiment pie charts
  * "cluster_data" for cluster size bar/pie charts
- Example: generate_line_chart(context_key="trend_data", title="Rating Trends", user_id=user_id, x_label="Period", y_label="Average Rating")
- You can also pass data directly, but using context_key is preferred for large datasets and avoids token costs

After creating visualizations, hand off to Report Writer to include them in the final report.
Always create clear, informative visualizations with proper labels and titles.""",
        tools=[
            generate_bar_chart_tool,
            generate_line_chart_tool,
            generate_pie_chart_tool,
            generate_heatmap_tool,
        ],
        llm=llm,
    )
    
    # ========================================================================
    # Report Writer Agent - Formats final markdown reports
    # ========================================================================
    report_writer_agent = FunctionAgent(
        name="report_writer",
        description="Formats comprehensive markdown reports with embedded visualizations",
        system_prompt="""You are a report writing specialist. You create:
1. Well-structured markdown reports
2. Embed visualization images using markdown image syntax: ![Alt Text](image_path)
3. Include executive summaries
4. Format findings with proper headings, lists, and citations
5. Make reports actionable and easy to read

You are the final agent - format all analysis results into a comprehensive report.
Include visualizations where appropriate using markdown image syntax.
Structure the report with clear sections: Summary, Findings, Visualizations, Recommendations.""",
        tools=[],  # No tools - just formats output
        llm=llm,
    )
    
    # ========================================================================
    # Create the Agent Workflow
    # ========================================================================
    workflow = AgentWorkflow(
        agents=[
            coordinator_agent,
            general_assistant_agent,
            data_discovery_agent,
            gap_analysis_agent,
            sentiment_analysis_agent,
            trend_analysis_agent,
            clustering_agent,
            visualization_agent,
            report_writer_agent,
        ],
        root_agent="coordinator",  # Start with coordinator
        timeout=300,  # 5 minutes for complex analysis
    )
    
    return workflow


# ============================================================================
# Custom Workflow for Enhanced Streaming and Visualization
# ============================================================================


class ProductReviewEvent(Event):
    """Custom event to track workflow progress"""
    agent_name: str
    action: str
    details: dict


class StreamingProductReviewWorkflow(Workflow):
    """
    Enhanced workflow that provides detailed streaming of agent actions.
    This wraps the AgentWorkflow to add custom event streaming.
    """
    
    def __init__(self, agent_workflow: AgentWorkflow, user_id: str, **kwargs):
        super().__init__(**kwargs)
        self.agent_workflow = agent_workflow
        self.user_id = user_id
    
    @step
    async def process_request(self, ev: StartEvent) -> StopEvent:
        """Process product review analysis request with detailed streaming"""
        user_msg = ev.get("user_msg")
        
        print(f"\n{'='*80}")
        print(f"🎯 User Query: {user_msg}")
        print(f"{'='*80}\n")
        
        # Create LlamaIndex Context object for this workflow run
        from llama_index.core.workflow import Context
        from app.core.llm.workflow.tools.review_analysis_tools import (
            register_workflow_context,
            clear_workflow_context,
            set_workflow_context_value,
        )
        
        # Clear any previous context for this user
        clear_workflow_context(self.user_id)
        
        # Create Context object and register it
        ctx = Context(self.agent_workflow)
        await ctx.store.set("user_id", self.user_id)
        register_workflow_context(self.user_id, ctx)
        
        # Sync any data from sync store to Context
        from app.core.llm.workflow.tools.review_analysis_tools import _sync_context_store
        if self.user_id in _sync_context_store:
            for key, value in _sync_context_store[self.user_id].items():
                await ctx.store.set(key, value)
        
        # Create a task to run the agent workflow with Context
        handler = self.agent_workflow.run(
            user_msg=user_msg,
            initial_state={"user_id": self.user_id},
            ctx=ctx
        )
        
        current_agent = None
        response_started = False
        
        # Stream events from the agent workflow
        async for event in handler.stream_events():
            # Format and display different event types
            if hasattr(event, 'agent_name'):
                current_agent = event.agent_name
                print(f"\n🤖 Agent: {event.agent_name.upper()}")
            
            if hasattr(event, 'tool_call'):
                tool_call = event.tool_call
                print(f"   🔧 Tool: {tool_call.tool_name}")
                if hasattr(tool_call, 'tool_kwargs'):
                    # Format kwargs nicely
                    kwargs_str = ", ".join(f"{k}={v}" for k, v in tool_call.tool_kwargs.items() if k != 'user_id')
                    print(f"   📝 Args: {kwargs_str}")
            
            if hasattr(event, 'tool_output'):
                output = event.tool_output.content if hasattr(event.tool_output, 'content') else str(event.tool_output)
                # Truncate long outputs
                output_str = str(output)[:200]
                if len(str(output)) > 200:
                    output_str += "..."
                print(f"   ✅ Result: {output_str}")
            
            # Stream the actual response text
            if hasattr(event, 'delta'):
                if not response_started:
                    print(f"\n   💬 Response: ", end='', flush=True)
                    response_started = True
                print(event.delta, end='', flush=True)
            
            if hasattr(event, 'msg'):
                msg = event.msg
                if hasattr(msg, 'content') and msg.content and not response_started:
                    # Fallback if streaming doesn't work
                    print(f"\n   💬 Response: {msg.content}")
        
        if response_started:
            print()  # New line after streaming
        
        # Get final result
        result = await handler
        
        return StopEvent(result=result)


# ============================================================================
# Convenience Functions
# ============================================================================


async def create_and_run_workflow(
    user_msg: str,
    user_id: str,
    llm: Optional[OpenAI] = None
) -> Any:
    """
    Create and run the product review analysis workflow.
    
    Args:
        user_msg: User's query message
        user_id: User ID for data access
        llm: Optional LLM instance (creates default if not provided)
        
    Returns:
        Workflow result
    """
    if llm is None:
        llm = OpenAI(
            model="gpt-4",
            temperature=0.3,
            streaming=True,
            api_key=api_key
        )
    
    # Create the agent workflow
    agent_workflow = create_product_review_workflow(llm)
    
    # Wrap it in our streaming workflow
    workflow = StreamingProductReviewWorkflow(
        agent_workflow=agent_workflow,
        user_id=user_id,
        timeout=300,
        verbose=True
    )
    
    # Run the workflow
    result = await workflow.run(user_msg=user_msg)
    
    return result


# ============================================================================
# Demo / Test Runner
# ============================================================================

async def main():
    """
    Run the multi-agent product review analysis system with test scenarios
    """
    
    # Initialize LLM
    llm = OpenAI(model="gpt-4", temperature=0.3, streaming=True, api_key=api_key)
    
    print("\n" + "="*80)
    print("LLAMAINDEX MULTI-AGENT PRODUCT REVIEW ANALYSIS SYSTEM")
    print("="*80)
    print("\nFeatures:")
    print("  ✓ Multiple specialized agents with handoffs")
    print("  ✓ Real-time streaming of agent actions")
    print("  ✓ Tool calling for data access, analysis, visualization")
    print("  ✓ PNG graph generation with plotly")
    print("  ✓ Context management across agents")
    print("="*80 + "\n")
    
    # Create the agent workflow
    agent_workflow = create_product_review_workflow(llm)
    
    # Wrap it in our streaming workflow for better visibility
    workflow = StreamingProductReviewWorkflow(
        agent_workflow=agent_workflow,
        user_id="test-user-1",
        timeout=300,
        verbose=True
    )
    
    # Test scenarios
    test_queries = [
        "What time is it?",
        "What are my main product gaps?",
        "Show me sentiment trends over time",
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{'█'*80}")
        print(f"TEST SCENARIO {i}/{len(test_queries)}")
        print(f"{'█'*80}")
        
        # Run the workflow
        result = await workflow.run(user_msg=query)
        
        # Pause between scenarios
        if i < len(test_queries):
            await asyncio.sleep(2)
    
    print("\n" + "="*80)
    print("Demo complete! 🎉")
    print("="*80 + "\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user.")
    except Exception as e:
        if "OPENAI_API_KEY" in str(e) or "api_key" in str(e).lower():
            print("\n❌ ERROR: Please set your OPENAI_API_KEY environment variable")
            print("   export OPENAI_API_KEY='your-key-here'")
        else:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()

