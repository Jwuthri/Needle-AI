# Visualization Agent

## Overview

The Visualization Agent is a specialized component of the Product Review Analysis Workflow that generates charts and graphs from analysis results. It uses Plotly to create high-quality visualizations with consistent styling and exports them as PNG files for embedding in responses.

## Purpose

The Visualization Agent:
- Generates charts from structured data
- Supports multiple chart types (bar, line, pie, scatter, heatmap)
- Applies consistent styling and branding
- Saves visualizations as PNG files
- Tracks visualization metadata in Chat Message Steps
- Provides file paths for embedding in markdown responses

## Supported Chart Types

### 1. Bar Chart
Used for comparing categories or showing distributions.

**Required Data:**
```python
{
    "x": ["Category A", "Category B", "Category C"],
    "y": [10, 25, 15],
    "name": "Optional series name",
    "color": "#4A90E2"  # Optional custom color
}
```

**Example Use Cases:**
- Sentiment distribution by aspect
- Topic frequency comparison
- Rating distribution

### 2. Line Chart
Used for showing trends over time or continuous data.

**Required Data:**
```python
{
    "x": ["Jan", "Feb", "Mar", "Apr"],
    "y": [10, 15, 13, 20],
    "name": "Optional series name",
    "color": "#4A90E2"  # Optional custom color
}
```

**Example Use Cases:**
- Sentiment trends over time
- Review volume trends
- Rating changes over time

### 3. Pie Chart
Used for showing proportions and percentages.

**Required Data:**
```python
{
    "labels": ["Positive", "Neutral", "Negative"],
    "values": [60, 25, 15],
    "colors": ["#4ECDC4", "#FFE66D", "#FF6B6B"]  # Optional custom colors
}
```

**Example Use Cases:**
- Sentiment distribution
- Source platform distribution
- Rating distribution

### 4. Scatter Plot
Used for showing correlations and relationships between variables.

**Required Data:**
```python
{
    "x": [1, 2, 3, 4, 5],
    "y": [2, 4, 3, 5, 6],
    "size": 10,  # Optional marker size
    "color": "#4A90E2"  # Optional custom color
}
```

**Example Use Cases:**
- Rating vs sentiment correlation
- Review length vs helpfulness
- Time vs engagement metrics

### 5. Heatmap
Used for showing multi-dimensional data and correlations.

**Required Data:**
```python
{
    "z": [[1, 2, 3], [4, 5, 6], [7, 8, 9]],  # 2D array
    "x": ["A", "B", "C"],  # Optional column labels
    "y": ["Row 1", "Row 2", "Row 3"],  # Optional row labels
    "colorscale": "Blues",  # Optional colorscale
    "colorbar_title": "Value"  # Optional colorbar title
}
```

**Example Use Cases:**
- Feature correlation matrix
- Time-based pattern analysis
- Multi-dimensional sentiment analysis

## Usage

### Basic Usage

```python
from app.core.llm.workflow.agents.visualization import VisualizationAgent

# Initialize agent
viz_agent = VisualizationAgent(
    output_dir="backend/data/graphs",
    stream_callback=None  # Optional streaming callback
)

# Generate a bar chart
data = {
    "x": ["Performance", "Features", "Support"],
    "y": [0.78, 0.45, 0.62]
}

result = await viz_agent.generate_visualization(
    data=data,
    chart_type="bar",
    title="Negative Sentiment by Aspect",
    labels={"x": "Aspect", "y": "Negative Sentiment Score"}
)

print(f"Chart saved to: {result.filepath}")
print(f"Chart type: {result.chart_type}")
print(f"Data points: {result.metadata['data_points']}")
```

### Usage with Execution Context

```python
# Generate visualization with tracking
result = await viz_agent.generate_visualization(
    data=data,
    chart_type="line",
    title="Sentiment Trend Over Time",
    labels={"x": "Date", "y": "Sentiment Score"},
    context=execution_context,  # For user-specific subdirectory
    db=db_session,  # For Chat Message Step tracking
    step_order=5  # Step order in execution
)
```

### Integration with Synthesis Agent

The Visualization Agent is typically called by the Synthesis Agent when embedding visualizations in responses:

```python
# In Synthesis Agent
if insight.visualization_hint and insight.visualization_data:
    viz_result = await self.visualization_agent.generate_visualization(
        data=insight.visualization_data,
        chart_type=insight.visualization_hint,
        title=insight.visualization_data.get("title", "Analysis Chart"),
        labels=insight.visualization_data.get("labels", {})
    )
    
    # Embed in markdown
    markdown += f"![{viz_result.title}]({viz_result.filepath})\n"
```

## File Organization

### Output Directory Structure

```
backend/data/graphs/
├── user_123/
│   ├── abc12345_bar_Sentiment_by_Aspect.png
│   ├── def67890_line_Trend_Over_Time.png
│   └── ...
├── user_456/
│   └── ...
└── ...
```

- Each user gets a dedicated subdirectory
- Filenames include: UUID prefix, chart type, and sanitized title
- PNG format for universal compatibility

### File Path Format

Generated file paths follow this format:
```
/static/visualizations/user_{user_id}/{viz_id}_{chart_type}_{safe_title}.png
```

Example:
```
/static/visualizations/user_123/abc12345_bar_Sentiment_by_Aspect.png
```

## Styling and Branding

All visualizations use consistent styling:

- **Font:** Arial, sans-serif
- **Title Size:** 18px
- **Axis Label Size:** 12px
- **Color Scheme:** Professional blue (#4A90E2) as default
- **Template:** plotly_white (clean, minimal)
- **Grid:** Light gray (#E0E0E0)
- **Dimensions:** 800x500 pixels (standard)
- **Background:** White

### Custom Styling

You can customize colors and styling through the data dictionary:

```python
data = {
    "x": ["A", "B", "C"],
    "y": [10, 20, 15],
    "color": "#FF6B6B",  # Custom color
    "name": "Custom Series"
}
```

## Error Handling

The Visualization Agent validates data and handles errors gracefully:

### Data Validation Errors

```python
# Missing required fields
ValueError: bar chart requires 'x' and 'y' data

# Mismatched lengths
ValueError: bar chart 'x' and 'y' must have same length

# Empty data
ValueError: bar chart requires at least one data point

# Invalid chart type
ValueError: Unsupported chart type: invalid_type
```

### Execution Errors

- Plotly import errors: Raises ImportError with installation instructions
- File write errors: Logged and re-raised
- All errors tracked in Chat Message Steps if context provided

## Metadata Tracking

When executed with a database session and execution context, the agent tracks:

```python
{
    "chart_type": "bar",
    "title": "Sentiment by Aspect",
    "filepath": "/static/visualizations/user_123/abc_bar_Sentiment.png",
    "viz_id": "abc12345",
    "filename": "abc12345_bar_Sentiment_by_Aspect.png",
    "data_points": 3
}
```

This metadata is stored in Chat Message Steps for:
- Execution transparency
- Debugging and troubleshooting
- Performance monitoring
- User feedback analysis

## Streaming Events

The agent emits streaming events for real-time updates:

### agent_step_start
```python
{
    "event_type": "agent_step_start",
    "data": {
        "agent_name": "visualization",
        "action": "generate_visualization",
        "chart_type": "bar",
        "title": "Chart Title"
    }
}
```

### agent_step_complete
```python
{
    "event_type": "agent_step_complete",
    "data": {
        "agent_name": "visualization",
        "action": "generate_visualization",
        "success": True,
        "filepath": "/static/visualizations/...",
        "chart_type": "bar"
    }
}
```

### agent_step_error
```python
{
    "event_type": "agent_step_error",
    "data": {
        "agent_name": "visualization",
        "action": "generate_visualization",
        "error": "Error message",
        "chart_type": "bar"
    }
}
```

## Performance Considerations

### Async Execution

Chart generation uses `asyncio.to_thread` to avoid blocking:

```python
await asyncio.to_thread(fig.write_image, str(filepath))
```

This ensures the event loop remains responsive during PNG export.

### File Size

- PNG files are typically 50-200 KB
- Larger datasets may produce larger files
- Consider data aggregation for very large datasets

### Caching

The agent doesn't implement caching internally. Consider:
- Caching at the Synthesis Agent level
- CDN for serving static visualization files
- Browser caching headers

## Dependencies

Required packages:
```
plotly>=5.0.0
kaleido>=0.2.0  # For PNG export
```

Install with:
```bash
pip install plotly kaleido
```

## Testing

Comprehensive test coverage includes:
- Chart generation for all types
- Data validation
- Error handling
- Metadata tracking
- Streaming events
- File path generation
- Custom styling

Run tests:
```bash
pytest backend/tests/unit/test_visualization_agent.py -v
```

## Future Enhancements

Potential improvements:
1. **Interactive Charts:** Support HTML export for interactive visualizations
2. **More Chart Types:** Add box plots, violin plots, sankey diagrams
3. **Animations:** Support animated charts for time-series data
4. **Themes:** Multiple color themes (dark mode, high contrast)
5. **Annotations:** Support for custom annotations and callouts
6. **Multi-series:** Better support for multiple data series
7. **Export Formats:** Support SVG, PDF export options
8. **Compression:** Optimize PNG file sizes
9. **Watermarking:** Add optional branding/watermarks
10. **Accessibility:** Enhanced alt-text and ARIA labels

## Related Components

- **Synthesis Agent:** Primary consumer of visualizations
- **Analysis Agents:** Generate data for visualizations
- **Chat Message Steps:** Track visualization metadata
- **Execution Context:** Provides user context for file organization
