"""
Utility tools for product review analysis workflow.

These tools provide helper functions for dates, formatting, etc.
"""

from datetime import datetime
from typing import Any, Dict


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

