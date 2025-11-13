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
from app.utils.logging import get_logger
from app.core.llm.simple_workflow.tools import (
    analyze_sentiment_patterns,
    cluster_reviews,
    detect_product_gaps,
    detect_trends,
    extract_keywords,
    format_date,
    generate_bar_chart,
    generate_heatmap,
    generate_line_chart,
    generate_pie_chart,
    get_current_time,
    get_review_statistics,
    get_table_eda,
    get_user_datasets,
    query_user_reviews_table,
    semantic_search_reviews,
)
from app.database.session import get_async_db_session
from llama_index.core.agent.workflow import AgentWorkflow, FunctionAgent
from llama_index.core.agent.workflow.workflow_events import AgentStream
from llama_index.core.tools import FunctionTool
from llama_index.core.workflow import Event, StartEvent, StopEvent, Workflow, step, Context
from llama_index.llms.openai import OpenAI

settings = get_settings()
logger = get_logger(__name__)

# Get OpenRouter API key from settings
api_key = settings.get_secret("anthropic_api_key")


# ============================================================================
# Create Agent Workflow with Multiple Specialized Agents
# ============================================================================


def create_product_review_workflow(llm: OpenAI, user_id: str = "user_123", ctx: Optional[Context] = None) -> AgentWorkflow:
    """
    Create a multi-agent product review analysis workflow with specialized agents.
    
    Each agent has:
    - Specific tools for their domain
    - A system prompt defining their role
    - Ability to hand off to other agents
    
    Args:
        llm: Language model instance
        user_id: User ID for data access (injected into agent prompts)
        ctx: LlamaIndex Context object for sharing data between tools
    """
    
    # ========================================================================
    # Create Context-Aware Tool Wrappers
    # ========================================================================
    # These wrappers inject the Context into tool calls so tools can
    # store/retrieve data without passing large payloads through LLM tokens
    
    # Data Access Tools
    async def _get_user_datasets(user_id: str) -> Dict[str, Any]:
        """Get all datasets available for a user.
        
        Returns information about all tables the user can analyze, including:
        - Table names
        - Row counts
        - Available columns
        - Data types
        
        Args:
            user_id: The user's ID
            
        Returns:
            Dict containing datasets list and metadata
        """
        return await get_user_datasets(user_id, ctx)
    
    async def _get_table_eda(user_id: str, table_name: str) -> Dict[str, Any]:
        """Get exploratory data analysis (EDA) for a specific table.
        
        Returns statistical summary and insights about the table including:
        - Column statistics (mean, median, std, min, max)
        - Missing values
        - Data distributions
        - Sample rows
        
        Args:
            user_id: The user's ID
            table_name: Name of the table to analyze (e.g., "__user_123_reviews")
            
        Returns:
            Dict with EDA metadata and statistics
        """
        return await get_table_eda(user_id, table_name, ctx)
    
    async def _query_user_reviews_table(user_id: str, query: str, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Query any user dataset table.
        
        Use this to retrieve data from any user table. Works with all dataset types.
        
        Args:
            user_id: The user's ID
            query: Fields to retrieve (comma-separated, e.g., "rating, text, source")
            filters: Optional dict with simple filter keys:
                - "source": Filter by source column
                - "min_rating": Minimum rating value
                - "max_rating": Maximum rating value
                - "date_from": Start date filter
                - "date_to": End date filter
                - "limit": Max results (default: 100)
            
        Returns:
            Dict with query results from the table
        """
        return await query_user_reviews_table(user_id, query, filters, ctx)
    
    async def _semantic_search_reviews(user_id: str, query: str, limit: int = 10) -> Dict[str, Any]:
        """Search any user dataset using semantic similarity.
        
        Finds records similar to the query text using embeddings. Works across all dataset types.
        Use this when looking for specific topics, themes, or content patterns.
        
        Args:
            user_id: The user's ID
            query: Natural language search query (e.g., "battery life issues")
            limit: Max number of results (default: 10)
            
        Returns:
            Dict with similar records and similarity scores
        """
        return await semantic_search_reviews(user_id, query, limit, ctx)
    
    async def _get_review_statistics(user_id: str, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Get aggregate statistics for any user dataset.
        
        Returns summary stats like:
        - Total record count
        - Average ratings/scores
        - Distribution breakdowns
        - Time ranges
        - Source/category breakdowns
        
        Args:
            user_id: The user's ID
            filters: Optional dict with simple filter keys:
                - "source": Filter by source column
                - "min_rating": Minimum rating value
                - "max_rating": Maximum rating value
                - "date_from": Start date
                - "date_to": End date
            
        Returns:
            Dict with aggregate statistics from the dataset
        """
        return await get_review_statistics(user_id, filters, ctx)
    
    # Analysis Tools
    async def _detect_product_gaps(user_id: str, analysis_params: Optional[Dict[str, Any]] = None, table_name: Optional[str] = None) -> Dict[str, Any]:
        """Identify gaps, unmet needs, and frequently mentioned issues in any dataset.
        
        Uses ML to cluster text content and identify frequently mentioned gaps or patterns.
        Works with any user dataset that has text fields.
        Automatically stores results in context with key 'gap_analysis_data' for visualization.
        
        Args:
            user_id: The user's ID
            analysis_params: Optional dict with:
                - min_frequency: Minimum mentions to consider (default: 3)
                - top_n: Number of top gaps to return (default: 10)
            table_name: Optional table name (defaults to main dataset, specify for others)
            
        Returns:
            Dict with detected gaps, frequencies, and representative records
        """
        return await detect_product_gaps(user_id, ctx, analysis_params, table_name)
    
    async def _analyze_sentiment_patterns(user_id: str, filters: Optional[Dict[str, Any]] = None, table_name: Optional[str] = None) -> Dict[str, Any]:
        """Analyze sentiment patterns and trends across any dataset.
        
        Calculates sentiment distribution (positive/neutral/negative) and identifies
        patterns by source, time period, or other attributes.
        Works with any dataset that has text or rating fields.
        Stores results in context with key 'sentiment_distribution_data' for visualization.
        
        Args:
            user_id: The user's ID
            filters: Optional dict with simple filter keys:
                - "source": Filter by source column
                - "min_rating": Minimum rating value
                - "max_rating": Maximum rating value
                - "date_from": Start date
                - "date_to": End date
            table_name: Optional table name (defaults to main dataset, specify for others)
            
        Returns:
            Dict with sentiment breakdown, patterns, and insights
        """
        return await analyze_sentiment_patterns(user_id, ctx, filters, table_name)
    
    async def _detect_trends(user_id: str, time_field: str = "date", metric: str = "rating", period: str = "month", table_name: Optional[str] = None) -> Dict[str, Any]:
        """Detect temporal trends in any dataset metrics over time.
        
        Analyzes how metrics change over time using statistical trend detection.
        Works with any dataset that has time/date fields and numeric metrics.
        Stores results in context with keys 'trend_data' and 'sentiment_trend_data'.
        
        Args:
            user_id: The user's ID
            time_field: Time/date column name (default: "date")
            metric: Metric column to analyze (e.g., "rating", "sentiment", "count")
            period: Grouping period - "day", "week", "month" (default: "month")
            table_name: Optional table name (defaults to main dataset, specify for others)
            
        Returns:
            Dict with trend data, slope, direction, and statistical significance
        """
        return await detect_trends(user_id, ctx, time_field, metric, period, table_name)
    
    async def _cluster_reviews(user_id: str, n_clusters: int = 5, filters: Optional[Dict[str, Any]] = None, table_name: Optional[str] = None) -> Dict[str, Any]:
        """Cluster similar records to identify common themes in any dataset.
        
        Uses KMeans clustering on embeddings to group similar content.
        Works with any dataset that has text fields and embeddings.
        Stores results in context with key 'cluster_data' for visualization.
        
        Args:
            user_id: The user's ID
            n_clusters: Number of clusters to create (default: 5)
            filters: Optional dict with simple filter keys:
                - "source": Filter by source column
                - "min_rating": Minimum rating value
                - "max_rating": Maximum rating value
                - "date_from": Start date
                - "date_to": End date
            table_name: Optional table name (defaults to main dataset, specify for others)
            
        Returns:
            Dict with clusters, themes, sizes, and representative records
        """
        return await cluster_reviews(user_id, ctx, n_clusters, filters, table_name)
    
    async def _extract_keywords(user_id: str, filters: Optional[Dict[str, Any]] = None, top_n: int = 20, table_name: Optional[str] = None) -> Dict[str, Any]:
        """Extract top keywords and phrases from any dataset.
        
        Uses TF-IDF to identify the most important and frequent terms.
        Works with any dataset that has text fields.
        Stores results in context with key 'keyword_data' for visualization.
        
        Args:
            user_id: The user's ID
            filters: Optional dict with simple filter keys:
                - "source": Filter by source column
                - "min_rating": Minimum rating value
                - "max_rating": Maximum rating value  
                - "date_from": Start date
                - "date_to": End date
            top_n: Number of keywords to extract (default: 20)
            table_name: Optional table name (defaults to main dataset, specify for others)
            
        Returns:
            Dict with keywords, frequencies, and TF-IDF scores
        """
        return await extract_keywords(user_id, ctx, filters, top_n, table_name)
    
    # Visualization Tools (these fetch data from Context using context_key)
    async def _generate_bar_chart(
        data: Optional[List[Dict[str, Any]]] = None,
        title: str = "",
        x_label: str = "",
        y_label: str = "",
        user_id: str = "",
        context_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate a bar chart visualization.
        
        IMPORTANT: Use context_key to reference data stored by analysis tools.
        DO NOT pass large datasets directly - reference them from context instead.
        
        Available context keys from analysis tools:
        - 'gap_analysis_data': From detect_product_gaps
        - 'keyword_data': From extract_keywords
        
        Args:
            data: Optional small dataset with [{"x": label, "y": value}] format
            title: Chart title
            x_label: X-axis label
            y_label: Y-axis label
            user_id: User ID for file storage
            context_key: Key to retrieve data from context (preferred method)
            
        Returns:
            Dict with chart_path and chart_url
        """
        return await generate_bar_chart(data, title, x_label, y_label, user_id, context_key, ctx)
    
    async def _generate_line_chart(
        data: Optional[List[Dict[str, Any]]] = None,
        title: str = "",
        x_label: str = "",
        y_label: str = "",
        user_id: str = "",
        context_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate a line chart for time-series or sequential data.
        
        IMPORTANT: Use context_key to reference data stored by analysis tools.
        
        Available context keys from analysis tools:
        - 'trend_data': From detect_trends (rating trends)
        - 'sentiment_trend_data': From detect_trends (sentiment over time)
        
        Args:
            data: Optional small dataset with [{"x": label, "y": value}] format
            title: Chart title
            x_label: X-axis label (e.g., "Month")
            y_label: Y-axis label (e.g., "Average Rating")
            user_id: User ID for file storage
            context_key: Key to retrieve data from context (preferred method)
            
        Returns:
            Dict with chart_path and chart_url
        """
        return await generate_line_chart(data, title, x_label, y_label, user_id, context_key, ctx)
    
    async def _generate_pie_chart(
        data: Optional[List[Dict[str, Any]]] = None,
        title: str = "",
        user_id: str = "",
        context_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate a pie chart for proportional data.
        
        IMPORTANT: Use context_key to reference data stored by analysis tools.
        
        Available context keys from analysis tools:
        - 'sentiment_distribution_data': From analyze_sentiment_patterns
        - 'cluster_data': From cluster_reviews
        
        Args:
            data: Optional small dataset with [{"label": name, "value": count}] format
            title: Chart title
            user_id: User ID for file storage
            context_key: Key to retrieve data from context (preferred method)
            
        Returns:
            Dict with chart_path and chart_url
        """
        return await generate_pie_chart(data, title, user_id, context_key, ctx)
    
    async def _generate_heatmap(
        data: Optional[List[Dict[str, Any]]] = None,
        title: str = "",
        user_id: str = "",
        context_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate a heatmap for 2D data matrices.
        
        IMPORTANT: Use context_key to reference data stored by analysis tools.
        
        Args:
            data: Optional dataset with [{"x": label, "y": label, "value": number}] format
            title: Chart title
            user_id: User ID for file storage
            context_key: Key to retrieve data from context (preferred method)
            
        Returns:
            Dict with chart_path and chart_url
        """
        return await generate_heatmap(data, title, user_id, context_key, ctx)
    
    # Create FunctionTool instances
    get_user_datasets_tool = FunctionTool.from_defaults(fn=_get_user_datasets, async_fn=_get_user_datasets)
    get_table_eda_tool = FunctionTool.from_defaults(fn=_get_table_eda, async_fn=_get_table_eda)
    query_user_reviews_tool = FunctionTool.from_defaults(fn=_query_user_reviews_table, async_fn=_query_user_reviews_table)
    semantic_search_tool = FunctionTool.from_defaults(fn=_semantic_search_reviews, async_fn=_semantic_search_reviews)
    get_review_stats_tool = FunctionTool.from_defaults(fn=_get_review_statistics, async_fn=_get_review_statistics)
    
    # Analysis Tools
    detect_gaps_tool = FunctionTool.from_defaults(fn=_detect_product_gaps, async_fn=_detect_product_gaps)
    analyze_sentiment_tool = FunctionTool.from_defaults(fn=_analyze_sentiment_patterns, async_fn=_analyze_sentiment_patterns)
    detect_trends_tool = FunctionTool.from_defaults(fn=_detect_trends, async_fn=_detect_trends)
    cluster_reviews_tool = FunctionTool.from_defaults(fn=_cluster_reviews, async_fn=_cluster_reviews)
    extract_keywords_tool = FunctionTool.from_defaults(fn=_extract_keywords, async_fn=_extract_keywords)
    
    # Visualization Tools
    generate_bar_chart_tool = FunctionTool.from_defaults(fn=_generate_bar_chart, async_fn=_generate_bar_chart)
    generate_line_chart_tool = FunctionTool.from_defaults(fn=_generate_line_chart, async_fn=_generate_line_chart)
    generate_pie_chart_tool = FunctionTool.from_defaults(fn=_generate_pie_chart, async_fn=_generate_pie_chart)
    generate_heatmap_tool = FunctionTool.from_defaults(fn=_generate_heatmap, async_fn=_generate_heatmap)
    
    # Utility Tools
    get_current_time_tool = FunctionTool.from_defaults(fn=get_current_time)
    format_date_tool = FunctionTool.from_defaults(fn=format_date)
    
    # ========================================================================
    # Coordinator Agent - Routes queries to appropriate specialists
    # ========================================================================
    coordinator_agent = FunctionAgent(
        name="coordinator",
        description="First point of contact. Analyzes query intent and routes to appropriate specialist.",
        system_prompt=f"""You are a coordinator that routes queries to specialists. 

Working with user_id: {user_id}

Route immediately without explanation:
- General Assistant: time, date, general questions, greetings
- Data Discovery Agent: reviews, gaps, sentiment, trends, any data analysis, etc..

CRITICAL RULES:
- NEVER explain handoffs or say "I'll route this to..."
- NEVER ask for data location - tools handle data access
- Just hand off silently - the user sees agent transitions automatically
- If unclear which specialist, pick the most likely one and hand off""",
        tools=[get_user_datasets_tool, get_current_time_tool],
        llm=llm,
    )
    
    # ========================================================================
    # General Assistant Agent - Handles non-data queries
    # ========================================================================
    general_assistant_agent = FunctionAgent(
        name="general_assistant",
        description="Handles general questions, time queries, and non-data questions",
        system_prompt="""Answer time, date, general questions, and greetings directly.

Be concise and helpful. No handoffs needed.""",
        tools=[get_current_time_tool, format_date_tool],
        llm=llm,
    )
    
    # ========================================================================
    # Data Discovery Agent - Discovers datasets and determines data sources
    # ========================================================================
    data_discovery_agent = FunctionAgent(
        name="data_discovery",
        description="Discovers available datasets, retrieves EDA metadata, determines optimal data sources",
        system_prompt="""Discover datasets and route to the right analysis agent.

Workflow:
1. Get user_id from context/initial_state
2. Call get_user_datasets to see available data
3. Call get_table_eda if needed for structure
4. Hand off to specialist:
   - Gap Analysis: product gaps, feature requests
   - Sentiment Analysis: sentiment patterns
   - Trend Analysis: trends over time
   - Clustering: review themes

CRITICAL RULES:
- NEVER ask user for data location or user_id - get from tools/context
- NEVER explain "I'll route to..." - just hand off
- Use tools proactively, don't ask permission
- Hand off immediately after discovery""",
        tools=[get_user_datasets_tool, get_table_eda_tool, query_user_reviews_tool],
        llm=llm,
    )
    
    # ========================================================================
    # Gap Analysis Agent - Identifies product gaps and unmet needs
    # ========================================================================
    gap_analysis_agent = FunctionAgent(
        name="gap_analysis",
        description="Specialist in identifying product gaps, unmet needs, and feature requests",
        system_prompt="""Analyze product gaps and unmet needs.

Use tools to find patterns:
- detect_gaps_tool for gap detection
- semantic_search_reviews for relevant reviews
- extract_keywords for themes
- query_user_reviews_table for data

After analysis, hand off to Visualization for charts.

CRITICAL: 
- Never say "I'll hand off" - just do it
- Never mention user_id in your response
- Focus on findings only""",
        tools=[detect_gaps_tool, semantic_search_tool, extract_keywords_tool, query_user_reviews_tool],
        llm=llm,
    )
    
    # ========================================================================
    # Sentiment Analysis Agent - Analyzes sentiment patterns
    # ========================================================================
    sentiment_analysis_agent = FunctionAgent(
        name="sentiment_analysis",
        description="Specialist in analyzing sentiment patterns and positive/negative trends",
        system_prompt="""Analyze sentiment patterns.

Use tools:
- analyze_sentiment_patterns for distribution
- get_review_statistics for stats
- query_user_reviews_table for data

Then hand off to Visualization.

CRITICAL: 
- Never mention user_id in your response
- Hand off immediately after analysis""",
        tools=[analyze_sentiment_tool, get_review_stats_tool, query_user_reviews_tool],
        llm=llm,
    )
    
    # ========================================================================
    # Trend Analysis Agent - Detects temporal trends
    # ========================================================================
    trend_analysis_agent = FunctionAgent(
        name="trend_analysis",
        description="Specialist in detecting temporal trends and patterns over time",
        system_prompt="""Detect trends over time.

Use tools:
- detect_trends for temporal patterns
- query_user_reviews_table for data
- get_review_statistics for stats

After analysis, hand off to Visualization for line charts.

CRITICAL: 
- Never mention user_id in your response
- Hand off immediately after analysis""",
        tools=[detect_trends_tool, query_user_reviews_tool, get_review_stats_tool],
        llm=llm,
    )
    
    # ========================================================================
    # Clustering Agent - Groups similar reviews
    # ========================================================================
    clustering_agent = FunctionAgent(
        name="clustering",
        description="Specialist in grouping similar reviews and identifying themes",
        system_prompt="""Group reviews into themes.

Use tools:
- cluster_reviews for grouping
- extract_keywords for patterns
- semantic_search_reviews for examples

After analysis, hand off to Visualization.

CRITICAL: 
- Never mention user_id in your response
- Hand off immediately after analysis""",
        tools=[cluster_reviews_tool, extract_keywords_tool, semantic_search_tool],
        llm=llm,
    )
    
    # ========================================================================
    # Visualization Agent - Generates charts and graphs
    # ========================================================================
    visualization_agent = FunctionAgent(
        name="visualization",
        description="Specialist in generating charts, graphs, and visualizations",
        system_prompt="""Generate charts from analysis data.

Chart types:
- Bar: categorical comparisons
- Line: trends over time
- Pie: distributions
- Heatmap: correlations

Get user_id from context/initial_state.
Use context_key for data from previous agents:
- "gap_analysis_data" → bar charts
- "trend_data" → line charts
- "sentiment_distribution_data" → pie charts
- "cluster_data" → cluster charts

CRITICAL: 
- After generating charts, IMMEDIATELY hand off to Report Writer
- Do NOT provide final answers or summaries yourself
- Never mention user_id in your response""",
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
        description="FINAL agent that delivers user-facing responses. Formats analysis results into clear, actionable reports.",
        system_prompt="""You are the FINAL agent that delivers results to the user.

Format analysis into a clear report with:
- Key Findings (bullet points)
- Visualizations (list chart paths)
- Brief recommendations

Keep it concise and actionable.

CRITICAL: 
- You are the ONLY agent that responds to the user
- Never mention user_id
- No handoffs - you are the end of the chain""",
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
        
        # Create Context object
        ctx = Context(self.agent_workflow)
        await ctx.set("user_id", self.user_id)
        
        # Create database session and store in context
        async for db_session in get_async_db_session():
            try:
                await ctx.set("db_session", db_session)
                logger.info(f"Database session created and stored in context for user {self.user_id}")
                
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
                    # Check for agent handoff using either field
                    new_agent = getattr(event, "current_agent_name", None) or getattr(event, "agent_name", None)
                    # if isinstance(event, AgentStream):
                    #     print(f"💭 * {event.raw.get('delta', {}).get('thinking')}")
                    #     print(f"💭 ** {event.thinking_delta}")

                    if new_agent:
                        # Detect and display agent handoff/transition
                        if current_agent and current_agent != new_agent:
                            print(f"\n🔀 Handoff: {current_agent.upper()} → {new_agent.upper()}")
                        elif not current_agent:
                            print(f"\n🤖 Starting Agent: {new_agent.upper()}")
                        
                        current_agent = new_agent
                    
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
                    
                    # Handle thinking/reasoning output from Claude
                    if hasattr(event, 'raw') and isinstance(event.raw, dict):
                        raw_delta = event.raw.get('delta')
                        if raw_delta and hasattr(raw_delta, 'type') and raw_delta.type == 'thinking_delta':
                            if hasattr(raw_delta, 'thinking'):
                                print(f"{raw_delta.thinking}", end='', flush=True)

                if response_started:
                    print()  # New line after streaming
                
                # Get final result
                result = await handler
                
                return StopEvent(result=result)
            finally:
                # Database session automatically closed by context manager
                pass


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
            model="gpt-5-mini",
            temperature=0.1,
            streaming=True,
            api_key=api_key,
            reasoning_effort="low"
        )
    
    # Create temporary Context for agent workflow creation
    # The actual context with DB session will be created in StreamingProductReviewWorkflow
    from llama_index.core.workflow import Workflow as BaseWorkflow
    temp_workflow = BaseWorkflow(timeout=900)
    ctx = Context(temp_workflow)
    
    # Create the agent workflow with user_id and context injected
    agent_workflow = create_product_review_workflow(llm, user_id=user_id, ctx=ctx)
    
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
    from llama_index.llms.openai import OpenAI
    from llama_index.llms.anthropic import Anthropic

    # Get Anthropic API key from settings
    # api_key = settings.get_secret("openai_api_key")
    # # Initialize LLM
    # llm = OpenAI(model="gpt-5", temperature=0.05, streaming=True, api_key=api_key, reasoning_effort="high", max_tokens=10000)
    llm = Anthropic(model="claude-sonnet-4-5", temperature=0.05, api_key=api_key, thinking_dict={'type': 'enabled', 'budget_tokens': 4096}, max_tokens=10000)
    
    print("\n" + "="*80)
    print("LLAMAINDEX MULTI-AGENT PRODUCT REVIEW ANALYSIS SYSTEM")
    print("="*80)
    print("\nFeatures:")
    print("  ✓ Multiple specialized agents with handoffs")
    print("  ✓ Real-time streaming of agent actions")
    print("  ✓ Tool calling for data access, analysis, visualization")
    print("  ✓ PNG graph generation with plotly")
    print("  ✓ Context management across agents")
    print("  ✓ Real database integration with sklearn analysis")
    print("="*80 + "\n")
    
    # Create temporary Context for agent workflow creation
    from llama_index.core.workflow import Workflow as BaseWorkflow
    temp_workflow = BaseWorkflow(timeout=900)
    ctx = Context(temp_workflow)
    
    # Create the agent workflow with user_id and context injected
    test_user_id = "user_123"
    agent_workflow = create_product_review_workflow(llm, user_id=test_user_id, ctx=ctx)
    
    # Wrap it in our streaming workflow for better visibility
    workflow = StreamingProductReviewWorkflow(
        agent_workflow=agent_workflow,
        user_id=test_user_id,
        timeout=900,
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

