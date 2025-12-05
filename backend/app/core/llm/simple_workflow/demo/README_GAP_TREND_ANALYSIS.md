# Gap Analysis & Trend Analysis Tools

## Overview

This document describes the implementation of two powerful analysis tools for the simple_workflow system:

1. **Gap Analysis Tool** - Identifies underrepresented clusters, outliers, and market gaps
2. **Trend Analysis Tool** - Detects temporal patterns and trends using Python/pandas

## Architecture

### Workflow Pattern

The simple_workflow follows a clear architecture:

```
Tools (tools/) → Agents (agents/) → Workflow (workflow.py)
                    ↓
              Context (shared state)
```

**Key Components:**
- **Tools**: Async functions that perform data operations
- **Agents**: LLM-powered agents that use tools
- **Context**: Shared state using `ctx.store` for data persistence
- **Workflow**: Orchestrates agents and manages execution flow

### Data Flow

```
1. Load Dataset → ctx.state.dataset_data[dataset_name]
2. Clustering → ctx.state.dataset_data.clustering[dataset_name]
3. Gap Analysis → ctx.state.gap_analysis[dataset_name]
4. Trend Analysis → ctx.state.trend_analysis[dataset_name]
```

## Gap Analysis Tool

### Location
`backend/app/core/llm/simple_workflow/tools/gap_analysis_tool.py`

### Function
```python
async def detect_gaps_from_clusters(
    ctx: Context,
    dataset_name: str,
    min_cluster_size: int = 5
) -> str
```

### What It Does

The gap analysis tool identifies opportunities and gaps by analyzing clustered data:

1. **Automatic Clustering**: If clustering hasn't been performed, it automatically triggers it
2. **Underrepresented Clusters**: Finds clusters smaller than 50% of average size
3. **Outlier Analysis**: Analyzes noise points (unclustered data) for edge cases
4. **Distribution Analysis**: Shows cluster size distribution and concentration
5. **Actionable Recommendations**: Provides insights on gaps and opportunities

### Output Format

Returns a markdown-formatted report with:
- Total data points and cluster statistics
- Underrepresented clusters with sample data
- Outlier analysis with high outlier rate warnings
- Cluster distribution table
- Key insights and recommendations

### Example Usage

```python
from app.core.llm.simple_workflow.tools.gap_analysis_tool import detect_gaps_from_clusters

# In a workflow step
gap_report = await detect_gaps_from_clusters(
    ctx,
    dataset_name="customer_reviews",
    min_cluster_size=5
)
```

### Key Insights Provided

- **Concentration Issues**: Identifies if too much data is in few clusters
- **Underserved Segments**: Highlights small clusters that may represent unmet needs
- **Outlier Patterns**: High outlier rates suggest diverse, unmet needs
- **Market Opportunities**: Small clusters and outliers indicate innovation opportunities

## Trend Analysis Tool

### Location
`backend/app/core/llm/simple_workflow/tools/trend_analysis_tool.py`

### Function
```python
async def analyze_temporal_trends(
    ctx: Context,
    dataset_name: str,
    time_column: str,
    value_columns: Optional[List[str]] = None,
    aggregation: str = "mean",
    time_grouping: str = "auto"
) -> str
```

### What It Does

The trend analysis tool performs time-series analysis using Python/pandas:

1. **Auto-Detection**: Automatically detects numeric columns if not specified
2. **Smart Grouping**: Auto-selects time grouping (day/week/month/quarter) based on data range
3. **Trend Direction**: Calculates slope and percentage change
4. **Statistical Analysis**: Provides mean, std dev, min, max, and volatility metrics
5. **Pattern Detection**: Identifies increasing, decreasing, or stable trends

### Parameters

- **time_column**: Name of the date/time column (required)
- **value_columns**: List of numeric columns to analyze (auto-detects if None)
- **aggregation**: `mean`, `sum`, `count`, or `median`
- **time_grouping**: `auto`, `day`, `week`, `month`, `quarter`, or `year`

### Output Format

Returns a markdown-formatted report with:
- Time range and grouping information
- Per-metric analysis with trend direction (📈/📉/📊)
- Summary statistics (first, last, mean, std dev, min, max)
- Volatility warnings for high coefficient of variation
- Recent time period values table
- Overall trend summary table

### Example Usage

```python
from app.core.llm.simple_workflow.tools.trend_analysis_tool import analyze_temporal_trends

# In a workflow step
trend_report = await analyze_temporal_trends(
    ctx,
    dataset_name="sales_data",
    time_column="order_date",
    value_columns=["revenue", "units_sold"],  # or None for auto-detect
    aggregation="sum",
    time_grouping="month"
)
```

### Key Insights Provided

- **Trend Direction**: Increasing (📈), Decreasing (📉), or Stable (📊)
- **Growth Rate**: Percentage change and slope per time period
- **Volatility**: Coefficient of variation to detect fluctuations
- **Recent Patterns**: Last 10 time periods for quick insights

## Agent Integration

### Gap Analysis Agent

**Location**: `backend/app/core/llm/simple_workflow/agents/gap_analysis_agent.py`

**Capabilities**:
- Identifies product gaps and unmet needs
- Analyzes underrepresented customer segments
- Detects outlier patterns and edge cases
- Provides market opportunity insights

**System Prompt Highlights**:
- Analyzes clustered data for gaps
- Auto-triggers clustering if needed
- Focuses on underserved segments
- Provides evidence-based recommendations

### Trend Analysis Agent

**Location**: `backend/app/core/llm/simple_workflow/agents/trend_analysis_agent.py`

**Capabilities**:
- Detects temporal trends and patterns
- Analyzes growth rates and velocity
- Identifies seasonal variations
- Detects anomalies and volatility

**System Prompt Highlights**:
- Uses Python/pandas for statistical analysis
- Auto-detects time and numeric columns
- Provides actionable business insights
- Recommends visualization approaches

## Demo Script

### Location
`backend/app/core/llm/simple_workflow/demo_gap_trend_analysis.py`

### Running the Demo

```bash
cd backend
python -m app.core.llm.simple_workflow.demo_gap_trend_analysis
```

### What the Demo Does

1. Initializes workflow context
2. Fetches available datasets
3. Loads a sample dataset
4. Runs gap analysis (auto-triggers clustering)
5. Runs trend analysis (if time columns exist)
6. Displays comprehensive results

## Context State Structure

```python
ctx.state = {
    "user_id": str,
    "dataset_data": {
        "dataset_name": pd.DataFrame,  # Raw data
        "sql_search": {...},
        "semantic_search": {...},
        "clustering": {
            "dataset_name": pd.DataFrame  # With __cluster_id__ column
        }
    },
    "list_of_user_datasets": {
        "dataset_name": {
            "table_name": str,
            "field_metadata": {...},
            "vector_store_columns": {...},
            ...
        }
    },
    "gap_analysis": {
        "dataset_name": {
            "total_clusters": int,
            "underrepresented_clusters": int,
            "outlier_count": int,
            "outlier_percentage": float,
            "top3_concentration": float,
            "cluster_stats": [...]
        }
    },
    "trend_analysis": {
        "dataset_name": {
            "time_column": str,
            "time_grouping": str,
            "value_columns": List[str],
            "trends_summary": [...]
        }
    }
}
```

## Implementation Details

### Gap Analysis Algorithm

1. **Check for Clustering**: Looks in `ctx.state.dataset_data.clustering[dataset_name]`
2. **Auto-Cluster**: If not found, calls `cuterize_dataset()` first
3. **Calculate Statistics**: Cluster sizes, percentages, average size
4. **Identify Gaps**:
   - Underrepresented: Clusters < 50% of average size
   - Outliers: Points with cluster_id == -1
   - Concentration: Top 3 clusters percentage
5. **Generate Report**: Markdown with tables, samples, and recommendations

### Trend Analysis Algorithm

1. **Load Data**: Gets dataset from context
2. **Validate Time Column**: Converts to datetime, handles errors
3. **Auto-Detect Columns**: Finds numeric columns if not specified
4. **Smart Grouping**: Chooses time grouping based on data range
5. **Aggregate Data**: Groups by time period with specified aggregation
6. **Calculate Trends**:
   - Linear regression for slope
   - Percentage change
   - Statistical measures (mean, std, min, max)
   - Coefficient of variation for volatility
7. **Generate Report**: Markdown with trend indicators and tables

## Best Practices

### When to Use Gap Analysis

- After clustering to identify market opportunities
- To find underserved customer segments
- To detect edge cases and niche needs
- To validate product-market fit

### When to Use Trend Analysis

- For time-series data with date columns
- To track KPIs over time
- To detect seasonal patterns
- To identify growth or decline trends

### Combining Both Tools

```python
# 1. Load dataset
await get_dataset_data_from_sql(ctx, sql_query, dataset_name)

# 2. Gap analysis (includes clustering)
gap_report = await detect_gaps_from_clusters(ctx, dataset_name)

# 3. Trend analysis
trend_report = await analyze_temporal_trends(
    ctx, dataset_name, "created_at"
)

# 4. Use insights for decision-making
```

## Error Handling

Both tools include comprehensive error handling:

- **Missing Data**: Clear error messages if dataset not found
- **Invalid Columns**: Helpful messages with available column names
- **Clustering Failures**: Graceful degradation with error details
- **Time Parsing**: Multiple encoding attempts and clear error messages
- **Edge Cases**: Handles empty datasets, insufficient data points, etc.

## Performance Considerations

### Gap Analysis
- **Clustering**: Can be expensive for large datasets (>10k rows)
- **Optimization**: Uses UMAP + HDBSCAN for efficient clustering
- **Caching**: Stores clustered data in context to avoid re-clustering

### Trend Analysis
- **Pandas Operations**: Efficient for datasets up to 100k rows
- **Auto-Detection**: Limits to first 5 numeric columns to avoid overhead
- **Grouping**: Smart time grouping reduces computation

## Future Enhancements

### Gap Analysis
- [ ] Advanced gap scoring algorithm
- [ ] Competitive gap analysis (compare with benchmarks)
- [ ] Automated gap prioritization
- [ ] Integration with recommendation systems

### Trend Analysis
- [ ] Forecasting capabilities (ARIMA, Prophet)
- [ ] Anomaly detection with statistical tests
- [ ] Seasonality decomposition
- [ ] Correlation analysis between metrics
- [ ] Change point detection

## Testing

Run tests with:
```bash
cd backend
pytest tests/unit/test_gap_analysis_tool.py
pytest tests/unit/test_trend_analysis_tool.py
```

## Contributing

When adding new analysis tools:

1. Create tool function in `tools/` directory
2. Create agent in `agents/` directory
3. Update workflow in `workflow.py`
4. Add to `agents/__init__.py`
5. Create demo script
6. Update this README

## Related Documentation

- [CQRS Guide](../../../guides/CQRS_GUIDE.md)
- [Testing Guide](../../../guides/TESTING_GUIDE.md)
- [LLM Integration](../../../../../.cursor/rules/llm-integration.mdc)
- [Clustering Tool](tools/clustering_analysis_tool.py)
- [User Dataset Service](../../../services/user_dataset_service.py)

