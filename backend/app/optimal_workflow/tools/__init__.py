"""
Tools package for agent testing.

This package provides mock tools for demonstrating agent capabilities
without requiring actual external services or databases.
"""

from app.optimal_workflow.tools.mock_tools import (
    # SQL Tools
    execute_query,
    get_schema,
    count_rows,
    
    # Analysis Tools
    calculate_stats,
    compare_values,
    find_trends,
    
    # Utility Tools
    calculator,
    weather,
    search,
    
    # Format Tools
    create_table,
    create_chart,
    format_markdown,
)

__all__ = [
    # SQL Tools
    "execute_query",
    "get_schema",
    "count_rows",
    
    # Analysis Tools
    "calculate_stats",
    "compare_values",
    "find_trends",
    
    # Utility Tools
    "calculator",
    "weather",
    "search",
    
    # Format Tools
    "create_table",
    "create_chart",
    "format_markdown",
]
