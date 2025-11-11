"""
Tool functions for product review analysis workflow.

All tools currently return realistic sample data.
Real database implementation will be added later.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import plotly.graph_objects as go
from plotly.utils import PlotlyJSONEncoder

from app.core.config.settings import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

# Graph output directory - use data directory from project root
GRAPHS_BASE_DIR = Path(__file__).parent.parent.parent.parent.parent / "data" / "graphs"
GRAPHS_BASE_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================================
# Context Store for Sharing Data Between Agents
# ============================================================================

# Workflow-scoped Context registry: {user_id: Context}
# This allows tools to access the LlamaIndex Context object
_workflow_context_registry: Dict[str, Any] = {}

# Sync store for immediate access (synced to Context when available)
# Structure: {user_id: {key: value}}
_sync_context_store: Dict[str, Dict[str, Any]] = {}


def register_workflow_context(user_id: str, ctx: Any) -> None:
    """Register a workflow Context object for a user.
    
    Args:
        user_id: User ID
        ctx: LlamaIndex Context object
    """
    _workflow_context_registry[user_id] = ctx
    logger.debug(f"Registered Context for user {user_id}")


async def get_workflow_context_value(user_id: str, key: str, default: Any = None) -> Any:
    """Get a value from workflow Context.
    
    Args:
        user_id: User ID
        key: Context key
        default: Default value if key not found
        
    Returns:
        Value from context or default
    """
    # First check sync store (for immediate access)
    if user_id in _sync_context_store and key in _sync_context_store[user_id]:
        return _sync_context_store[user_id][key]
    
    # Then check Context registry
    if user_id not in _workflow_context_registry:
        return default
    
    ctx = _workflow_context_registry[user_id]
    try:
        value = await ctx.store.get(key)
        return value if value is not None else default
    except Exception as e:
        logger.warning(f"Failed to get context key '{key}' for user {user_id}: {e}")
        return default


def get_workflow_context_value_sync(user_id: str, key: str, default: Any = None) -> Any:
    """Get a value from workflow Context synchronously (checks sync store first).
    
    Args:
        user_id: User ID
        key: Context key
        default: Default value if key not found
        
    Returns:
        Value from context or default
    """
    # Check sync store first
    if user_id in _sync_context_store and key in _sync_context_store[user_id]:
        return _sync_context_store[user_id][key]
    
    return default


async def set_workflow_context_value(user_id: str, key: str, value: Any) -> None:
    """Set a value in workflow Context.
    
    Args:
        user_id: User ID
        key: Context key
        value: Value to store
    """
    if user_id not in _workflow_context_registry:
        logger.warning(f"No Context registered for user {user_id}, cannot store '{key}'")
        return
    
    ctx = _workflow_context_registry[user_id]
    try:
        await ctx.store.set(key, value)
        logger.debug(f"Stored context key '{key}' for user {user_id}")
    except Exception as e:
        logger.warning(f"Failed to set context key '{key}' for user {user_id}: {e}")


def clear_workflow_context(user_id: str) -> None:
    """Clear workflow context registry and sync store for a user.
    
    Args:
        user_id: User ID
    """
    if user_id in _workflow_context_registry:
        del _workflow_context_registry[user_id]
    if user_id in _sync_context_store:
        del _sync_context_store[user_id]
    logger.debug(f"Cleared context registry and sync store for user {user_id}")


# ============================================================================
# Data Access Tools
# ============================================================================


def get_user_datasets(user_id: str) -> Dict[str, Any]:
    """List all user datasets with metadata.
    
    Args:
        user_id: User ID to get datasets for
        
    Returns:
        Dict with datasets list and metadata
    """
    # Mock data - realistic sample
    return {
        "user_id": user_id,
        "datasets": [
            {
                "id": "dataset-1",
                "table_name": "netflix_reviews",
                "dynamic_table_name": f"__user_{user_id}_netflix_reviews",
                "row_count": 45,
                "description": "Netflix app reviews from App Store and Reddit",
                "sources": ["app_store", "reddit", "trustpilot"],
                "date_range": {"start": "2025-09-01", "end": "2025-10-15"},
            },
            {
                "id": "dataset-2",
                "table_name": "spotify_feedback",
                "dynamic_table_name": f"__user_{user_id}_spotify_feedback",
                "row_count": 120,
                "description": "Spotify user feedback from multiple sources",
                "sources": ["app_store", "forum", "twitter"],
                "date_range": {"start": "2025-08-01", "end": "2025-10-20"},
            },
        ],
        "total_datasets": 2,
        "main_reviews_table": f"__user_{user_id}_reviews",
    }


def get_table_eda(user_id: str, table_name: str) -> Dict[str, Any]:
    """Get EDA metadata for a table.
    
    Args:
        user_id: User ID
        table_name: Table name to get EDA for
        
    Returns:
        Dict with EDA metadata including column_stats, summary, insights
    """
    # Mock EDA data - matching the structure from user's example
    return {
        "id": 1,
        "table_name": table_name,
        "row_count": 45,
        "column_stats": {
            "id": {
                "non_null_count": 45,
                "null_count": 0,
                "dtype": "int64",
                "min": 1.0,
                "max": 45.0,
                "mean": 23.0,
                "median": 23.0,
                "distinct_count": 45,
            },
            "rating": {
                "non_null_count": 45,
                "null_count": 0,
                "dtype": "int64",
                "min": 1.0,
                "max": 5.0,
                "mean": 3.0,
                "median": 3.0,
                "distinct_count": 5,
            },
            "text": {
                "non_null_count": 45,
                "null_count": 0,
                "dtype": "object",
                "distinct_count": 45,
                "top_values": {
                    "The UI sometimes feels clunky and slow to respond.": 1,
                    "The download size for movies is too large, quickly fills up my device.": 1,
                },
            },
            "source": {
                "non_null_count": 45,
                "null_count": 0,
                "dtype": "object",
                "distinct_count": 5,
                "top_values": {
                    "app_store": 18,
                    "reddit": 10,
                    "trustpilot": 9,
                    "forum": 7,
                    "twitter": 1,
                },
            },
        },
        "summary": f"This table stores {45} user review feedback records collected from multiple external sources.",
        "insights": [
            {
                "field_name": "rating",
                "data_type": "int",
                "description": "Numeric rating provided by the reviewer, on a 1-5 scale.",
                "unique_value_count": 5,
            },
            {
                "field_name": "text",
                "data_type": "text",
                "description": "Full free-text content of the user's review or feedback.",
                "unique_value_count": 45,
            },
        ],
    }


def query_user_reviews_table(
    user_id: str, query: str, filters: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Query the __user_{id}_reviews table.
    
    Args:
        user_id: User ID
        query: SQL-like query or natural language query
        filters: Optional filters (source, date_range, rating, etc.)
        
    Returns:
        Dict with query results
    """
    # Mock query results
    filters = filters or {}
    
    return {
        "user_id": user_id,
        "table_name": f"__user_{user_id}_reviews",
        "query": query,
        "filters_applied": filters,
        "results": [
            {
                "id": 1,
                "company_name": "Netflix",
                "rating": 2,
                "text": "The UI sometimes feels clunky and slow to respond.",
                "source": "app_store",
                "date": "2025-09-15",
                "author": "user123",
            },
            {
                "id": 2,
                "company_name": "Netflix",
                "rating": 4,
                "text": "Great content selection, but the download feature needs work.",
                "source": "reddit",
                "date": "2025-09-20",
                "author": "redditor456",
            },
        ],
        "total_count": 45,
        "returned_count": 2,
    }


def semantic_search_reviews(user_id: str, query: str, limit: int = 10) -> Dict[str, Any]:
    """Perform semantic search on reviews using vector embeddings.
    
    Args:
        user_id: User ID
        query: Search query
        limit: Maximum number of results
        
    Returns:
        Dict with search results and similarity scores
    """
    # Mock semantic search results
    return {
        "user_id": user_id,
        "query": query,
        "results": [
            {
                "id": 1,
                "text": "The UI sometimes feels clunky and slow to respond.",
                "rating": 2,
                "source": "app_store",
                "similarity_score": 0.89,
                "company_name": "Netflix",
            },
            {
                "id": 5,
                "text": "App freezes frequently when navigating between screens.",
                "rating": 1,
                "source": "reddit",
                "similarity_score": 0.85,
                "company_name": "Netflix",
            },
        ],
        "total_found": 12,
        "returned_count": 2,
    }


def get_review_statistics(user_id: str, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Get aggregate statistics for reviews.
    
    Args:
        user_id: User ID
        filters: Optional filters
        
    Returns:
        Dict with statistics
    """
    filters = filters or {}
    
    return {
        "user_id": user_id,
        "filters_applied": filters,
        "statistics": {
            "total_reviews": 45,
            "average_rating": 3.2,
            "rating_distribution": {
                "1": 8,
                "2": 12,
                "3": 10,
                "4": 10,
                "5": 5,
            },
            "source_distribution": {
                "app_store": 18,
                "reddit": 10,
                "trustpilot": 9,
                "forum": 7,
                "twitter": 1,
            },
            "sentiment_distribution": {
                "positive": 15,
                "neutral": 10,
                "negative": 20,
            },
            "date_range": {
                "earliest": "2025-09-01",
                "latest": "2025-10-15",
            },
        },
    }


# ============================================================================
# Analysis Tools
# ============================================================================


def detect_product_gaps(user_id: str, analysis_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Identify product gaps, unmet needs, and feature requests.
    
    Args:
        user_id: User ID
        analysis_params: Optional analysis parameters
        
    Returns:
        Dict with detected gaps
    """
    analysis_params = analysis_params or {}
    
    result = {
        "user_id": user_id,
        "gaps_detected": [
            {
                "gap_id": "gap-1",
                "title": "UI Performance Issues",
                "description": "Multiple users report slow UI response times and clunky navigation",
                "frequency": 15,
                "severity": "high",
                "sentiment": "negative",
                "sources": ["app_store", "reddit"],
                "example_reviews": [
                    "The UI sometimes feels clunky and slow to respond.",
                    "App freezes frequently when navigating between screens.",
                ],
            },
            {
                "gap_id": "gap-2",
                "title": "Download Size Management",
                "description": "Users complain about large download sizes filling up device storage",
                "frequency": 8,
                "severity": "medium",
                "sentiment": "negative",
                "sources": ["app_store", "forum"],
                "example_reviews": [
                    "The download size for movies is too large, quickly fills up my device.",
                ],
            },
            {
                "gap_id": "gap-3",
                "title": "Content Discovery",
                "description": "Users want better ways to find and sort content",
                "frequency": 12,
                "severity": "medium",
                "sentiment": "neutral",
                "sources": ["reddit", "trustpilot"],
                "example_reviews": [
                    "Wish there was an option to sort by release date for new content.",
                    "The search function is limited, hard to find obscure titles.",
                ],
            },
        ],
        "total_gaps": 3,
        "analysis_date": datetime.now().isoformat(),
    }
    
    # Store results in sync store (will be synced to Context by workflow)
    if user_id not in _sync_context_store:
        _sync_context_store[user_id] = {}
    
    gap_data = [{"x": gap["title"], "y": gap["frequency"]} for gap in result["gaps_detected"]]
    _sync_context_store[user_id]["gap_analysis_results"] = result
    _sync_context_store[user_id]["gap_analysis_data"] = gap_data
    
    # Try to sync to Context if available (non-blocking)
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(set_workflow_context_value(user_id, "gap_analysis_results", result))
            asyncio.create_task(set_workflow_context_value(user_id, "gap_analysis_data", gap_data))
    except (RuntimeError, AttributeError):
        pass  # Will be synced later by workflow
    
    return result


def analyze_sentiment_patterns(user_id: str, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Analyze sentiment patterns and trends.
    
    Args:
        user_id: User ID
        filters: Optional filters
        
    Returns:
        Dict with sentiment analysis results
    """
    filters = filters or {}
    
    result = {
        "user_id": user_id,
        "filters_applied": filters,
        "sentiment_analysis": {
            "overall_sentiment": {
                "positive": 33.3,
                "neutral": 22.2,
                "negative": 44.4,
            },
            "by_source": {
                "app_store": {"positive": 30, "neutral": 20, "negative": 50},
                "reddit": {"positive": 40, "neutral": 30, "negative": 30},
                "trustpilot": {"positive": 33, "neutral": 22, "negative": 45},
            },
            "by_rating": {
                "1": {"sentiment": "negative", "count": 8},
                "2": {"sentiment": "negative", "count": 12},
                "3": {"sentiment": "neutral", "count": 10},
                "4": {"sentiment": "positive", "count": 10},
                "5": {"sentiment": "positive", "count": 5},
            },
            "trend": "declining",  # positive, declining, stable, improving
            "key_positive_themes": ["content quality", "original shows", "profiles feature"],
            "key_negative_themes": ["UI performance", "download size", "search limitations"],
        },
    }
    
    # Store results in sync store (will be synced to Context by workflow)
    if user_id not in _sync_context_store:
        _sync_context_store[user_id] = {}
    
    sentiment_dist_data = [
        {"label": "Positive", "value": result["sentiment_analysis"]["overall_sentiment"]["positive"]},
        {"label": "Neutral", "value": result["sentiment_analysis"]["overall_sentiment"]["neutral"]},
        {"label": "Negative", "value": result["sentiment_analysis"]["overall_sentiment"]["negative"]},
    ]
    
    _sync_context_store[user_id]["sentiment_analysis_results"] = result
    _sync_context_store[user_id]["sentiment_distribution_data"] = sentiment_dist_data
    
    # Try to sync to Context if available (non-blocking)
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(set_workflow_context_value(user_id, "sentiment_analysis_results", result))
            asyncio.create_task(set_workflow_context_value(user_id, "sentiment_distribution_data", sentiment_dist_data))
    except (RuntimeError, AttributeError):
        pass
    
    return result


def detect_trends(user_id: str, time_field: str = "date", metric: str = "rating") -> Dict[str, Any]:
    """Detect temporal trends in reviews.
    
    Args:
        user_id: User ID
        time_field: Field to use for time analysis
        metric: Metric to analyze (rating, sentiment, etc.)
        
    Returns:
        Dict with trend analysis
    """
    result = {
        "user_id": user_id,
        "time_field": time_field,
        "metric": metric,
        "trends": [
            {
                "period": "2025-09",
                "average_rating": 3.5,
                "review_count": 20,
                "sentiment_score": -0.2,
            },
            {
                "period": "2025-10",
                "average_rating": 2.9,
                "review_count": 25,
                "sentiment_score": -0.4,
            },
        ],
        "overall_trend": "declining",
        "trend_strength": "moderate",
        "insights": [
            "Average rating decreased from 3.5 to 2.9",
            "Review volume increased by 25%",
            "Negative sentiment increased over time",
        ],
    }
    
    # Store results in sync store (will be synced to Context by workflow)
    if user_id not in _sync_context_store:
        _sync_context_store[user_id] = {}
    
    trend_data = [{"x": trend["period"], "y": trend["average_rating"]} for trend in result["trends"]]
    sentiment_trend_data = [{"x": trend["period"], "y": trend["sentiment_score"]} for trend in result["trends"]]
    
    _sync_context_store[user_id]["trend_analysis_results"] = result
    _sync_context_store[user_id]["trend_data"] = trend_data
    _sync_context_store[user_id]["sentiment_trend_data"] = sentiment_trend_data
    
    # Try to sync to Context if available (non-blocking)
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(set_workflow_context_value(user_id, "trend_analysis_results", result))
            asyncio.create_task(set_workflow_context_value(user_id, "trend_data", trend_data))
            asyncio.create_task(set_workflow_context_value(user_id, "sentiment_trend_data", sentiment_trend_data))
    except (RuntimeError, AttributeError):
        pass
    
    return result


def cluster_reviews(user_id: str, n_clusters: int = 5, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Cluster similar reviews to identify themes.
    
    Args:
        user_id: User ID
        n_clusters: Number of clusters to create
        filters: Optional filters
        
    Returns:
        Dict with clustering results
    """
    filters = filters or {}
    
    result = {
        "user_id": user_id,
        "n_clusters": n_clusters,
        "clusters": [
            {
                "cluster_id": 0,
                "theme": "UI/Performance Issues",
                "size": 15,
                "keywords": ["slow", "clunky", "freeze", "lag", "performance"],
                "average_rating": 1.8,
                "representative_review": "The UI sometimes feels clunky and slow to respond.",
            },
            {
                "cluster_id": 1,
                "theme": "Content Discovery",
                "size": 12,
                "keywords": ["search", "find", "discover", "sort", "browse"],
                "average_rating": 2.5,
                "representative_review": "The search function is limited, hard to find obscure titles.",
            },
            {
                "cluster_id": 2,
                "theme": "Download/Storage",
                "size": 8,
                "keywords": ["download", "storage", "size", "space", "device"],
                "average_rating": 2.2,
                "representative_review": "The download size for movies is too large, quickly fills up my device.",
            },
        ],
        "total_reviews_clustered": 35,
    }
    
    # Store results in sync store (will be synced to Context by workflow)
    if user_id not in _sync_context_store:
        _sync_context_store[user_id] = {}
    
    cluster_data = [{"label": cluster["theme"], "value": cluster["size"]} for cluster in result["clusters"]]
    
    _sync_context_store[user_id]["clustering_results"] = result
    _sync_context_store[user_id]["cluster_data"] = cluster_data
    
    # Try to sync to Context if available (non-blocking)
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(set_workflow_context_value(user_id, "clustering_results", result))
            asyncio.create_task(set_workflow_context_value(user_id, "cluster_data", cluster_data))
    except (RuntimeError, AttributeError):
        pass
    
    return result


def extract_keywords(user_id: str, filters: Optional[Dict[str, Any]] = None, top_n: int = 20) -> Dict[str, Any]:
    """Extract top keywords from reviews.
    
    Args:
        user_id: User ID
        filters: Optional filters
        top_n: Number of top keywords to return
        
    Returns:
        Dict with keywords and frequencies
    """
    filters = filters or {}
    
    return {
        "user_id": user_id,
        "top_keywords": [
            {"keyword": "slow", "frequency": 15, "relevance_score": 0.92},
            {"keyword": "clunky", "frequency": 12, "relevance_score": 0.89},
            {"keyword": "download", "frequency": 10, "relevance_score": 0.85},
            {"keyword": "search", "frequency": 9, "relevance_score": 0.82},
            {"keyword": "freeze", "frequency": 8, "relevance_score": 0.80},
        ],
        "total_keywords": top_n,
    }


# ============================================================================
# Visualization Tools
# ============================================================================


def _save_chart_png(fig: go.Figure, user_id: str, chart_type: str, title: str) -> str:
    """Save chart as PNG and return local file path.
    
    Args:
        fig: Plotly figure
        user_id: User ID
        chart_type: Type of chart (bar, line, pie, heatmap)
        title: Chart title
        
    Returns:
        Local file path to saved PNG file
    """
    # Create user-specific directory
    user_dir = GRAPHS_BASE_DIR / user_id
    user_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()[:50]
    safe_title = safe_title.replace(' ', '_')
    filename = f"{timestamp}_{chart_type}_{safe_title}.png"
    filepath = user_dir / filename
    
    # Save as PNG
    fig.write_image(str(filepath), width=1200, height=800, scale=2)
    
    # Return absolute local file path
    absolute_path = str(filepath.resolve())
    logger.info(f"Saved chart to {absolute_path}")
    
    return absolute_path


def generate_bar_chart(
    data: Optional[List[Dict[str, Any]]] = None,
    title: str = "",
    x_label: str = "",
    y_label: str = "",
    user_id: str = "",
    context_key: Optional[str] = None
) -> Dict[str, Any]:
    """Generate bar chart PNG.
    
    Args:
        data: List of dicts with x and y keys (optional, will use context if not provided)
        title: Chart title
        x_label: X-axis label
        y_label: Y-axis label
        user_id: User ID for file path
        context_key: Optional key to look up data in workflow context (e.g., "gap_analysis_data")
        
    Returns:
        Dict with chart path and metadata
    """
    # Try to get data from context if not provided or if data is minimal
    if (not data or len(data) < 3) and context_key and user_id:
        data_from_ctx = get_workflow_context_value_sync(user_id, context_key)
        if data_from_ctx:
            data = data_from_ctx
            logger.info(f"Using data from context key '{context_key}' for bar chart")
    
    # Fallback to provided data or empty
    if not data:
        data = []
    
    # Extract x and y values
    x_values = [item.get("x", item.get("label", "")) for item in data]
    y_values = [item.get("y", item.get("value", 0)) for item in data]
    
    # Create bar chart
    fig = go.Figure(
        data=[
            go.Bar(
                x=x_values,
                y=y_values,
                marker_color="rgb(55, 83, 109)",
            )
        ]
    )
    
    fig.update_layout(
        title=title,
        xaxis_title=x_label,
        yaxis_title=y_label,
        template="plotly_white",
    )
    
    # Save and return path
    chart_path = _save_chart_png(fig, user_id, "bar", title)
    
    return {
        "chart_type": "bar",
        "title": title,
        "path": chart_path,
        "data_points": len(data),
    }


def generate_line_chart(
    data: Optional[List[Dict[str, Any]]] = None,
    title: str = "",
    x_label: str = "",
    y_label: str = "",
    user_id: str = "",
    context_key: Optional[str] = None
) -> Dict[str, Any]:
    """Generate line chart PNG.
    
    Args:
        data: List of dicts with x and y keys (optional, will use context if not provided)
        title: Chart title
        x_label: X-axis label
        y_label: Y-axis label
        user_id: User ID for file path
        context_key: Optional key to look up data in workflow context (e.g., "trend_data", "sentiment_trend_data")
        
    Returns:
        Dict with chart path and metadata
    """
    # Try to get data from context if not provided or if data is minimal
    if (not data or len(data) < 3) and context_key and user_id:
        data_from_ctx = get_workflow_context_value_sync(user_id, context_key)
        if data_from_ctx:
            data = data_from_ctx
            logger.info(f"Using data from context key '{context_key}' for line chart")
    
    # Fallback to provided data or empty
    if not data:
        data = []
    
    # Extract x and y values
    x_values = [item.get("x", item.get("date", "")) for item in data]
    y_values = [item.get("y", item.get("value", 0)) for item in data]
    
    # Create line chart
    fig = go.Figure(
        data=[
            go.Scatter(
                x=x_values,
                y=y_values,
                mode="lines+markers",
                marker_color="rgb(55, 83, 109)",
                line=dict(width=3),
            )
        ]
    )
    
    fig.update_layout(
        title=title,
        xaxis_title=x_label,
        yaxis_title=y_label,
        template="plotly_white",
    )
    
    # Save and return path
    chart_path = _save_chart_png(fig, user_id, "line", title)
    
    return {
        "chart_type": "line",
        "title": title,
        "path": chart_path,
        "data_points": len(data),
    }


def generate_pie_chart(
    data: Optional[List[Dict[str, Any]]] = None,
    title: str = "",
    user_id: str = "",
    context_key: Optional[str] = None
) -> Dict[str, Any]:
    """Generate pie chart PNG.
    
    Args:
        data: List of dicts with label and value keys (optional, will use context if not provided)
        title: Chart title
        user_id: User ID for file path
        context_key: Optional key to look up data in workflow context (e.g., "sentiment_distribution_data")
        
    Returns:
        Dict with chart path and metadata
    """
    # Try to get data from context if not provided or if data is minimal
    if (not data or len(data) < 2) and context_key and user_id:
        data_from_ctx = get_workflow_context_value_sync(user_id, context_key)
        if data_from_ctx:
            data = data_from_ctx
            logger.info(f"Using data from context key '{context_key}' for pie chart")
    
    # Fallback to provided data or empty
    if not data:
        data = []
    
    # Extract labels and values
    labels = [item.get("label", item.get("name", "")) for item in data]
    values = [item.get("value", item.get("count", 0)) for item in data]
    
    # Create pie chart
    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.3,  # Donut chart
            )
        ]
    )
    
    fig.update_layout(title=title, template="plotly_white")
    
    # Save and return path
    chart_path = _save_chart_png(fig, user_id, "pie", title)
    
    return {
        "chart_type": "pie",
        "title": title,
        "path": chart_path,
        "data_points": len(data),
    }


def generate_heatmap(
    data: Optional[List[Dict[str, Any]]] = None,
    title: str = "",
    user_id: str = "",
    context_key: Optional[str] = None
) -> Dict[str, Any]:
    """Generate heatmap PNG.
    
    Args:
        data: List of dicts with x, y, and value keys (optional, will use context if not provided)
        title: Chart title
        user_id: User ID for file path
        context_key: Optional key to look up data in workflow context
        
    Returns:
        Dict with chart path and metadata
    """
    # Try to get data from context if not provided
    if (not data or len(data) < 3) and context_key and user_id:
        data_from_ctx = get_workflow_context_value_sync(user_id, context_key)
        if data_from_ctx:
            data = data_from_ctx
            logger.info(f"Using data from context key '{context_key}' for heatmap")
    
    # Fallback to provided data or empty
    if not data:
        data = []
    
    # Extract data for heatmap
    # Assume data is in format: [{"x": "category1", "y": "metric1", "value": 10}, ...]
    x_values = sorted(set(item.get("x", "") for item in data))
    y_values = sorted(set(item.get("y", "") for item in data))
    
    # Create matrix
    z_matrix = []
    for y in y_values:
        row = []
        for x in x_values:
            value = next(
                (item.get("value", 0) for item in data if item.get("x") == x and item.get("y") == y),
                0,
            )
            row.append(value)
        z_matrix.append(row)
    
    # Create heatmap
    fig = go.Figure(
        data=go.Heatmap(
            z=z_matrix,
            x=x_values,
            y=y_values,
            colorscale="Viridis",
        )
    )
    
    fig.update_layout(title=title, template="plotly_white")
    
    # Save and return path
    chart_path = _save_chart_png(fig, user_id, "heatmap", title)
    
    return {
        "chart_type": "heatmap",
        "title": title,
        "path": chart_path,
        "data_points": len(data),
    }


# ============================================================================
# Utility Tools
# ============================================================================


def get_current_time() -> Dict[str, Any]:
    """Get current time and date.
    
    Returns:
        Dict with current time information
    """
    now = datetime.now()
    return {
        "current_time": now.strftime("%H:%M:%S"),
        "current_date": now.strftime("%Y-%m-%d"),
        "current_datetime": now.isoformat(),
        "timezone": "UTC",
    }


def format_date(date_str: str, format: str = "%Y-%m-%d") -> Dict[str, Any]:
    """Format a date string.
    
    Args:
        date_str: Date string to format
        format: Output format (default: YYYY-MM-DD)
        
    Returns:
        Dict with formatted date
    """
    try:
        # Try parsing common formats
        for fmt in ["%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%d/%m/%Y"]:
            try:
                dt = datetime.strptime(date_str, fmt)
                return {
                    "original": date_str,
                    "formatted": dt.strftime(format),
                    "iso": dt.isoformat(),
                }
            except ValueError:
                continue
        
        raise ValueError(f"Could not parse date: {date_str}")
    except Exception as e:
        return {
            "original": date_str,
            "error": str(e),
        }

