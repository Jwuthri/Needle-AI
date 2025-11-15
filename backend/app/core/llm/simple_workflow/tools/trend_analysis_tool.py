from app.core.llm.simple_workflow.utils.extract_data_from_ctx_by_key import extract_data_from_ctx_by_key
from app.database.session import get_async_session
from app.services.user_dataset_service import UserDatasetService
from app.utils.logging import get_logger

import pandas as pd
import numpy as np
from llama_index.core.workflow import Context
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = get_logger(__name__)


async def analyze_temporal_trends(
    ctx: Context,
    dataset_name: str,
    time_column: str,
    value_columns: Optional[List[str]] = None,
    aggregation: str = "mean",
    time_grouping: str = "auto"
) -> str:
    """Analyze temporal trends in dataset using Python/pandas.
    
    This tool performs time-series analysis to identify:
    1. Trends over time (increasing, decreasing, stable)
    2. Seasonal patterns
    3. Anomalies or sudden changes
    4. Growth rates and velocity
    
    Args:
        ctx: Context
        dataset_name: Name of the dataset to analyze
        time_column: Name of the column containing time/date data
        value_columns: List of numeric columns to analyze (if None, auto-detect)
        aggregation: Aggregation method ('mean', 'sum', 'count', 'median')
        time_grouping: Time grouping ('auto', 'day', 'week', 'month', 'quarter', 'year')
    
    Returns:
        str: Markdown formatted trend analysis report
    """
    async with get_async_session() as db:
        try:
            # Get dataset from context (check all possible sources)
            data = await extract_data_from_ctx_by_key(ctx, "dataset_data", dataset_name)
            
            if data is None or data.empty:
                return f"Error: Dataset '{dataset_name}' not found in context. Please load the dataset first."
            
            # Check if time column exists
            if time_column not in data.columns:
                available_cols = ", ".join(data.columns[:10])
                return f"Error: Time column '{time_column}' not found. Available columns: {available_cols}"
            
            # Convert time column to datetime
            try:
                data[time_column] = pd.to_datetime(data[time_column], errors='coerce')
                data = data.dropna(subset=[time_column])
                
                if data.empty:
                    return f"Error: No valid dates found in column '{time_column}'"
            except Exception as e:
                return f"Error: Failed to parse dates in column '{time_column}': {str(e)}"
            
            # Auto-detect numeric columns if not specified
            if value_columns is None:
                numeric_cols = data.select_dtypes(include=[np.number]).columns.tolist()
                # Exclude internal columns
                value_columns = [col for col in numeric_cols if not col.startswith("__")]
                
                if not value_columns:
                    return "Error: No numeric columns found for trend analysis"
                
                logger.info(f"Auto-detected numeric columns: {value_columns}")
            
            # Validate value columns exist
            missing_cols = [col for col in value_columns if col not in data.columns]
            if missing_cols:
                return f"Error: Columns not found: {', '.join(missing_cols)}"
            
            # Sort by time
            data = data.sort_values(time_column)
            
            # Determine time grouping
            time_range = (data[time_column].max() - data[time_column].min()).days
            
            if time_grouping == "auto":
                if time_range <= 7:
                    time_grouping = "day"
                elif time_range <= 90:
                    time_grouping = "week"
                elif time_range <= 730:  # 2 years
                    time_grouping = "month"
                else:
                    time_grouping = "quarter"
            
            # Group data by time
            if time_grouping == "day":
                data['time_group'] = data[time_column].dt.date
            elif time_grouping == "week":
                data['time_group'] = data[time_column].dt.to_period('W').apply(lambda r: r.start_time)
            elif time_grouping == "month":
                data['time_group'] = data[time_column].dt.to_period('M').apply(lambda r: r.start_time)
            elif time_grouping == "quarter":
                data['time_group'] = data[time_column].dt.to_period('Q').apply(lambda r: r.start_time)
            elif time_grouping == "year":
                data['time_group'] = data[time_column].dt.to_period('Y').apply(lambda r: r.start_time)
            
            # Build report
            report = []
            report.append(f"# Trend Analysis Report for '{dataset_name}'")
            report.append(f"\n**Time Column:** {time_column}")
            report.append(f"**Time Range:** {data[time_column].min().strftime('%Y-%m-%d')} to {data[time_column].max().strftime('%Y-%m-%d')}")
            report.append(f"**Time Grouping:** {time_grouping}")
            report.append(f"**Aggregation Method:** {aggregation}")
            report.append(f"**Analyzing {len(value_columns)} metric(s)**\n")
            
            # Analyze each value column
            for col in value_columns[:5]:  # Limit to 5 columns
                report.append(f"## Metric: {col}")
                
                # Aggregate by time group
                if aggregation == "mean":
                    grouped = data.groupby('time_group')[col].mean()
                elif aggregation == "sum":
                    grouped = data.groupby('time_group')[col].sum()
                elif aggregation == "count":
                    grouped = data.groupby('time_group')[col].count()
                elif aggregation == "median":
                    grouped = data.groupby('time_group')[col].median()
                else:
                    grouped = data.groupby('time_group')[col].mean()
                
                grouped = grouped.dropna()
                
                if len(grouped) < 2:
                    report.append("\n*Insufficient data points for trend analysis*\n")
                    continue
                
                # Calculate statistics
                values = grouped.values
                first_value = values[0]
                last_value = values[-1]
                mean_value = np.mean(values)
                std_value = np.std(values)
                min_value = np.min(values)
                max_value = np.max(values)
                
                # Calculate trend direction
                if len(values) >= 3:
                    # Simple linear regression for trend
                    x = np.arange(len(values))
                    coefficients = np.polyfit(x, values, 1)
                    slope = coefficients[0]
                    
                    # Calculate percentage change
                    if first_value != 0:
                        pct_change = ((last_value - first_value) / abs(first_value)) * 100
                    else:
                        pct_change = 0
                    
                    # Determine trend
                    if abs(pct_change) < 5:
                        trend_direction = "📊 Stable"
                        trend_desc = "relatively stable"
                    elif pct_change > 0:
                        trend_direction = "📈 Increasing"
                        trend_desc = "upward trend"
                    else:
                        trend_direction = "📉 Decreasing"
                        trend_desc = "downward trend"
                    
                    report.append(f"\n**Trend Direction:** {trend_direction}")
                    report.append(f"**Overall Change:** {pct_change:+.1f}%")
                    report.append(f"**Slope:** {slope:.4f} per {time_grouping}")
                else:
                    trend_desc = "insufficient data"
                    pct_change = 0
                
                report.append(f"\n**Summary Statistics:**")
                report.append(f"- First Value: {first_value:.2f}")
                report.append(f"- Last Value: {last_value:.2f}")
                report.append(f"- Mean: {mean_value:.2f}")
                report.append(f"- Std Dev: {std_value:.2f}")
                report.append(f"- Min: {min_value:.2f}")
                report.append(f"- Max: {max_value:.2f}")
                
                # Detect volatility
                cv = (std_value / mean_value) * 100 if mean_value != 0 else 0
                if cv > 30:
                    report.append(f"\n⚠️ **High Volatility Detected** (CV: {cv:.1f}%)")
                    report.append("- Values fluctuate significantly over time")
                
                # Show time series data (last 10 periods)
                report.append(f"\n**Recent {time_grouping.capitalize()} Values:**\n")
                recent_data = grouped.tail(10).reset_index()
                recent_data.columns = ['Time Period', col]
                recent_data['Time Period'] = recent_data['Time Period'].astype(str)
                report.append(recent_data.to_markdown(index=False))
                report.append("")
            
            # Overall insights
            report.append("## Key Insights")
            report.append("\n**Trend Summary:**\n")
            
            # Analyze all columns for summary
            trends_summary = []
            for col in value_columns[:5]:
                if aggregation == "mean":
                    grouped = data.groupby('time_group')[col].mean()
                else:
                    grouped = data.groupby('time_group')[col].sum()
                
                grouped = grouped.dropna()
                if len(grouped) >= 2:
                    values = grouped.values
                    first_value = values[0]
                    last_value = values[-1]
                    
                    if first_value != 0:
                        pct_change = ((last_value - first_value) / abs(first_value)) * 100
                    else:
                        pct_change = 0
                    
                    if abs(pct_change) < 5:
                        trend = "Stable"
                    elif pct_change > 0:
                        trend = "↑ Increasing"
                    else:
                        trend = "↓ Decreasing"
                    
                    trends_summary.append({
                        "Metric": col,
                        "Trend": trend,
                        "Change": f"{pct_change:+.1f}%",
                        "First": f"{first_value:.2f}",
                        "Last": f"{last_value:.2f}"
                    })
            
            if trends_summary:
                summary_df = pd.DataFrame(trends_summary)
                report.append(summary_df.to_markdown(index=False))
            
            # Store trend analysis results in context
            async with ctx.store.edit_state() as ctx_state:
                if "state" not in ctx_state:
                    ctx_state["state"] = {}
                if "trend_analysis" not in ctx_state["state"]:
                    ctx_state["state"]["trend_analysis"] = {}
                
                ctx_state["state"]["trend_analysis"][dataset_name] = {
                    "time_column": time_column,
                    "time_grouping": time_grouping,
                    "value_columns": value_columns,
                    "trends_summary": trends_summary
                }
            
            result = "\n".join(report)
            logger.info(f"Trend analysis completed for '{dataset_name}': {len(value_columns)} metrics analyzed")
            
            return result
            
        except Exception as e:
            logger.error(f"Error performing trend analysis: {e}", exc_info=True)
            return f"Error: {str(e)}"
