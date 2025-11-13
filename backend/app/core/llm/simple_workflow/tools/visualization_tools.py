"""
Visualization tools for product review analysis workflow.

These tools generate charts and graphs as PNG files.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import plotly.graph_objects as go
from llama_index.core.workflow import Context

from app.utils.logging import get_logger

logger = get_logger(__name__)

# Graph output directory
GRAPHS_BASE_DIR = Path(__file__).parent.parent.parent.parent.parent.parent / "data" / "graphs"
GRAPHS_BASE_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================================
# Helper Functions
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


async def _get_data_from_context(
    ctx: Optional[Context],
    context_key: str,
    default_data: Optional[List[Dict[str, Any]]] = None
) -> List[Dict[str, Any]]:
    """Get data from context or use default.
    
    Args:
        ctx: LlamaIndex Context object
        context_key: Key to look up in context
        default_data: Default data if context lookup fails
        
    Returns:
        List of data dictionaries
    """
    if ctx and context_key:
        try:
            data = await ctx.get(context_key)
            if data:
                logger.info(f"Retrieved data from context key '{context_key}'")
                return data
        except Exception as e:
            logger.warning(f"Failed to get data from context key '{context_key}': {e}")
    
    return default_data or []


# ============================================================================
# Visualization Tools
# ============================================================================


async def generate_bar_chart(
    data: Optional[List[Dict[str, Any]]] = None,
    title: str = "",
    x_label: str = "",
    y_label: str = "",
    user_id: str = "",
    context_key: Optional[str] = None,
    ctx: Optional[Context] = None
) -> Dict[str, Any]:
    """Generate bar chart PNG.
    
    Args:
        data: List of dicts with x and y keys (optional, will use context if not provided)
        title: Chart title
        x_label: X-axis label
        y_label: Y-axis label
        user_id: User ID for file path
        context_key: Optional key to look up data in workflow context (e.g., "gap_analysis_data")
        ctx: LlamaIndex Context object
        
    Returns:
        Dict with chart path and metadata
    """
    try:
        # Try to get data from context if not provided
        if (not data or len(data) < 2) and context_key:
            data = await _get_data_from_context(ctx, context_key, data)
        
        if not data:
            logger.warning("No data provided for bar chart")
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
            template="plotly_dark",
        )
        
        # Save and return path
        chart_path = _save_chart_png(fig, user_id, "bar", title)
        
        return {
            "chart_type": "bar",
            "title": title,
            "path": chart_path,
            "data_points": len(data),
        }
        
    except Exception as e:
        logger.error(f"Error generating bar chart: {e}")
        raise


async def generate_line_chart(
    data: Optional[List[Dict[str, Any]]] = None,
    title: str = "",
    x_label: str = "",
    y_label: str = "",
    user_id: str = "",
    context_key: Optional[str] = None,
    ctx: Optional[Context] = None
) -> Dict[str, Any]:
    """Generate line chart PNG.
    
    Args:
        data: List of dicts with x and y keys (optional, will use context if not provided)
        title: Chart title
        x_label: X-axis label
        y_label: Y-axis label
        user_id: User ID for file path
        context_key: Optional key to look up data in workflow context (e.g., "trend_data", "sentiment_trend_data")
        ctx: LlamaIndex Context object
        
    Returns:
        Dict with chart path and metadata
    """
    try:
        # Try to get data from context if not provided
        if (not data or len(data) < 2) and context_key:
            data = await _get_data_from_context(ctx, context_key, data)
        
        if not data:
            logger.warning("No data provided for line chart")
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
            template="plotly_dark",
        )
        
        # Save and return path
        chart_path = _save_chart_png(fig, user_id, "line", title)
        
        return {
            "chart_type": "line",
            "title": title,
            "path": chart_path,
            "data_points": len(data),
        }
        
    except Exception as e:
        logger.error(f"Error generating line chart: {e}")
        raise


async def generate_pie_chart(
    data: Optional[List[Dict[str, Any]]] = None,
    title: str = "",
    user_id: str = "",
    context_key: Optional[str] = None,
    ctx: Optional[Context] = None
) -> Dict[str, Any]:
    """Generate pie chart PNG.
    
    Args:
        data: List of dicts with label and value keys (optional, will use context if not provided)
        title: Chart title
        user_id: User ID for file path
        context_key: Optional key to look up data in workflow context (e.g., "sentiment_distribution_data")
        ctx: LlamaIndex Context object
        
    Returns:
        Dict with chart path and metadata
    """
    try:
        # Try to get data from context if not provided
        if (not data or len(data) < 2) and context_key:
            data = await _get_data_from_context(ctx, context_key, data)
        
        if not data:
            logger.warning("No data provided for pie chart")
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
        
        fig.update_layout(title=title, template="plotly_dark")
        
        # Save and return path
        chart_path = _save_chart_png(fig, user_id, "pie", title)
        
        return {
            "chart_type": "pie",
            "title": title,
            "path": chart_path,
            "data_points": len(data),
        }
        
    except Exception as e:
        logger.error(f"Error generating pie chart: {e}")
        raise


async def generate_heatmap(
    data: Optional[List[Dict[str, Any]]] = None,
    title: str = "",
    user_id: str = "",
    context_key: Optional[str] = None,
    ctx: Optional[Context] = None
) -> Dict[str, Any]:
    """Generate heatmap PNG.
    
    Args:
        data: List of dicts with x, y, and value keys (optional, will use context if not provided)
        title: Chart title
        user_id: User ID for file path
        context_key: Optional key to look up data in workflow context
        ctx: LlamaIndex Context object
        
    Returns:
        Dict with chart path and metadata
    """
    try:
        # Try to get data from context if not provided
        if (not data or len(data) < 3) and context_key:
            data = await _get_data_from_context(ctx, context_key, data)
        
        if not data:
            logger.warning("No data provided for heatmap")
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
        
        fig.update_layout(title=title, template="plotly_dark")
        
        # Save and return path
        chart_path = _save_chart_png(fig, user_id, "heatmap", title)
        
        return {
            "chart_type": "heatmap",
            "title": title,
            "path": chart_path,
            "data_points": len(data),
        }
        
    except Exception as e:
        logger.error(f"Error generating heatmap: {e}")
        raise


async def generate_scatter_plot(
    data: Optional[List[Dict[str, Any]]] = None,
    title: str = "",
    x_label: str = "",
    y_label: str = "",
    user_id: str = "",
    context_key: Optional[str] = None,
    ctx: Optional[Context] = None
) -> Dict[str, Any]:
    """Generate scatter plot PNG for correlation analysis.
    
    Args:
        data: List of dicts with x and y keys (optional, will use context if not provided)
        title: Chart title
        x_label: X-axis label
        y_label: Y-axis label
        user_id: User ID for file path
        context_key: Optional key to look up data in workflow context
        ctx: LlamaIndex Context object
        
    Returns:
        Dict with chart path and metadata
    """
    try:
        # Try to get data from context if not provided
        if (not data or len(data) < 2) and context_key:
            data = await _get_data_from_context(ctx, context_key, data)
        
        if not data:
            logger.warning("No data provided for scatter plot")
            data = []
        
        # Extract x and y values
        x_values = [item.get("x", 0) for item in data]
        y_values = [item.get("y", 0) for item in data]
        
        # Create scatter plot
        fig = go.Figure(
            data=[
                go.Scatter(
                    x=x_values,
                    y=y_values,
                    mode="markers",
                    marker=dict(
                        size=10,
                        color=y_values,
                        colorscale="Viridis",
                        showscale=True
                    ),
                )
            ]
        )
        
        fig.update_layout(
            title=title,
            xaxis_title=x_label,
            yaxis_title=y_label,
            template="plotly_dark",
        )
        
        # Save and return path
        chart_path = _save_chart_png(fig, user_id, "scatter", title)
        
        return {
            "chart_type": "scatter",
            "title": title,
            "path": chart_path,
            "data_points": len(data),
        }
        
    except Exception as e:
        logger.error(f"Error generating scatter plot: {e}")
        raise


async def generate_box_plot(
    data: Optional[List[Dict[str, Any]]] = None,
    title: str = "",
    x_label: str = "",
    y_label: str = "",
    user_id: str = "",
    context_key: Optional[str] = None,
    ctx: Optional[Context] = None
) -> Dict[str, Any]:
    """Generate box plot PNG for distribution analysis.
    
    Args:
        data: List of dicts with category and value keys (optional, will use context if not provided)
        title: Chart title
        x_label: X-axis label (categories)
        y_label: Y-axis label (values)
        user_id: User ID for file path
        context_key: Optional key to look up data in workflow context
        ctx: LlamaIndex Context object
        
    Returns:
        Dict with chart path and metadata
    """
    try:
        # Try to get data from context if not provided
        if (not data or len(data) < 2) and context_key:
            data = await _get_data_from_context(ctx, context_key, data)
        
        if not data:
            logger.warning("No data provided for box plot")
            data = []
        
        # Group data by category
        categories = {}
        for item in data:
            category = item.get("category", item.get("x", "Unknown"))
            value = item.get("value", item.get("y", 0))
            if category not in categories:
                categories[category] = []
            categories[category].append(value)
        
        # Create box plot
        fig = go.Figure()
        for category, values in categories.items():
            fig.add_trace(go.Box(y=values, name=category, marker_color="rgb(55, 83, 109)"))
        
        fig.update_layout(
            title=title,
            xaxis_title=x_label,
            yaxis_title=y_label,
            template="plotly_dark",
            showlegend=True,
        )
        
        # Save and return path
        chart_path = _save_chart_png(fig, user_id, "box", title)
        
        return {
            "chart_type": "box",
            "title": title,
            "path": chart_path,
            "data_points": len(data),
        }
        
    except Exception as e:
        logger.error(f"Error generating box plot: {e}")
        raise


async def generate_histogram(
    data: Optional[List[Dict[str, Any]]] = None,
    title: str = "",
    x_label: str = "",
    y_label: str = "Count",
    user_id: str = "",
    context_key: Optional[str] = None,
    ctx: Optional[Context] = None
) -> Dict[str, Any]:
    """Generate histogram PNG for frequency distribution.
    
    Args:
        data: List of dicts with value key (optional, will use context if not provided)
        title: Chart title
        x_label: X-axis label
        y_label: Y-axis label
        user_id: User ID for file path
        context_key: Optional key to look up data in workflow context
        ctx: LlamaIndex Context object
        
    Returns:
        Dict with chart path and metadata
    """
    try:
        # Try to get data from context if not provided
        if (not data or len(data) < 2) and context_key:
            data = await _get_data_from_context(ctx, context_key, data)
        
        if not data:
            logger.warning("No data provided for histogram")
            data = []
        
        # Extract values
        values = [item.get("value", item.get("x", 0)) for item in data]
        
        # Create histogram
        fig = go.Figure(
            data=[
                go.Histogram(
                    x=values,
                    marker_color="rgb(55, 83, 109)",
                    nbinsx=20,
                )
            ]
        )
        
        fig.update_layout(
            title=title,
            xaxis_title=x_label,
            yaxis_title=y_label,
            template="plotly_dark",
        )
        
        # Save and return path
        chart_path = _save_chart_png(fig, user_id, "histogram", title)
        
        return {
            "chart_type": "histogram",
            "title": title,
            "path": chart_path,
            "data_points": len(data),
        }
        
    except Exception as e:
        logger.error(f"Error generating histogram: {e}")
        raise


async def generate_area_chart(
    data: Optional[List[Dict[str, Any]]] = None,
    title: str = "",
    x_label: str = "",
    y_label: str = "",
    user_id: str = "",
    context_key: Optional[str] = None,
    ctx: Optional[Context] = None
) -> Dict[str, Any]:
    """Generate area chart PNG for cumulative trends.
    
    Args:
        data: List of dicts with x and y keys (optional, will use context if not provided)
        title: Chart title
        x_label: X-axis label
        y_label: Y-axis label
        user_id: User ID for file path
        context_key: Optional key to look up data in workflow context
        ctx: LlamaIndex Context object
        
    Returns:
        Dict with chart path and metadata
    """
    try:
        # Try to get data from context if not provided
        if (not data or len(data) < 2) and context_key:
            data = await _get_data_from_context(ctx, context_key, data)
        
        if not data:
            logger.warning("No data provided for area chart")
            data = []
        
        # Extract x and y values
        x_values = [item.get("x", item.get("date", "")) for item in data]
        y_values = [item.get("y", item.get("value", 0)) for item in data]
        
        # Create area chart
        fig = go.Figure(
            data=[
                go.Scatter(
                    x=x_values,
                    y=y_values,
                    mode="lines",
                    fill="tozeroy",
                    line=dict(color="rgb(55, 83, 109)", width=3),
                    fillcolor="rgba(55, 83, 109, 0.3)",
                )
            ]
        )
        
        fig.update_layout(
            title=title,
            xaxis_title=x_label,
            yaxis_title=y_label,
            template="plotly_dark",
        )
        
        # Save and return path
        chart_path = _save_chart_png(fig, user_id, "area", title)
        
        return {
            "chart_type": "area",
            "title": title,
            "path": chart_path,
            "data_points": len(data),
        }
        
    except Exception as e:
        logger.error(f"Error generating area chart: {e}")
        raise


async def generate_radar_chart(
    data: Optional[List[Dict[str, Any]]] = None,
    title: str = "",
    user_id: str = "",
    context_key: Optional[str] = None,
    ctx: Optional[Context] = None
) -> Dict[str, Any]:
    """Generate radar/spider chart PNG for multi-dimensional comparison.
    
    Args:
        data: List of dicts with dimension and value keys (optional, will use context if not provided)
        title: Chart title
        user_id: User ID for file path
        context_key: Optional key to look up data in workflow context
        ctx: LlamaIndex Context object
        
    Returns:
        Dict with chart path and metadata
    """
    try:
        # Try to get data from context if not provided
        if (not data or len(data) < 3) and context_key:
            data = await _get_data_from_context(ctx, context_key, data)
        
        if not data:
            logger.warning("No data provided for radar chart")
            data = []
        
        # Extract dimensions and values
        dimensions = [item.get("dimension", item.get("label", "")) for item in data]
        values = [item.get("value", item.get("score", 0)) for item in data]
        
        # Create radar chart
        fig = go.Figure(
            data=go.Scatterpolar(
                r=values,
                theta=dimensions,
                fill="toself",
                line=dict(color="rgb(55, 83, 109)", width=3),
                fillcolor="rgba(55, 83, 109, 0.3)",
            )
        )
        
        fig.update_layout(
            title=title,
            template="plotly_dark",
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, max(values) * 1.1] if values else [0, 10]
                )
            ),
        )
        
        # Save and return path
        chart_path = _save_chart_png(fig, user_id, "radar", title)
        
        return {
            "chart_type": "radar",
            "title": title,
            "path": chart_path,
            "data_points": len(data),
        }
        
    except Exception as e:
        logger.error(f"Error generating radar chart: {e}")
        raise


async def generate_treemap(
    data: Optional[List[Dict[str, Any]]] = None,
    title: str = "",
    user_id: str = "",
    context_key: Optional[str] = None,
    ctx: Optional[Context] = None
) -> Dict[str, Any]:
    """Generate treemap PNG for hierarchical data.
    
    Args:
        data: List of dicts with label, parent, and value keys (optional, will use context if not provided)
        title: Chart title
        user_id: User ID for file path
        context_key: Optional key to look up data in workflow context
        ctx: LlamaIndex Context object
        
    Returns:
        Dict with chart path and metadata
    """
    try:
        # Try to get data from context if not provided
        if (not data or len(data) < 2) and context_key:
            data = await _get_data_from_context(ctx, context_key, data)
        
        if not data:
            logger.warning("No data provided for treemap")
            data = []
        
        # Extract labels, parents, and values
        labels = [item.get("label", item.get("name", "")) for item in data]
        parents = [item.get("parent", "") for item in data]
        values = [item.get("value", item.get("count", 0)) for item in data]
        
        # Create treemap
        fig = go.Figure(
            go.Treemap(
                labels=labels,
                parents=parents,
                values=values,
                marker=dict(colorscale="Viridis"),
            )
        )
        
        fig.update_layout(
            title=title,
            template="plotly_dark",
        )
        
        # Save and return path
        chart_path = _save_chart_png(fig, user_id, "treemap", title)
        
        return {
            "chart_type": "treemap",
            "title": title,
            "path": chart_path,
            "data_points": len(data),
        }
        
    except Exception as e:
        logger.error(f"Error generating treemap: {e}")
        raise


async def generate_waterfall_chart(
    data: Optional[List[Dict[str, Any]]] = None,
    title: str = "",
    x_label: str = "",
    y_label: str = "",
    user_id: str = "",
    context_key: Optional[str] = None,
    ctx: Optional[Context] = None
) -> Dict[str, Any]:
    """Generate waterfall chart PNG for showing cumulative effects.
    
    Args:
        data: List of dicts with label and value keys (optional, will use context if not provided)
        title: Chart title
        x_label: X-axis label
        y_label: Y-axis label
        user_id: User ID for file path
        context_key: Optional key to look up data in workflow context
        ctx: LlamaIndex Context object
        
    Returns:
        Dict with chart path and metadata
    """
    try:
        # Try to get data from context if not provided
        if (not data or len(data) < 2) and context_key:
            data = await _get_data_from_context(ctx, context_key, data)
        
        if not data:
            logger.warning("No data provided for waterfall chart")
            data = []
        
        # Extract labels and values
        labels = [item.get("label", item.get("name", "")) for item in data]
        values = [item.get("value", item.get("change", 0)) for item in data]
        
        # Create waterfall chart
        fig = go.Figure(
            go.Waterfall(
                x=labels,
                y=values,
                connector={"line": {"color": "rgb(63, 63, 63)"}},
                increasing={"marker": {"color": "green"}},
                decreasing={"marker": {"color": "red"}},
                totals={"marker": {"color": "rgb(55, 83, 109)"}},
            )
        )
        
        fig.update_layout(
            title=title,
            xaxis_title=x_label,
            yaxis_title=y_label,
            template="plotly_dark",
        )
        
        # Save and return path
        chart_path = _save_chart_png(fig, user_id, "waterfall", title)
        
        return {
            "chart_type": "waterfall",
            "title": title,
            "path": chart_path,
            "data_points": len(data),
        }
        
    except Exception as e:
        logger.error(f"Error generating waterfall chart: {e}")
        raise

