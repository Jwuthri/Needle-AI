from datetime import datetime
from pathlib import Path
from app.core.llm.simple_workflow.utils.extract_data_from_ctx_by_key import extract_data_from_ctx_by_key
from app.utils.logging import get_logger

import plotly.graph_objects as go
import pandas as pd
from llama_index.core.workflow import Context
from typing import Any, Dict, List, Optional

logger = get_logger(__name__)

GRAPHS_BASE_DIR = Path(__file__).parent.parent.parent.parent.parent / "data" / "graphs"
GRAPHS_BASE_DIR.mkdir(parents=True, exist_ok=True)


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


async def generate_bar_chart(
    ctx: Context,
    data: List[Dict[str, Any]],
    title: str,
    x_label: str,
    y_label: str,
    user_id: str
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
    
    result = {
        "chart_type": "bar",
        "title": title,
        "path": chart_path,
        "data_points": len(data),
    }
    
    # Save to context
    state = await ctx.store.get("state", {})
    if "graph_data" not in state:
        state["graph_data"] = {}
    state["graph_data"][title] = result
    await ctx.store.set("state", state)
    
    return result


async def generate_line_chart(
    ctx: Context,
    data: List[Dict[str, Any]],
    title: str,
    x_label: str,
    y_label: str,
    user_id: str
) -> Dict[str, Any]:
    """Generate line chart PNG.
    
    Args:
        data: List of dicts with x and y keys
        title: Chart title
        x_label: X-axis label
        y_label: Y-axis label
        user_id: User ID for file path
        
    Returns:
        Dict with chart path and metadata
    """
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
    
    result = {
        "chart_type": "line",
        "title": title,
        "path": chart_path,
        "data_points": len(data),
    }
    
    # Save to context
    state = await ctx.store.get("state", {})
    if "graph_data" not in state:
        state["graph_data"] = {}
    state["graph_data"][title] = result
    await ctx.store.set("state", state)
    
    return result


async def generate_pie_chart(
    ctx: Context,
    data: List[Dict[str, Any]],
    title: str,
    user_id: str
) -> Dict[str, Any]:
    """Generate pie chart PNG.
    
    Args:
        data: List of dicts with label and value keys
        title: Chart title
        user_id: User ID for file path
        
    Returns:
        Dict with chart path and metadata
    """
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
    
    result = {
        "chart_type": "pie",
        "title": title,
        "path": chart_path,
        "data_points": len(data),
    }
    
    # Save to context
    state = await ctx.store.get("state", {})
    if "graph_data" not in state:
        state["graph_data"] = {}
    state["graph_data"][title] = result
    await ctx.store.set("state", state)
    
    return result


async def generate_heatmap(
    ctx: Context,
    data: List[Dict[str, Any]],
    title: str,
    user_id: str
) -> Dict[str, Any]:
    """Generate heatmap PNG.
    
    Args:
        data: List of dicts with x, y, and value keys
        title: Chart title
        user_id: User ID for file path
        
    Returns:
        Dict with chart path and metadata
    """
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
    
    result = {
        "chart_type": "heatmap",
        "title": title,
        "path": chart_path,
        "data_points": len(data),
    }
    
    # Save to context
    state = await ctx.store.get("state", {})
    if "graph_data" not in state:
        state["graph_data"] = {}
    state["graph_data"][title] = result
    await ctx.store.set("state", state)
    
    return result
