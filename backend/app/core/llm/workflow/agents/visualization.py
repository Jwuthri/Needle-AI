"""
Visualization Agent for Product Review Analysis Workflow.

The Visualization Agent generates charts and graphs from analysis results
using Plotly, supporting multiple chart types with consistent styling.
"""

from pathlib import Path
from typing import Any, Callable, Dict, Optional
import uuid
import asyncio

from app.database.repositories.chat_message_step import ChatMessageStepRepository
from app.models.workflow import ExecutionContext, VisualizationResult
from app.utils.logging import get_logger
from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)


class VisualizationAgent:
    """
    Specialized agent for generating visualizations from analysis data.
    
    The Visualization Agent:
    1. Generates charts using Plotly library
    2. Supports bar, line, pie, scatter, and heatmap chart types
    3. Applies consistent styling and templates
    4. Saves charts as PNG files with unique identifiers
    5. Returns file paths for embedding in responses
    6. Tracks visualization metadata in Chat Message Steps
    """
    
    def __init__(
        self,
        output_dir: str = "backend/data/graphs",
        stream_callback: Optional[Callable] = None
    ):
        """
        Initialize the Visualization Agent.
        
        Args:
            output_dir: Directory to save visualization files
            stream_callback: Optional callback for streaming events
        """
        self.output_dir = Path(output_dir)
        self.stream_callback = stream_callback
        
        # Create output directory if it doesn't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Initialized VisualizationAgent with output_dir={output_dir}")
    
    async def generate_visualization(
        self,
        data: Dict[str, Any],
        chart_type: str,
        title: str,
        labels: Optional[Dict[str, str]] = None,
        context: Optional[ExecutionContext] = None,
        db: Optional[AsyncSession] = None,
        step_order: Optional[int] = None
    ) -> VisualizationResult:
        """
        Generate a visualization from data.
        
        This method:
        1. Validates input data and chart type
        2. Creates Plotly figure based on chart type
        3. Applies consistent styling
        4. Saves as PNG file
        5. Tracks metadata in Chat Message Steps
        
        Args:
            data: Data for visualization (must include 'x' and 'y' keys)
            chart_type: Type of chart (bar, line, pie, scatter, heatmap)
            title: Chart title
            labels: Optional axis labels (e.g., {"x": "Date", "y": "Count"})
            context: Optional execution context for tracking
            db: Optional database session for tracking
            step_order: Optional step order for tracking
            
        Returns:
            VisualizationResult with file path and metadata
            
        Raises:
            ValueError: If data format is invalid or chart type is unsupported
        """
        logger.info(f"Generating {chart_type} visualization: {title}")
        
        # Emit step start event
        await self._emit_event("agent_step_start", {
            "agent_name": "visualization",
            "action": "generate_visualization",
            "chart_type": chart_type,
            "title": title
        })
        
        try:
            # Validate chart type
            supported_types = ["bar", "line", "pie", "scatter", "heatmap"]
            if chart_type not in supported_types:
                raise ValueError(
                    f"Unsupported chart type: {chart_type}. "
                    f"Supported types: {', '.join(supported_types)}"
                )
            
            # Validate data format
            self._validate_data(data, chart_type)
            
            # Generate unique filename
            viz_id = str(uuid.uuid4())[:8]
            # Create safe filename from title
            safe_title = "".join(c if c.isalnum() or c in (' ', '_', '-') else '_' for c in title)
            safe_title = safe_title.replace(' ', '_')[:50]
            filename = f"{viz_id}_{chart_type}_{safe_title}.png"
            
            # Determine user-specific subdirectory if context available
            if context:
                user_dir = self.output_dir / f"user_{context.user_id}"
                user_dir.mkdir(parents=True, exist_ok=True)
                filepath = user_dir / filename
            else:
                filepath = self.output_dir / filename
            
            # Generate chart based on type
            if chart_type == "bar":
                await self._generate_bar_chart(data, title, labels, filepath)
            elif chart_type == "line":
                await self._generate_line_chart(data, title, labels, filepath)
            elif chart_type == "pie":
                await self._generate_pie_chart(data, title, filepath)
            elif chart_type == "scatter":
                await self._generate_scatter_chart(data, title, labels, filepath)
            elif chart_type == "heatmap":
                await self._generate_heatmap(data, title, labels, filepath)
            
            # Create result
            relative_path = f"/static/visualizations/{filepath.relative_to(self.output_dir)}"
            
            # Calculate data points based on chart type
            if chart_type == "pie":
                data_points = len(data.get("labels", []))
            elif chart_type == "heatmap":
                data_points = len(data.get("z", []))
            else:
                data_points = len(data.get("x", []))
            
            result = VisualizationResult(
                filepath=relative_path,
                chart_type=chart_type,
                title=title,
                metadata={
                    "filename": filename,
                    "viz_id": viz_id,
                    "data_points": data_points
                }
            )
            
            # Track in Chat Message Steps if context provided
            if context and db and step_order is not None:
                await ChatMessageStepRepository.create(
                    db=db,
                    message_id=context.message_id,
                    agent_name="visualization",
                    step_order=step_order,
                    thought=f"Generated {chart_type} chart: {title}",
                    structured_output={
                        "chart_type": chart_type,
                        "title": title,
                        "filepath": relative_path,
                        "viz_id": viz_id
                    }
                )
            
            # Emit step complete event
            await self._emit_event("agent_step_complete", {
                "agent_name": "visualization",
                "action": "generate_visualization",
                "success": True,
                "filepath": relative_path,
                "chart_type": chart_type
            })
            
            logger.info(f"Generated visualization: {relative_path}")
            return result
            
        except Exception as e:
            logger.error(f"Error generating visualization: {e}", exc_info=True)
            
            # Emit error event
            await self._emit_event("agent_step_error", {
                "agent_name": "visualization",
                "action": "generate_visualization",
                "error": str(e),
                "chart_type": chart_type
            })
            
            # Track error in Chat Message Steps if context provided
            if context and db and step_order is not None:
                await ChatMessageStepRepository.create(
                    db=db,
                    message_id=context.message_id,
                    agent_name="visualization",
                    step_order=step_order,
                    thought=f"Failed to generate {chart_type} chart: {str(e)}"
                )
            
            raise
    
    def _validate_data(
        self,
        data: Dict[str, Any],
        chart_type: str
    ) -> None:
        """
        Validate data format for the specified chart type.
        
        Args:
            data: Data dictionary to validate
            chart_type: Type of chart
            
        Raises:
            ValueError: If data format is invalid
        """
        if chart_type in ["bar", "line", "scatter"]:
            if "x" not in data or "y" not in data:
                raise ValueError(f"{chart_type} chart requires 'x' and 'y' data")
            if not isinstance(data["x"], list) or not isinstance(data["y"], list):
                raise ValueError(f"{chart_type} chart 'x' and 'y' must be lists")
            if len(data["x"]) != len(data["y"]):
                raise ValueError(f"{chart_type} chart 'x' and 'y' must have same length")
            if len(data["x"]) == 0:
                raise ValueError(f"{chart_type} chart requires at least one data point")
        
        elif chart_type == "pie":
            if "labels" not in data or "values" not in data:
                raise ValueError("Pie chart requires 'labels' and 'values' data")
            if not isinstance(data["labels"], list) or not isinstance(data["values"], list):
                raise ValueError("Pie chart 'labels' and 'values' must be lists")
            if len(data["labels"]) != len(data["values"]):
                raise ValueError("Pie chart 'labels' and 'values' must have same length")
            if len(data["labels"]) == 0:
                raise ValueError("Pie chart requires at least one data point")
        
        elif chart_type == "heatmap":
            if "z" not in data:
                raise ValueError("Heatmap requires 'z' data (2D array)")
            if not isinstance(data["z"], list):
                raise ValueError("Heatmap 'z' must be a list")
            if len(data["z"]) == 0:
                raise ValueError("Heatmap requires at least one row")
    
    async def _generate_bar_chart(
        self,
        data: Dict[str, Any],
        title: str,
        labels: Optional[Dict[str, str]],
        filepath: Path
    ) -> None:
        """
        Generate a bar chart.
        
        Args:
            data: Data with 'x' and 'y' keys
            title: Chart title
            labels: Optional axis labels
            filepath: Path to save the chart
        """
        # Import plotly here to avoid import errors if not installed
        try:
            import plotly.graph_objects as go
        except ImportError:
            raise ImportError("plotly is required for visualization. Install with: pip install plotly kaleido")
        
        # Create figure
        fig = go.Figure(data=[
            go.Bar(
                x=data["x"],
                y=data["y"],
                name=data.get("name", ""),
                marker=dict(
                    color=data.get("color", "#4A90E2"),
                    line=dict(color="#2E5C8A", width=1)
                )
            )
        ])
        
        # Update layout with consistent styling
        fig.update_layout(
            title=dict(
                text=title,
                font=dict(size=18, family="Arial, sans-serif", color="#333")
            ),
            xaxis_title=labels.get("x", "X") if labels else "X",
            yaxis_title=labels.get("y", "Y") if labels else "Y",
            template="plotly_white",
            font=dict(family="Arial, sans-serif", size=12, color="#555"),
            plot_bgcolor="white",
            paper_bgcolor="white",
            margin=dict(l=60, r=40, t=80, b=60),
            height=500,
            width=800
        )
        
        # Add grid
        fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor="#E0E0E0")
        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor="#E0E0E0")
        
        # Save as PNG
        await asyncio.to_thread(fig.write_image, str(filepath))
        logger.debug(f"Saved bar chart to {filepath}")
    
    async def _generate_line_chart(
        self,
        data: Dict[str, Any],
        title: str,
        labels: Optional[Dict[str, str]],
        filepath: Path
    ) -> None:
        """
        Generate a line chart.
        
        Args:
            data: Data with 'x' and 'y' keys
            title: Chart title
            labels: Optional axis labels
            filepath: Path to save the chart
        """
        try:
            import plotly.graph_objects as go
        except ImportError:
            raise ImportError("plotly is required for visualization. Install with: pip install plotly kaleido")
        
        # Create figure
        fig = go.Figure(data=[
            go.Scatter(
                x=data["x"],
                y=data["y"],
                mode="lines+markers",
                name=data.get("name", ""),
                line=dict(color=data.get("color", "#4A90E2"), width=3),
                marker=dict(size=8, color=data.get("color", "#4A90E2"))
            )
        ])
        
        # Update layout
        fig.update_layout(
            title=dict(
                text=title,
                font=dict(size=18, family="Arial, sans-serif", color="#333")
            ),
            xaxis_title=labels.get("x", "X") if labels else "X",
            yaxis_title=labels.get("y", "Y") if labels else "Y",
            template="plotly_white",
            font=dict(family="Arial, sans-serif", size=12, color="#555"),
            plot_bgcolor="white",
            paper_bgcolor="white",
            margin=dict(l=60, r=40, t=80, b=60),
            height=500,
            width=800
        )
        
        # Add grid
        fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor="#E0E0E0")
        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor="#E0E0E0")
        
        # Save as PNG
        await asyncio.to_thread(fig.write_image, str(filepath))
        logger.debug(f"Saved line chart to {filepath}")
    
    async def _generate_pie_chart(
        self,
        data: Dict[str, Any],
        title: str,
        filepath: Path
    ) -> None:
        """
        Generate a pie chart.
        
        Args:
            data: Data with 'labels' and 'values' keys
            title: Chart title
            filepath: Path to save the chart
        """
        try:
            import plotly.graph_objects as go
        except ImportError:
            raise ImportError("plotly is required for visualization. Install with: pip install plotly kaleido")
        
        # Create figure
        fig = go.Figure(data=[
            go.Pie(
                labels=data["labels"],
                values=data["values"],
                hole=0.3,  # Donut chart style
                marker=dict(
                    colors=data.get("colors", None),
                    line=dict(color="white", width=2)
                ),
                textinfo="label+percent",
                textfont=dict(size=12)
            )
        ])
        
        # Update layout
        fig.update_layout(
            title=dict(
                text=title,
                font=dict(size=18, family="Arial, sans-serif", color="#333")
            ),
            template="plotly_white",
            font=dict(family="Arial, sans-serif", size=12, color="#555"),
            paper_bgcolor="white",
            margin=dict(l=40, r=40, t=80, b=40),
            height=500,
            width=800,
            showlegend=True,
            legend=dict(
                orientation="v",
                yanchor="middle",
                y=0.5,
                xanchor="left",
                x=1.05
            )
        )
        
        # Save as PNG
        await asyncio.to_thread(fig.write_image, str(filepath))
        logger.debug(f"Saved pie chart to {filepath}")
    
    async def _generate_scatter_chart(
        self,
        data: Dict[str, Any],
        title: str,
        labels: Optional[Dict[str, str]],
        filepath: Path
    ) -> None:
        """
        Generate a scatter plot.
        
        Args:
            data: Data with 'x' and 'y' keys
            title: Chart title
            labels: Optional axis labels
            filepath: Path to save the chart
        """
        try:
            import plotly.graph_objects as go
        except ImportError:
            raise ImportError("plotly is required for visualization. Install with: pip install plotly kaleido")
        
        # Create figure
        fig = go.Figure(data=[
            go.Scatter(
                x=data["x"],
                y=data["y"],
                mode="markers",
                name=data.get("name", ""),
                marker=dict(
                    size=data.get("size", 10),
                    color=data.get("color", "#4A90E2"),
                    opacity=0.7,
                    line=dict(color="white", width=1)
                )
            )
        ])
        
        # Update layout
        fig.update_layout(
            title=dict(
                text=title,
                font=dict(size=18, family="Arial, sans-serif", color="#333")
            ),
            xaxis_title=labels.get("x", "X") if labels else "X",
            yaxis_title=labels.get("y", "Y") if labels else "Y",
            template="plotly_white",
            font=dict(family="Arial, sans-serif", size=12, color="#555"),
            plot_bgcolor="white",
            paper_bgcolor="white",
            margin=dict(l=60, r=40, t=80, b=60),
            height=500,
            width=800
        )
        
        # Add grid
        fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor="#E0E0E0")
        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor="#E0E0E0")
        
        # Save as PNG
        await asyncio.to_thread(fig.write_image, str(filepath))
        logger.debug(f"Saved scatter chart to {filepath}")
    
    async def _generate_heatmap(
        self,
        data: Dict[str, Any],
        title: str,
        labels: Optional[Dict[str, str]],
        filepath: Path
    ) -> None:
        """
        Generate a heatmap.
        
        Args:
            data: Data with 'z' key (2D array) and optional 'x', 'y' keys for labels
            title: Chart title
            labels: Optional axis labels
            filepath: Path to save the chart
        """
        try:
            import plotly.graph_objects as go
        except ImportError:
            raise ImportError("plotly is required for visualization. Install with: pip install plotly kaleido")
        
        # Create figure
        fig = go.Figure(data=[
            go.Heatmap(
                z=data["z"],
                x=data.get("x", None),
                y=data.get("y", None),
                colorscale=data.get("colorscale", "Blues"),
                showscale=True,
                colorbar=dict(title=data.get("colorbar_title", "Value"))
            )
        ])
        
        # Update layout
        fig.update_layout(
            title=dict(
                text=title,
                font=dict(size=18, family="Arial, sans-serif", color="#333")
            ),
            xaxis_title=labels.get("x", "X") if labels else "X",
            yaxis_title=labels.get("y", "Y") if labels else "Y",
            template="plotly_white",
            font=dict(family="Arial, sans-serif", size=12, color="#555"),
            paper_bgcolor="white",
            margin=dict(l=80, r=40, t=80, b=60),
            height=500,
            width=800
        )
        
        # Save as PNG
        await asyncio.to_thread(fig.write_image, str(filepath))
        logger.debug(f"Saved heatmap to {filepath}")
    
    async def _emit_event(
        self,
        event_type: str,
        event_data: Dict[str, Any]
    ) -> None:
        """
        Emit a streaming event if callback is configured.
        
        Args:
            event_type: Type of event
            event_data: Event data payload
        """
        if self.stream_callback:
            try:
                await self.stream_callback({
                    "event_type": event_type,
                    "data": event_data
                })
            except Exception as e:
                logger.error(f"Error emitting event {event_type}: {e}")
