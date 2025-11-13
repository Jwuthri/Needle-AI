"""
Tool functions for product review analysis workflow.

Organized by category:
- data_access_tools: Query databases and retrieve data
- analysis_tools: ML-based analysis (gaps, sentiment, trends, clustering, keywords)
- visualization_tools: Generate charts and graphs
- utility_tools: Helper functions for dates, formatting, etc.
"""

from .analysis_tools import (
    analyze_sentiment_patterns,
    cluster_reviews,
    detect_product_gaps,
    detect_trends,
    extract_keywords,
)
from .data_access_tools import (
    get_review_statistics,
    get_table_eda,
    get_user_datasets,
    query_user_reviews_table,
    semantic_search_reviews,
)
from .utility_tools import format_date, get_current_time
from .visualization_tools import (
    generate_bar_chart,
    generate_heatmap,
    generate_line_chart,
    generate_pie_chart,
)

__all__ = [
    # Data access tools
    "get_user_datasets",
    "get_table_eda",
    "query_user_reviews_table",
    "semantic_search_reviews",
    "get_review_statistics",
    # Analysis tools
    "detect_product_gaps",
    "analyze_sentiment_patterns",
    "detect_trends",
    "cluster_reviews",
    "extract_keywords",
    # Visualization tools
    "generate_bar_chart",
    "generate_line_chart",
    "generate_pie_chart",
    "generate_heatmap",
    # Utility tools
    "get_current_time",
    "format_date",
]

