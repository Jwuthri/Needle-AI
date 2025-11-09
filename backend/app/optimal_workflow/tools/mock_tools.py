"""
Mock tools for agent demonstrations.

These tools provide realistic-looking outputs for testing agent functionality
without requiring actual database connections or external services.
"""

import json
import random
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta


# =============================================================================
# SQL TOOLS
# =============================================================================

def execute_query(query: str) -> Dict[str, Any]:
    """
    Execute a SQL query and return results.
    
    Args:
        query: SQL query string to execute
        
    Returns:
        Dictionary with query results including rows and metadata
    """
    # Mock some common query patterns
    query_lower = query.lower()
    
    if "select" not in query_lower:
        return {
            "error": "Invalid query - must be a SELECT statement",
            "rows": []
        }
    
    # Mock product data
    if "product" in query_lower:
        return {
            "rows": [
                {"id": 1, "name": "Laptop Pro", "price": 1299.99, "stock": 45, "category": "Electronics"},
                {"id": 2, "name": "Wireless Mouse", "price": 29.99, "stock": 120, "category": "Electronics"},
                {"id": 3, "name": "Desk Chair", "price": 199.99, "stock": 30, "category": "Furniture"},
                {"id": 4, "name": "Monitor 27in", "price": 349.99, "stock": 60, "category": "Electronics"},
                {"id": 5, "name": "Standing Desk", "price": 599.99, "stock": 15, "category": "Furniture"},
            ],
            "row_count": 5,
            "query_time_ms": random.randint(10, 50)
        }
    
    # Mock sales data
    if "sales" in query_lower or "order" in query_lower:
        return {
            "rows": [
                {"order_id": 1001, "date": "2024-01-15", "amount": 1299.99, "customer_id": 501},
                {"order_id": 1002, "date": "2024-01-16", "amount": 229.98, "customer_id": 502},
                {"order_id": 1003, "date": "2024-01-17", "amount": 949.98, "customer_id": 503},
                {"order_id": 1004, "date": "2024-01-18", "amount": 29.99, "customer_id": 501},
                {"order_id": 1005, "date": "2024-01-19", "amount": 599.99, "customer_id": 504},
            ],
            "row_count": 5,
            "query_time_ms": random.randint(15, 60)
        }
    
    # Mock user data
    if "user" in query_lower or "customer" in query_lower:
        return {
            "rows": [
                {"id": 501, "name": "Alice Johnson", "email": "alice@example.com", "joined": "2023-05-12"},
                {"id": 502, "name": "Bob Smith", "email": "bob@example.com", "joined": "2023-08-20"},
                {"id": 503, "name": "Carol Davis", "email": "carol@example.com", "joined": "2023-11-05"},
                {"id": 504, "name": "David Wilson", "email": "david@example.com", "joined": "2024-01-10"},
            ],
            "row_count": 4,
            "query_time_ms": random.randint(8, 30)
        }
    
    # Generic response
    return {
        "rows": [
            {"column1": "value1", "column2": 100},
            {"column1": "value2", "column2": 200},
        ],
        "row_count": 2,
        "query_time_ms": random.randint(5, 25)
    }


def get_schema(table_name: str) -> Dict[str, Any]:
    """
    Get the schema information for a database table.
    
    Args:
        table_name: Name of the table to inspect
        
    Returns:
        Dictionary with table schema information
    """
    schemas = {
        "products": {
            "columns": [
                {"name": "id", "type": "INTEGER", "nullable": False, "primary_key": True},
                {"name": "name", "type": "VARCHAR(255)", "nullable": False, "primary_key": False},
                {"name": "price", "type": "DECIMAL(10,2)", "nullable": False, "primary_key": False},
                {"name": "stock", "type": "INTEGER", "nullable": False, "primary_key": False},
                {"name": "category", "type": "VARCHAR(100)", "nullable": True, "primary_key": False},
            ],
            "row_count": 150,
            "indexes": ["idx_category", "idx_price"]
        },
        "sales": {
            "columns": [
                {"name": "order_id", "type": "INTEGER", "nullable": False, "primary_key": True},
                {"name": "date", "type": "DATE", "nullable": False, "primary_key": False},
                {"name": "amount", "type": "DECIMAL(10,2)", "nullable": False, "primary_key": False},
                {"name": "customer_id", "type": "INTEGER", "nullable": False, "primary_key": False},
            ],
            "row_count": 5420,
            "indexes": ["idx_date", "idx_customer_id"]
        },
        "users": {
            "columns": [
                {"name": "id", "type": "INTEGER", "nullable": False, "primary_key": True},
                {"name": "name", "type": "VARCHAR(255)", "nullable": False, "primary_key": False},
                {"name": "email", "type": "VARCHAR(255)", "nullable": False, "primary_key": False},
                {"name": "joined", "type": "DATE", "nullable": False, "primary_key": False},
            ],
            "row_count": 1250,
            "indexes": ["idx_email"]
        }
    }
    
    return schemas.get(table_name, {
        "error": f"Table '{table_name}' not found",
        "available_tables": list(schemas.keys())
    })


def count_rows(table_name: str, condition: Optional[str] = None) -> Dict[str, Any]:
    """
    Count rows in a table with optional condition.
    
    Args:
        table_name: Name of the table
        condition: Optional WHERE clause condition
        
    Returns:
        Dictionary with row count
    """
    base_counts = {
        "products": 150,
        "sales": 5420,
        "users": 1250,
        "orders": 3200
    }
    
    if table_name not in base_counts:
        return {"error": f"Table '{table_name}' not found"}
    
    count = base_counts[table_name]
    
    if condition:
        # Mock filtering reduces count
        count = int(count * random.uniform(0.1, 0.5))
    
    return {
        "table": table_name,
        "count": count,
        "condition": condition or "none",
        "query_time_ms": random.randint(5, 15)
    }


# =============================================================================
# ANALYSIS TOOLS
# =============================================================================

def calculate_stats(data: List[float], stat_type: str = "all") -> Dict[str, Any]:
    """
    Calculate statistical measures for a dataset.
    
    Args:
        data: List of numeric values
        stat_type: Type of stats to calculate (all, mean, median, std)
        
    Returns:
        Dictionary with calculated statistics
    """
    if not data:
        return {"error": "Empty dataset provided"}
    
    import statistics
    
    stats = {}
    
    if stat_type in ["all", "mean"]:
        stats["mean"] = round(statistics.mean(data), 2)
    
    if stat_type in ["all", "median"]:
        stats["median"] = round(statistics.median(data), 2)
    
    if stat_type in ["all", "std"]:
        if len(data) > 1:
            stats["std_dev"] = round(statistics.stdev(data), 2)
        else:
            stats["std_dev"] = 0
    
    if stat_type == "all":
        stats["min"] = min(data)
        stats["max"] = max(data)
        stats["count"] = len(data)
    
    return stats


def compare_values(value1: float, value2: float, comparison_type: str = "percentage") -> Dict[str, Any]:
    """
    Compare two values and return the difference.
    
    Args:
        value1: First value
        value2: Second value
        comparison_type: Type of comparison (percentage, absolute, ratio)
        
    Returns:
        Dictionary with comparison results
    """
    result = {
        "value1": value1,
        "value2": value2,
        "absolute_difference": round(value2 - value1, 2)
    }
    
    if comparison_type in ["all", "percentage"]:
        if value1 != 0:
            result["percentage_change"] = round(((value2 - value1) / value1) * 100, 2)
        else:
            result["percentage_change"] = "N/A (division by zero)"
    
    if comparison_type in ["all", "ratio"]:
        if value1 != 0:
            result["ratio"] = round(value2 / value1, 2)
        else:
            result["ratio"] = "N/A (division by zero)"
    
    result["direction"] = "increase" if value2 > value1 else "decrease" if value2 < value1 else "no change"
    
    return result


def find_trends(data_points: List[Dict[str, Any]], x_key: str = "date", y_key: str = "value") -> Dict[str, Any]:
    """
    Identify trends in time-series or sequential data.
    
    Args:
        data_points: List of data points with x and y values
        x_key: Key name for x-axis values
        y_key: Key name for y-axis values
        
    Returns:
        Dictionary with trend analysis
    """
    if len(data_points) < 2:
        return {"error": "Need at least 2 data points for trend analysis"}
    
    values = [point[y_key] for point in data_points if y_key in point]
    
    if not values:
        return {"error": f"No valid values found for key '{y_key}'"}
    
    # Calculate simple trend
    first_half = values[:len(values)//2]
    second_half = values[len(values)//2:]
    
    avg_first = sum(first_half) / len(first_half)
    avg_second = sum(second_half) / len(second_half)
    
    trend = "increasing" if avg_second > avg_first else "decreasing" if avg_second < avg_first else "stable"
    
    # Calculate simple slope
    if len(values) > 1:
        slope = (values[-1] - values[0]) / (len(values) - 1)
    else:
        slope = 0
    
    return {
        "trend": trend,
        "slope": round(slope, 2),
        "first_value": values[0],
        "last_value": values[-1],
        "total_change": round(values[-1] - values[0], 2),
        "data_points": len(values)
    }


# =============================================================================
# UTILITY TOOLS
# =============================================================================

def calculator(expression: str) -> Dict[str, Any]:
    """
    Evaluate a mathematical expression safely.
    
    Args:
        expression: Mathematical expression as string (e.g., "2 + 2 * 3")
        
    Returns:
        Dictionary with calculation result
    """
    try:
        # Safe evaluation - only allow basic math operations
        allowed_chars = set("0123456789+-*/(). ")
        if not all(c in allowed_chars for c in expression):
            return {"error": "Expression contains invalid characters"}
        
        result = eval(expression)
        return {
            "expression": expression,
            "result": result,
            "type": type(result).__name__
        }
    except Exception as e:
        return {
            "error": f"Calculation error: {str(e)}",
            "expression": expression
        }


def weather(location: str, date: Optional[str] = None) -> Dict[str, Any]:
    """
    Get weather information for a location (mock data).
    
    Args:
        location: City or location name
        date: Optional date (YYYY-MM-DD), defaults to today
        
    Returns:
        Dictionary with weather information
    """
    conditions = ["Sunny", "Partly Cloudy", "Cloudy", "Rainy", "Stormy"]
    
    return {
        "location": location,
        "date": date or datetime.now().strftime("%Y-%m-%d"),
        "temperature": random.randint(50, 85),
        "temperature_unit": "F",
        "condition": random.choice(conditions),
        "humidity": random.randint(30, 80),
        "wind_speed": random.randint(5, 25),
        "wind_unit": "mph"
    }


def search(query: str, num_results: int = 5) -> Dict[str, Any]:
    """
    Search for information (mock results).
    
    Args:
        query: Search query string
        num_results: Number of results to return
        
    Returns:
        Dictionary with search results
    """
    mock_results = [
        {
            "title": f"Understanding {query} - Complete Guide",
            "url": f"https://example.com/guide/{query.replace(' ', '-').lower()}",
            "snippet": f"A comprehensive guide to {query} covering all essential aspects...",
            "relevance": 0.95
        },
        {
            "title": f"{query} Best Practices",
            "url": f"https://example.com/practices/{query.replace(' ', '-').lower()}",
            "snippet": f"Learn the best practices for {query} from industry experts...",
            "relevance": 0.88
        },
        {
            "title": f"Introduction to {query}",
            "url": f"https://example.com/intro/{query.replace(' ', '-').lower()}",
            "snippet": f"Get started with {query} in just a few simple steps...",
            "relevance": 0.82
        },
        {
            "title": f"{query} FAQ",
            "url": f"https://example.com/faq/{query.replace(' ', '-').lower()}",
            "snippet": f"Frequently asked questions about {query} answered...",
            "relevance": 0.75
        },
        {
            "title": f"Advanced {query} Techniques",
            "url": f"https://example.com/advanced/{query.replace(' ', '-').lower()}",
            "snippet": f"Take your {query} skills to the next level with advanced techniques...",
            "relevance": 0.70
        }
    ]
    
    return {
        "query": query,
        "results": mock_results[:num_results],
        "total_results": len(mock_results),
        "search_time_ms": random.randint(10, 100)
    }


# =============================================================================
# FORMAT TOOLS
# =============================================================================

def create_table(data: List[Dict[str, Any]], format_type: str = "markdown") -> str:
    """
    Format data as a table.
    
    Args:
        data: List of dictionaries to format as table
        format_type: Output format (markdown, html, ascii)
        
    Returns:
        Formatted table string
    """
    if not data:
        return "No data to display"
    
    headers = list(data[0].keys())
    
    if format_type == "markdown":
        # Create markdown table
        header_row = "| " + " | ".join(headers) + " |"
        separator = "|" + "|".join([" --- " for _ in headers]) + "|"
        data_rows = []
        for row in data:
            row_str = "| " + " | ".join(str(row.get(h, "")) for h in headers) + " |"
            data_rows.append(row_str)
        
        return "\n".join([header_row, separator] + data_rows)
    
    elif format_type == "html":
        html = "<table>\n"
        html += "  <tr>" + "".join(f"<th>{h}</th>" for h in headers) + "</tr>\n"
        for row in data:
            html += "  <tr>" + "".join(f"<td>{row.get(h, '')}</td>" for h in headers) + "</tr>\n"
        html += "</table>"
        return html
    
    else:  # ascii
        # Simple ASCII table
        col_widths = {h: max(len(str(h)), max(len(str(row.get(h, ""))) for row in data)) for h in headers}
        
        header_row = "| " + " | ".join(str(h).ljust(col_widths[h]) for h in headers) + " |"
        separator = "+" + "+".join(["-" * (col_widths[h] + 2) for h in headers]) + "+"
        
        result = [separator, header_row, separator]
        for row in data:
            row_str = "| " + " | ".join(str(row.get(h, "")).ljust(col_widths[h]) for h in headers) + " |"
            result.append(row_str)
        result.append(separator)
        
        return "\n".join(result)


def create_chart(data: List[Dict[str, Any]], chart_type: str = "bar", x_key: str = "x", y_key: str = "y") -> str:
    """
    Create a text-based chart visualization.
    
    Args:
        data: Data points for the chart
        chart_type: Type of chart (bar, line)
        x_key: Key for x-axis values
        y_key: Key for y-axis values
        
    Returns:
        ASCII art chart
    """
    if not data:
        return "No data to chart"
    
    values = [(point.get(x_key, ""), point.get(y_key, 0)) for point in data]
    
    if chart_type == "bar":
        max_val = max(v[1] for v in values)
        scale = 50 / max_val if max_val > 0 else 1
        
        chart = "Bar Chart:\n\n"
        for label, value in values:
            bar = "█" * int(value * scale)
            chart += f"{str(label)[:15]:15s} | {bar} {value}\n"
        
        return chart
    
    else:  # line chart (simple)
        return f"Line chart for {len(data)} data points (visualization not implemented in text)"


def format_markdown(content: str, style: str = "report") -> str:
    """
    Format content as structured markdown.
    
    Args:
        content: Content to format
        style: Markdown style (report, article, list)
        
    Returns:
        Formatted markdown string
    """
    if style == "report":
        return f"""# Report

## Summary
{content}

## Details
Generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""
    
    elif style == "article":
        return f"""# Article

{content}

---
*Published: {datetime.now().strftime("%Y-%m-%d")}*
"""
    
    else:  # list
        lines = content.split("\n")
        return "\n".join([f"- {line}" for line in lines if line.strip()])

