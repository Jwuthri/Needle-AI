"""
Tool functions for the Product Review Analysis Workflow.

These tools implement the interface specified in the design document
and return mock data for testing the workflow implementation.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
import uuid

import plotly.graph_objects as go

from app.utils.logging import get_logger

logger = get_logger(__name__)

# Graph output directory
GRAPHS_BASE_DIR = Path(__file__).parent.parent.parent.parent.parent / "data" / "graphs"
GRAPHS_BASE_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================================
# Tool 1: get_user_datasets_with_eda
# ============================================================================


def get_user_datasets_with_eda(user_id: str) -> List[Dict[str, Any]]:
    """
    Retrieve all datasets for a user along with EDA metadata.
    
    This tool returns comprehensive dataset information including:
    - Dataset identification and table names
    - Row counts and date ranges
    - Column statistics (min, max, mean, distinct counts, top values)
    - Data quality insights
    - Summary descriptions
    
    Args:
        user_id: User ID to get datasets for
        
    Returns:
        List of datasets with schema:
        [
            {
                "dataset_id": str,
                "table_name": str,
                "dynamic_table_name": str,
                "row_count": int,
                "description": str,
                "sources": List[str],
                "date_range": {"start": str, "end": str},
                "eda": {
                    "column_stats": {
                        "column_name": {
                            "non_null_count": int,
                            "null_count": int,
                            "dtype": str,
                            "min": Optional[Any],
                            "max": Optional[Any],
                            "mean": Optional[float],
                            "median": Optional[float],
                            "distinct_count": int,
                            "top_values": Optional[Dict[str, int]],
                            "sample_values": List[Any]
                        }
                    },
                    "summary": str,
                    "insights": List[Dict]
                }
            }
        ]
    """
    logger.info(f"Getting datasets with EDA for user {user_id}")
    
    # Mock data matching Netflix review example from requirements
    return [
        {
            "dataset_id": "dataset-netflix-001",
            "table_name": "netflix_reviews",
            "dynamic_table_name": f"__user_{user_id}_netflix_reviews",
            "row_count": 45,
            "description": "Netflix app reviews from App Store and Reddit",
            "sources": ["app_store", "reddit", "trustpilot"],
            "date_range": {
                "start": "2025-09-01",
                "end": "2025-10-15"
            },
            "eda": {
                "column_stats": {
                    "id": {
                        "non_null_count": 45,
                        "null_count": 0,
                        "dtype": "int64",
                        "min": 1,
                        "max": 45,
                        "mean": 23.0,
                        "median": 23.0,
                        "distinct_count": 45,
                        "top_values": None,
                        "sample_values": [1, 2, 3, 4, 5]
                    },
                    "rating": {
                        "non_null_count": 45,
                        "null_count": 0,
                        "dtype": "int64",
                        "min": 1,
                        "max": 5,
                        "mean": 3.0,
                        "median": 3.0,
                        "distinct_count": 5,
                        "top_values": {
                            "2": 12,
                            "3": 10,
                            "4": 10,
                            "1": 8,
                            "5": 5
                        },
                        "sample_values": [1, 2, 3, 4, 5]
                    },
                    "text": {
                        "non_null_count": 45,
                        "null_count": 0,
                        "dtype": "object",
                        "min": None,
                        "max": None,
                        "mean": None,
                        "median": None,
                        "distinct_count": 45,
                        "top_values": {
                            "The UI sometimes feels clunky and slow to respond.": 1,
                            "Great content selection, but the download feature needs work.": 1
                        },
                        "sample_values": [
                            "The UI sometimes feels clunky and slow to respond.",
                            "Great content selection, but the download feature needs work.",
                            "App freezes frequently when navigating between screens."
                        ]
                    },
                    "source": {
                        "non_null_count": 45,
                        "null_count": 0,
                        "dtype": "object",
                        "min": None,
                        "max": None,
                        "mean": None,
                        "median": None,
                        "distinct_count": 3,
                        "top_values": {
                            "app_store": 18,
                            "reddit": 10,
                            "trustpilot": 17
                        },
                        "sample_values": ["app_store", "reddit", "trustpilot"]
                    },
                    "date": {
                        "non_null_count": 45,
                        "null_count": 0,
                        "dtype": "datetime64",
                        "min": "2025-09-01",
                        "max": "2025-10-15",
                        "mean": None,
                        "median": None,
                        "distinct_count": 35,
                        "top_values": None,
                        "sample_values": ["2025-09-15", "2025-09-20", "2025-10-01"]
                    },
                    "author": {
                        "non_null_count": 45,
                        "null_count": 0,
                        "dtype": "object",
                        "min": None,
                        "max": None,
                        "mean": None,
                        "median": None,
                        "distinct_count": 42,
                        "top_values": {
                            "user123": 2,
                            "redditor456": 1
                        },
                        "sample_values": ["user123", "redditor456", "reviewer789"]
                    }
                },
                "summary": "This table stores 45 user review feedback records collected from multiple external sources (App Store, Reddit, Trustpilot). Reviews span from September 1 to October 15, 2025.",
                "insights": [
                    {
                        "field_name": "rating",
                        "data_type": "int",
                        "description": "Numeric rating provided by the reviewer, on a 1-5 scale.",
                        "unique_value_count": 5,
                        "top_values": ["2 (12 reviews)", "3 (10 reviews)", "4 (10 reviews)"],
                        "insight": "Most reviews are 2-4 stars, with 2-star being most common (negative bias)"
                    },
                    {
                        "field_name": "text",
                        "data_type": "text",
                        "description": "Full free-text content of the user's review or feedback.",
                        "unique_value_count": 45,
                        "top_values": None,
                        "insight": "All reviews have unique text content, suitable for semantic analysis"
                    },
                    {
                        "field_name": "source",
                        "data_type": "text",
                        "description": "Platform where the review was collected from.",
                        "unique_value_count": 3,
                        "top_values": ["app_store (18)", "trustpilot (17)", "reddit (10)"],
                        "insight": "Reviews primarily from App Store and Trustpilot"
                    }
                ]
            }
        }
    ]


# ============================================================================
# Tool 2: query_reviews
# ============================================================================


def query_reviews(
    user_id: str,
    table_name: Optional[str] = None,
    rating_filter: Optional[str] = None,
    date_range: Optional[Tuple[str, str]] = None,
    source_filter: Optional[List[str]] = None,
    text_contains: Optional[str] = None,
    limit: int = 1000
) -> Dict[str, Any]:
    """
    Query reviews with filters.
    
    This tool retrieves reviews from the user's dataset with optional filtering.
    It uses EDA metadata to optimize query construction.
    
    Args:
        user_id: User ID
        table_name: Optional specific table name (defaults to main reviews table)
        rating_filter: Rating filter expression (e.g., ">=4", "<=2", "==3")
        date_range: Tuple of (start_date, end_date) in YYYY-MM-DD format
        source_filter: List of sources to filter by (e.g., ["app_store", "reddit"])
        text_contains: Text substring to search for in review text
        limit: Maximum number of results to return (default: 1000)
        
    Returns:
        Dict with schema:
        {
            "reviews": List[Dict],
            "total_count": int,
            "returned_count": int,
            "query_info": {
                "filters_applied": Dict,
                "execution_time_ms": float,
                "table_name": str
            }
        }
    """
    logger.info(f"Querying reviews for user {user_id} with filters: rating={rating_filter}, "
                f"date_range={date_range}, sources={source_filter}, text_contains={text_contains}")
    
    # Mock review data
    all_reviews = [
        {
            "id": 1,
            "company_name": "Netflix",
            "rating": 2,
            "text": "The UI sometimes feels clunky and slow to respond.",
            "source": "app_store",
            "date": "2025-09-15",
            "author": "user123"
        },
        {
            "id": 2,
            "company_name": "Netflix",
            "rating": 4,
            "text": "Great content selection, but the download feature needs work.",
            "source": "reddit",
            "date": "2025-09-20",
            "author": "redditor456"
        },
        {
            "id": 3,
            "company_name": "Netflix",
            "rating": 1,
            "text": "App freezes frequently when navigating between screens.",
            "source": "app_store",
            "date": "2025-09-22",
            "author": "frustrated_user"
        },
        {
            "id": 4,
            "company_name": "Netflix",
            "rating": 5,
            "text": "Love the new profiles feature! Makes sharing with family much easier.",
            "source": "trustpilot",
            "date": "2025-09-25",
            "author": "happy_customer"
        },
        {
            "id": 5,
            "company_name": "Netflix",
            "rating": 2,
            "text": "The download size for movies is too large, quickly fills up my device.",
            "source": "app_store",
            "date": "2025-09-28",
            "author": "storage_issues"
        },
        {
            "id": 6,
            "company_name": "Netflix",
            "rating": 3,
            "text": "Decent app overall, but search functionality could be better.",
            "source": "reddit",
            "date": "2025-10-01",
            "author": "neutral_reviewer"
        },
        {
            "id": 7,
            "company_name": "Netflix",
            "rating": 1,
            "text": "Constant buffering issues even with good internet connection.",
            "source": "trustpilot",
            "date": "2025-10-03",
            "author": "buffering_victim"
        },
        {
            "id": 8,
            "company_name": "Netflix",
            "rating": 4,
            "text": "Original content is excellent, worth the subscription.",
            "source": "app_store",
            "date": "2025-10-05",
            "author": "content_lover"
        },
        {
            "id": 9,
            "company_name": "Netflix",
            "rating": 2,
            "text": "Wish there was an option to sort by release date for new content.",
            "source": "reddit",
            "date": "2025-10-08",
            "author": "feature_requester"
        },
        {
            "id": 10,
            "company_name": "Netflix",
            "rating": 3,
            "text": "Interface is okay but could use some modernization.",
            "source": "trustpilot",
            "date": "2025-10-10",
            "author": "design_critic"
        },
        {
            "id": 11,
            "company_name": "Netflix",
            "rating": 1,
            "text": "App crashes every time I try to download content offline.",
            "source": "app_store",
            "date": "2025-10-12",
            "author": "crash_reporter"
        },
        {
            "id": 12,
            "company_name": "Netflix",
            "rating": 4,
            "text": "Good variety of shows and movies, recommendations are spot on.",
            "source": "reddit",
            "date": "2025-10-14",
            "author": "algo_fan"
        }
    ]
    
    # Apply filters
    filtered_reviews = all_reviews.copy()
    
    # Rating filter
    if rating_filter:
        if rating_filter.startswith(">="):
            threshold = int(rating_filter[2:])
            filtered_reviews = [r for r in filtered_reviews if r["rating"] >= threshold]
        elif rating_filter.startswith("<="):
            threshold = int(rating_filter[2:])
            filtered_reviews = [r for r in filtered_reviews if r["rating"] <= threshold]
        elif rating_filter.startswith("=="):
            threshold = int(rating_filter[2:])
            filtered_reviews = [r for r in filtered_reviews if r["rating"] == threshold]
    
    # Date range filter
    if date_range:
        start_date, end_date = date_range
        filtered_reviews = [
            r for r in filtered_reviews
            if start_date <= r["date"] <= end_date
        ]
    
    # Source filter
    if source_filter:
        filtered_reviews = [r for r in filtered_reviews if r["source"] in source_filter]
    
    # Text contains filter
    if text_contains:
        filtered_reviews = [
            r for r in filtered_reviews
            if text_contains.lower() in r["text"].lower()
        ]
    
    # Apply limit
    returned_reviews = filtered_reviews[:limit]
    
    return {
        "reviews": returned_reviews,
        "total_count": len(filtered_reviews),
        "returned_count": len(returned_reviews),
        "query_info": {
            "filters_applied": {
                "rating_filter": rating_filter,
                "date_range": date_range,
                "source_filter": source_filter,
                "text_contains": text_contains,
                "limit": limit
            },
            "execution_time_ms": 45.2,
            "table_name": table_name or f"__user_{user_id}_reviews"
        }
    }


# ============================================================================
# Tool 3: semantic_search_reviews
# ============================================================================


def semantic_search_reviews(
    user_id: str,
    query_text: str,
    top_k: int = 50,
    rating_filter: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Semantic search using vector embeddings.
    
    This tool performs similarity search on review text using vector embeddings
    stored in PostgreSQL. It returns reviews most semantically similar to the query.
    
    Args:
        user_id: User ID
        query_text: Search query text
        top_k: Number of top results to return (default: 50)
        rating_filter: Optional rating filter (e.g., "<=2" for negative reviews)
        
    Returns:
        List of reviews with similarity scores:
        [
            {
                "id": int,
                "text": str,
                "rating": int,
                "source": str,
                "date": str,
                "author": str,
                "company_name": str,
                "similarity_score": float  # 0.0 to 1.0
            }
        ]
    """
    logger.info(f"Semantic search for user {user_id}: query='{query_text}', top_k={top_k}")
    
    # Mock semantic search results based on query
    # Simulate vector similarity by matching keywords
    query_lower = query_text.lower()
    
    # All possible reviews with simulated similarity scores
    all_reviews_with_scores = [
        {
            "id": 1,
            "text": "The UI sometimes feels clunky and slow to respond.",
            "rating": 2,
            "source": "app_store",
            "date": "2025-09-15",
            "author": "user123",
            "company_name": "Netflix",
            "similarity_score": 0.92 if any(kw in query_lower for kw in ["ui", "slow", "performance", "clunky"]) else 0.45
        },
        {
            "id": 3,
            "text": "App freezes frequently when navigating between screens.",
            "rating": 1,
            "source": "app_store",
            "date": "2025-09-22",
            "author": "frustrated_user",
            "company_name": "Netflix",
            "similarity_score": 0.89 if any(kw in query_lower for kw in ["freeze", "crash", "performance", "slow"]) else 0.42
        },
        {
            "id": 7,
            "text": "Constant buffering issues even with good internet connection.",
            "rating": 1,
            "source": "trustpilot",
            "date": "2025-10-03",
            "author": "buffering_victim",
            "company_name": "Netflix",
            "similarity_score": 0.85 if any(kw in query_lower for kw in ["buffer", "performance", "slow", "issue"]) else 0.38
        },
        {
            "id": 11,
            "text": "App crashes every time I try to download content offline.",
            "rating": 1,
            "source": "app_store",
            "date": "2025-10-12",
            "author": "crash_reporter",
            "company_name": "Netflix",
            "similarity_score": 0.82 if any(kw in query_lower for kw in ["crash", "download", "offline"]) else 0.35
        },
        {
            "id": 5,
            "text": "The download size for movies is too large, quickly fills up my device.",
            "rating": 2,
            "source": "app_store",
            "date": "2025-09-28",
            "author": "storage_issues",
            "company_name": "Netflix",
            "similarity_score": 0.78 if any(kw in query_lower for kw in ["download", "storage", "size", "device"]) else 0.32
        },
        {
            "id": 6,
            "text": "Decent app overall, but search functionality could be better.",
            "rating": 3,
            "source": "reddit",
            "date": "2025-10-01",
            "author": "neutral_reviewer",
            "company_name": "Netflix",
            "similarity_score": 0.75 if any(kw in query_lower for kw in ["search", "find", "discover"]) else 0.40
        },
        {
            "id": 9,
            "text": "Wish there was an option to sort by release date for new content.",
            "rating": 2,
            "source": "reddit",
            "date": "2025-10-08",
            "author": "feature_requester",
            "company_name": "Netflix",
            "similarity_score": 0.72 if any(kw in query_lower for kw in ["sort", "feature", "content", "find"]) else 0.38
        },
        {
            "id": 4,
            "text": "Love the new profiles feature! Makes sharing with family much easier.",
            "rating": 5,
            "source": "trustpilot",
            "date": "2025-09-25",
            "author": "happy_customer",
            "company_name": "Netflix",
            "similarity_score": 0.88 if any(kw in query_lower for kw in ["profile", "feature", "family", "share"]) else 0.30
        },
        {
            "id": 8,
            "text": "Original content is excellent, worth the subscription.",
            "rating": 4,
            "source": "app_store",
            "date": "2025-10-05",
            "author": "content_lover",
            "company_name": "Netflix",
            "similarity_score": 0.80 if any(kw in query_lower for kw in ["content", "original", "show", "movie"]) else 0.35
        },
        {
            "id": 2,
            "text": "Great content selection, but the download feature needs work.",
            "rating": 4,
            "source": "reddit",
            "date": "2025-09-20",
            "author": "redditor456",
            "company_name": "Netflix",
            "similarity_score": 0.76 if any(kw in query_lower for kw in ["content", "download", "feature"]) else 0.42
        }
    ]
    
    # Sort by similarity score
    sorted_reviews = sorted(all_reviews_with_scores, key=lambda x: x["similarity_score"], reverse=True)
    
    # Apply rating filter if provided
    if rating_filter:
        if rating_filter.startswith(">="):
            threshold = int(rating_filter[2:])
            sorted_reviews = [r for r in sorted_reviews if r["rating"] >= threshold]
        elif rating_filter.startswith("<="):
            threshold = int(rating_filter[2:])
            sorted_reviews = [r for r in sorted_reviews if r["rating"] <= threshold]
    
    # Return top_k results
    return sorted_reviews[:top_k]


# ============================================================================
# Tool 4: get_time
# ============================================================================


def get_time() -> Dict[str, Any]:
    """
    Get current time and date.
    
    Simple utility function for handling informational queries about time.
    
    Returns:
        Dict with current time information:
        {
            "current_time": str,  # HH:MM:SS format
            "current_date": str,  # YYYY-MM-DD format
            "current_datetime": str,  # ISO format
            "day_of_week": str,
            "timezone": str
        }
    """
    now = datetime.now()
    
    return {
        "current_time": now.strftime("%H:%M:%S"),
        "current_date": now.strftime("%Y-%m-%d"),
        "current_datetime": now.isoformat(),
        "day_of_week": now.strftime("%A"),
        "timezone": "UTC"
    }


# ============================================================================
# Tool 5: generate_visualization
# ============================================================================


def generate_visualization(
    data: List[Dict[str, Any]],
    chart_type: str,
    title: str,
    labels: Optional[Dict[str, str]] = None,
    user_id: str = "default"
) -> Dict[str, Any]:
    """
    Generate visualization as PNG chart.
    
    This tool creates charts using Plotly and saves them as PNG files
    in the static/visualizations directory.
    
    Args:
        data: Chart data as list of dicts
            - For bar/line charts: [{"x": value, "y": value}, ...]
            - For pie charts: [{"label": str, "value": number}, ...]
        chart_type: Type of chart ("bar", "line", "pie", "scatter")
        title: Chart title
        labels: Optional axis labels {"x": "X Label", "y": "Y Label"}
        user_id: User ID for organizing files (default: "default")
        
    Returns:
        Dict with chart information:
        {
            "chart_type": str,
            "title": str,
            "filepath": str,  # Absolute path to PNG file
            "data_points": int,
            "created_at": str
        }
    """
    logger.info(f"Generating {chart_type} chart: {title}")
    
    labels = labels or {}
    
    # Create user-specific directory
    user_dir = GRAPHS_BASE_DIR / user_id
    user_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()[:50]
    safe_title = safe_title.replace(' ', '_')
    filename = f"{timestamp}_{chart_type}_{safe_title}.png"
    filepath = user_dir / filename
    
    # Create chart based on type
    fig = None
    
    if chart_type == "bar":
        x_values = [item.get("x", item.get("label", "")) for item in data]
        y_values = [item.get("y", item.get("value", 0)) for item in data]
        
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
            xaxis_title=labels.get("x", "Category"),
            yaxis_title=labels.get("y", "Value"),
            template="plotly_white",
            font=dict(size=14),
            height=600,
            width=1000
        )
    
    elif chart_type == "line":
        x_values = [item.get("x", item.get("date", "")) for item in data]
        y_values = [item.get("y", item.get("value", 0)) for item in data]
        
        fig = go.Figure(
            data=[
                go.Scatter(
                    x=x_values,
                    y=y_values,
                    mode="lines+markers",
                    marker=dict(size=8, color="rgb(55, 83, 109)"),
                    line=dict(width=3, color="rgb(55, 83, 109)"),
                )
            ]
        )
        
        fig.update_layout(
            title=title,
            xaxis_title=labels.get("x", "Time"),
            yaxis_title=labels.get("y", "Value"),
            template="plotly_white",
            font=dict(size=14),
            height=600,
            width=1000
        )
    
    elif chart_type == "pie":
        pie_labels = [item.get("label", item.get("name", "")) for item in data]
        values = [item.get("value", item.get("count", 0)) for item in data]
        
        fig = go.Figure(
            data=[
                go.Pie(
                    labels=pie_labels,
                    values=values,
                    hole=0.3,  # Donut chart
                    marker=dict(
                        colors=['rgb(55, 83, 109)', 'rgb(26, 118, 255)', 'rgb(50, 171, 96)']
                    )
                )
            ]
        )
        
        fig.update_layout(
            title=title,
            template="plotly_white",
            font=dict(size=14),
            height=600,
            width=1000
        )
    
    elif chart_type == "scatter":
        x_values = [item.get("x", 0) for item in data]
        y_values = [item.get("y", 0) for item in data]
        
        fig = go.Figure(
            data=[
                go.Scatter(
                    x=x_values,
                    y=y_values,
                    mode="markers",
                    marker=dict(size=10, color="rgb(55, 83, 109)"),
                )
            ]
        )
        
        fig.update_layout(
            title=title,
            xaxis_title=labels.get("x", "X"),
            yaxis_title=labels.get("y", "Y"),
            template="plotly_white",
            font=dict(size=14),
            height=600,
            width=1000
        )
    
    else:
        raise ValueError(f"Unsupported chart type: {chart_type}")
    
    # Save as PNG
    fig.write_image(str(filepath), width=1200, height=800, scale=2)
    
    absolute_path = str(filepath.resolve())
    logger.info(f"Saved {chart_type} chart to {absolute_path}")
    
    return {
        "chart_type": chart_type,
        "title": title,
        "filepath": absolute_path,
        "data_points": len(data),
        "created_at": datetime.now().isoformat()
    }
