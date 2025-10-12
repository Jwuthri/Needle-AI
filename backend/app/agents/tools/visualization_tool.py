"""
Visualization Tool - Generates chart and table configurations.
"""

from typing import Any, Dict, List, Optional

from app.agents.tools.base_tool import BaseTool, ToolResult
from app.utils.logging import get_logger

logger = get_logger("visualization_tool")


class VisualizationTool(BaseTool):
    """
    Generates visualization configurations for charts and tables.
    
    Does not render actual visualizations - generates JSON configs
    that the frontend can use with Chart.js or similar libraries.
    """
    
    @property
    def name(self) -> str:
        return "visualization"
    
    @property
    def description(self) -> str:
        return """Generate visualization configurations for data.

Use this tool when you need to create charts or tables to display data visually.

Supported chart types:
- bar: Bar chart for categorical comparisons
- line: Line chart for trends over time
- pie: Pie chart for proportions
- table: Data table for detailed view

Parameters:
- data: List of data points (dictionaries)
- chart_type: Type of visualization (bar, line, pie, table)
- x_axis: Column name for X axis (for bar/line charts)
- y_axis: Column name for Y axis (for bar/line charts)
- title: Chart title
- labels: Optional custom labels

Returns a chart configuration JSON that frontend can render.
"""
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "data": {
                    "type": "array",
                    "description": "List of data points to visualize"
                },
                "chart_type": {
                    "type": "string",
                    "enum": ["bar", "line", "pie", "table"],
                    "description": "Type of visualization"
                },
                "x_axis": {
                    "type": "string",
                    "description": "Column for X axis (bar/line charts)"
                },
                "y_axis": {
                    "type": "string",
                    "description": "Column for Y axis (bar/line charts)"
                },
                "title": {
                    "type": "string",
                    "description": "Chart title"
                },
                "labels": {
                    "type": "object",
                    "description": "Custom axis labels"
                }
            },
            "required": ["data", "chart_type"]
        }
    
    async def execute(
        self,
        data: List[Dict[str, Any]],
        chart_type: str,
        x_axis: Optional[str] = None,
        y_axis: Optional[str] = None,
        title: Optional[str] = None,
        labels: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> ToolResult:
        """
        Generate visualization configuration.
        
        Args:
            data: Data to visualize
            chart_type: Type of chart
            x_axis: X axis column
            y_axis: Y axis column
            title: Chart title
            labels: Custom labels
            
        Returns:
            ToolResult with chart configuration
        """
        try:
            if not data:
                return ToolResult(
                    success=False,
                    summary="No data provided for visualization",
                    error="Data array is empty"
                )
            
            if chart_type == "table":
                config = self._generate_table_config(data, title)
            elif chart_type == "bar":
                config = self._generate_bar_chart(data, x_axis, y_axis, title, labels)
            elif chart_type == "line":
                config = self._generate_line_chart(data, x_axis, y_axis, title, labels)
            elif chart_type == "pie":
                config = self._generate_pie_chart(data, x_axis, y_axis, title)
            else:
                return ToolResult(
                    success=False,
                    summary=f"Unsupported chart type: {chart_type}",
                    error=f"Chart type '{chart_type}' not recognized"
                )
            
            return ToolResult(
                success=True,
                data={"config": config, "chart_type": chart_type},
                summary=f"Generated {chart_type} visualization with {len(data)} data points",
                metadata={
                    "chart_type": chart_type,
                    "data_points": len(data)
                }
            )
            
        except Exception as e:
            logger.error(f"Visualization generation failed: {e}", exc_info=True)
            return ToolResult(
                success=False,
                summary=f"Failed to generate visualization: {str(e)}",
                error=str(e)
            )
    
    def _generate_table_config(
        self,
        data: List[Dict[str, Any]],
        title: Optional[str]
    ) -> Dict[str, Any]:
        """Generate table configuration."""
        # Extract columns from first row
        columns = list(data[0].keys()) if data else []
        
        return {
            "type": "table",
            "title": title or "Data Table",
            "columns": columns,
            "rows": data,
            "totalRows": len(data)
        }
    
    def _generate_bar_chart(
        self,
        data: List[Dict[str, Any]],
        x_axis: Optional[str],
        y_axis: Optional[str],
        title: Optional[str],
        labels: Optional[Dict[str, str]]
    ) -> Dict[str, Any]:
        """Generate bar chart configuration."""
        if not x_axis or not y_axis:
            # Auto-detect axes
            first_row = data[0]
            x_axis = x_axis or list(first_row.keys())[0]
            y_axis = y_axis or list(first_row.keys())[1] if len(first_row) > 1 else x_axis
        
        chart_labels = [str(row.get(x_axis, "")) for row in data]
        chart_values = [row.get(y_axis, 0) for row in data]
        
        return {
            "type": "bar",
            "title": title or f"{y_axis} by {x_axis}",
            "data": {
                "labels": chart_labels,
                "datasets": [{
                    "label": labels.get(y_axis, y_axis) if labels else y_axis,
                    "data": chart_values,
                    "backgroundColor": "rgba(54, 162, 235, 0.5)",
                    "borderColor": "rgba(54, 162, 235, 1)",
                    "borderWidth": 1
                }]
            },
            "options": {
                "scales": {
                    "y": {
                        "beginAtZero": True,
                        "title": {
                            "display": True,
                            "text": labels.get(y_axis, y_axis) if labels else y_axis
                        }
                    },
                    "x": {
                        "title": {
                            "display": True,
                            "text": labels.get(x_axis, x_axis) if labels else x_axis
                        }
                    }
                }
            }
        }
    
    def _generate_line_chart(
        self,
        data: List[Dict[str, Any]],
        x_axis: Optional[str],
        y_axis: Optional[str],
        title: Optional[str],
        labels: Optional[Dict[str, str]]
    ) -> Dict[str, Any]:
        """Generate line chart configuration."""
        if not x_axis or not y_axis:
            first_row = data[0]
            x_axis = x_axis or list(first_row.keys())[0]
            y_axis = y_axis or list(first_row.keys())[1] if len(first_row) > 1 else x_axis
        
        chart_labels = [str(row.get(x_axis, "")) for row in data]
        chart_values = [row.get(y_axis, 0) for row in data]
        
        return {
            "type": "line",
            "title": title or f"{y_axis} over {x_axis}",
            "data": {
                "labels": chart_labels,
                "datasets": [{
                    "label": labels.get(y_axis, y_axis) if labels else y_axis,
                    "data": chart_values,
                    "fill": False,
                    "borderColor": "rgb(75, 192, 192)",
                    "tension": 0.1
                }]
            },
            "options": {
                "scales": {
                    "y": {
                        "beginAtZero": True,
                        "title": {
                            "display": True,
                            "text": labels.get(y_axis, y_axis) if labels else y_axis
                        }
                    },
                    "x": {
                        "title": {
                            "display": True,
                            "text": labels.get(x_axis, x_axis) if labels else x_axis
                        }
                    }
                }
            }
        }
    
    def _generate_pie_chart(
        self,
        data: List[Dict[str, Any]],
        x_axis: Optional[str],
        y_axis: Optional[str],
        title: Optional[str]
    ) -> Dict[str, Any]:
        """Generate pie chart configuration."""
        if not x_axis or not y_axis:
            first_row = data[0]
            x_axis = x_axis or list(first_row.keys())[0]
            y_axis = y_axis or list(first_row.keys())[1] if len(first_row) > 1 else x_axis
        
        chart_labels = [str(row.get(x_axis, "")) for row in data]
        chart_values = [row.get(y_axis, 0) for row in data]
        
        # Generate colors
        colors = self._generate_colors(len(data))
        
        return {
            "type": "pie",
            "title": title or f"Distribution of {y_axis}",
            "data": {
                "labels": chart_labels,
                "datasets": [{
                    "data": chart_values,
                    "backgroundColor": colors,
                    "borderWidth": 1
                }]
            },
            "options": {
                "plugins": {
                    "legend": {
                        "display": True,
                        "position": "right"
                    }
                }
            }
        }
    
    def _generate_colors(self, count: int) -> List[str]:
        """Generate a list of colors for charts."""
        base_colors = [
            "rgba(255, 99, 132, 0.7)",
            "rgba(54, 162, 235, 0.7)",
            "rgba(255, 206, 86, 0.7)",
            "rgba(75, 192, 192, 0.7)",
            "rgba(153, 102, 255, 0.7)",
            "rgba(255, 159, 64, 0.7)",
            "rgba(199, 199, 199, 0.7)",
            "rgba(83, 102, 255, 0.7)",
            "rgba(255, 99, 255, 0.7)",
            "rgba(99, 255, 132, 0.7)"
        ]
        
        # Repeat colors if needed
        colors = []
        for i in range(count):
            colors.append(base_colors[i % len(base_colors)])
        
        return colors

