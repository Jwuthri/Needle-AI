"""Visualization tools using Plotly for high-quality charts."""
import asyncio
from datetime import datetime
from pathlib import Path
from langchain_core.tools import tool
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from app.core.llm.lg_workflow.data.manager import DataManager
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Base directory for saving graphs
GRAPHS_BASE_DIR = Path(__file__).parent.parent.parent.parent.parent / "data" / "graphs"
GRAPHS_BASE_DIR.mkdir(parents=True, exist_ok=True)


def _save_chart_png(fig: go.Figure, user_id: str, chart_type: str, title: str) -> str:
    """Save chart as PNG and return absolute file path.
    
    Args:
        fig: Plotly figure
        user_id: User ID
        chart_type: Type of chart (scatter, line, bar, histogram, pie, heatmap)
        title: Chart title
        
    Returns:
        Absolute file path to saved PNG file
    """
    # Create user-specific directory
    user_dir = GRAPHS_BASE_DIR / user_id
    user_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()[:50]
    safe_title = safe_title.replace(' ', '_')
    filename = f"{timestamp}_{chart_type}_{safe_title}.png"
    filepath = user_dir / filename
    
    # Save as high-quality PNG
    fig.write_image(str(filepath), width=1200, height=800, scale=2)
    
    # Return absolute path
    absolute_path = str(filepath.resolve())
    logger.info(f"Saved chart to {absolute_path}")
    
    return absolute_path


@tool
async def generate_plot_tool(
    table_name: str, 
    x_column: str, 
    y_column: str, 
    user_id: str, 
    plot_type: str = "scatter"
) -> str:
    """
    Generate a high-quality interactive plot for a dataset using Plotly.
    
    Saves the plot as a PNG file to the user's graph directory and returns details.
    
    Args:
        table_name: Name of the dataset to plot
        x_column: Column name for x-axis
        y_column: Column name for y-axis (optional for histogram)
        user_id: User ID for dataset access and file organization
        plot_type: Type of plot - Options:
            - 'scatter': Scatter plot (default)
            - 'line': Line chart for trends
            - 'bar': Bar chart for comparisons
            - 'histogram': Distribution histogram (uses only x_column)
            - 'pie': Pie chart (x_column=labels, y_column=values)
            - 'box': Box plot for distribution analysis
        
    Returns:
        Markdown formatted report with chart details and file path
    """
    dm = DataManager.get_instance("default")
    df = await dm.get_dataset(table_name, user_id)
    
    if df is None or df.empty:
        return f"Error: Dataset '{table_name}' not found or empty."
    
    if x_column not in df.columns:
        available_cols = ", ".join(df.columns[:10].tolist())
        return f"Error: Column '{x_column}' not found. Available columns: {available_cols}"
    
    # y_column is optional for some plot types
    if y_column and y_column not in df.columns and plot_type not in ['histogram', 'hist']:
        available_cols = ", ".join(df.columns[:10].tolist())
        return f"Error: Column '{y_column}' not found. Available columns: {available_cols}"

    def _generate_plot():
        try:
            # Prepare clean data
            plot_df = df[[x_column, y_column]].dropna() if y_column and plot_type not in ['histogram', 'hist'] else df[[x_column]].dropna()
            
            if plot_df.empty:
                return None, "Error: No valid data after removing null values."
            
            # Generate title
            if y_column and plot_type not in ['histogram', 'hist']:
                title = f"{plot_type.capitalize()}: {y_column} vs {x_column}"
            else:
                title = f"{plot_type.capitalize()}: {x_column}"
            
            # Create figure based on plot type
            fig = None
            
            if plot_type in ["scatter", "scatterplot"]:
                fig = px.scatter(
                    plot_df, 
                    x=x_column, 
                    y=y_column,
                    title=title,
                    template="plotly_dark",
                    color_discrete_sequence=["#636EFA"]
                )
                fig.update_traces(marker=dict(size=8, opacity=0.7))
                
            elif plot_type in ["line", "lineplot"]:
                fig = px.line(
                    plot_df, 
                    x=x_column, 
                    y=y_column,
                    title=title,
                    template="plotly_dark",
                    color_discrete_sequence=["#636EFA"]
                )
                fig.update_traces(line=dict(width=3))
                
            elif plot_type in ["bar", "barplot"]:
                # Aggregate data if needed
                if pd.api.types.is_numeric_dtype(plot_df[y_column]):
                    agg_df = plot_df.groupby(x_column)[y_column].mean().reset_index()
                else:
                    agg_df = plot_df
                    
                fig = px.bar(
                    agg_df, 
                    x=x_column, 
                    y=y_column,
                    title=title,
                    template="plotly_dark",
                    color_discrete_sequence=["#636EFA"]
                )
                
            elif plot_type in ["histogram", "hist"]:
                fig = px.histogram(
                    plot_df, 
                    x=x_column,
                    title=title,
                    template="plotly_dark",
                    color_discrete_sequence=["#636EFA"]
                )
                fig.update_traces(marker=dict(line=dict(width=1, color='white')))
                
            elif plot_type in ["pie", "piechart"]:
                # For pie charts, handle two cases:
                # 1. Data is already aggregated (has both labels and values)
                # 2. Data needs aggregation (categorical column - count occurrences)
                
                if y_column:
                    # Case 1: Pre-aggregated data with explicit values
                    if y_column in plot_df.columns:
                        fig = go.Figure(
                            data=[go.Pie(
                                labels=plot_df[x_column],
                                values=plot_df[y_column],
                                hole=0.3  # Donut chart
                            )]
                        )
                    else:
                        return None, f"Error: Column '{y_column}' not found for pie chart values."
                else:
                    # Case 2: Categorical data - aggregate by counting occurrences
                    value_counts = plot_df[x_column].value_counts()
                    fig = go.Figure(
                        data=[go.Pie(
                            labels=value_counts.index,
                            values=value_counts.values,
                            hole=0.3  # Donut chart
                        )]
                    )
                    
                fig.update_layout(title=title, template="plotly_dark")
                
            elif plot_type in ["box", "boxplot"]:
                fig = px.box(
                    plot_df,
                    x=x_column,
                    y=y_column if y_column else None,
                    title=title,
                    template="plotly_dark",
                    color_discrete_sequence=["#636EFA"]
                )
                
            else:
                return None, f"Error: Unsupported plot type '{plot_type}'. Supported types: scatter, line, bar, histogram, pie, box."
            
            # Update layout for better appearance
            fig.update_layout(
                font=dict(size=12),
                title_font=dict(size=18, family="Arial"),
                showlegend=True,
                hovermode='closest'
            )
            
            # Save chart
            chart_path = _save_chart_png(fig, user_id, plot_type, title)
            
            # Build report
            report = []
            report.append(f"# Visualization Generated: {plot_type.capitalize()} Chart")
            report.append(f"\n**Chart Title:** {title}")
            report.append(f"**Dataset:** {table_name}")
            report.append(f"**Chart Type:** {plot_type}")
            report.append(f"**X-Axis:** {x_column}")
            if y_column and plot_type not in ['histogram', 'hist']:
                report.append(f"**Y-Axis:** {y_column}")
            report.append(f"**Data Points:** {len(plot_df)}")
            report.append(f"\n**File Location:** `{chart_path}`")
            
            report.append("\n## Chart Details")
            report.append(f"- **Resolution:** 1200x800 pixels (2x scale for high quality)")
            report.append(f"- **Format:** PNG")
            report.append(f"- **Theme:** Dark mode")
            
            # Add data insights
            if plot_type not in ['pie', 'piechart']:
                report.append("\n## Data Summary")
                if pd.api.types.is_numeric_dtype(plot_df[x_column]):
                    report.append(f"- **{x_column} range:** {plot_df[x_column].min():.2f} to {plot_df[x_column].max():.2f}")
                    
                if y_column and pd.api.types.is_numeric_dtype(plot_df[y_column]):
                    report.append(f"- **{y_column} range:** {plot_df[y_column].min():.2f} to {plot_df[y_column].max():.2f}")
                    report.append(f"- **{y_column} mean:** {plot_df[y_column].mean():.2f}")
            
            report.append("\n✅ **Chart generated successfully and saved!**")
            
            return fig, "\n".join(report)
            
        except Exception as e:
            logger.error(f"Error generating plot: {e}", exc_info=True)
            return None, f"Error generating plot: {str(e)}"
    
    loop = asyncio.get_running_loop()
    fig, result = await loop.run_in_executor(None, _generate_plot)
    
    return result
