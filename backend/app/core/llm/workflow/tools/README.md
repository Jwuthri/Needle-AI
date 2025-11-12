# Workflow Tools Implementation

This directory contains the tool functions for the Product Review Analysis Workflow, as specified in the design document at `.kiro/specs/product-review-analysis-workflow/design.md`.

## Implemented Tools

All tools are implemented in `workflow_tools.py` and return mock data for testing the workflow implementation.

### 1. get_user_datasets_with_eda

**Purpose**: Retrieve all datasets for a user along with EDA metadata.

**Signature**:
```python
def get_user_datasets_with_eda(user_id: str) -> List[Dict[str, Any]]
```

**Returns**: List of datasets with comprehensive EDA metadata including:
- Dataset identification and table names
- Row counts and date ranges
- Column statistics (min, max, mean, distinct counts, top values)
- Data quality insights
- Summary descriptions

**Mock Data**: Returns Netflix review dataset with 45 reviews from App Store, Reddit, and Trustpilot.

### 2. query_reviews

**Purpose**: Query reviews with filters.

**Signature**:
```python
def query_reviews(
    user_id: str,
    table_name: Optional[str] = None,
    rating_filter: Optional[str] = None,
    date_range: Optional[Tuple[str, str]] = None,
    source_filter: Optional[List[str]] = None,
    text_contains: Optional[str] = None,
    limit: int = 1000
) -> Dict[str, Any]
```

**Filters Supported**:
- `rating_filter`: Rating expressions like ">=4", "<=2", "==3"
- `date_range`: Tuple of (start_date, end_date) in YYYY-MM-DD format
- `source_filter`: List of sources (e.g., ["app_store", "reddit"])
- `text_contains`: Text substring search
- `limit`: Maximum results to return

**Returns**: Dict with reviews, counts, and query metadata.

**Mock Data**: Returns 12 sample Netflix reviews with various ratings and sources.

### 3. semantic_search_reviews

**Purpose**: Semantic search using vector embeddings.

**Signature**:
```python
def semantic_search_reviews(
    user_id: str,
    query_text: str,
    top_k: int = 50,
    rating_filter: Optional[str] = None
) -> List[Dict[str, Any]]
```

**Returns**: List of reviews with similarity scores (0.0 to 1.0).

**Mock Data**: Simulates vector similarity by matching keywords in the query text. Returns reviews sorted by relevance with realistic similarity scores.

### 4. get_time

**Purpose**: Get current time and date.

**Signature**:
```python
def get_time() -> Dict[str, Any]
```

**Returns**: Dict with current time, date, datetime, day of week, and timezone.

**Use Case**: Handles simple informational queries like "What time is it?"

### 5. generate_visualization

**Purpose**: Generate visualization as PNG chart.

**Signature**:
```python
def generate_visualization(
    data: List[Dict[str, Any]],
    chart_type: str,
    title: str,
    labels: Optional[Dict[str, str]] = None,
    user_id: str = "default"
) -> Dict[str, Any]
```

**Supported Chart Types**:
- `bar`: Bar charts for comparisons and distributions
- `line`: Line charts for trends over time
- `pie`: Pie/donut charts for proportions
- `scatter`: Scatter plots for correlations

**Data Format**:
- Bar/Line charts: `[{"x": value, "y": value}, ...]`
- Pie charts: `[{"label": str, "value": number}, ...]`

**Returns**: Dict with chart type, title, filepath (absolute path to PNG), and metadata.

**Output**: Saves PNG files to `backend/app/data/graphs/{user_id}/` directory.

## Testing

Run the test script to verify all tools work correctly:

```bash
cd backend
python test_workflow_tools.py
```

The test script verifies:
- ✓ Dataset retrieval with EDA metadata
- ✓ Query filtering (rating, source, text search)
- ✓ Semantic search with similarity scoring
- ✓ Time utility function
- ✓ Visualization generation (bar, line, pie charts)

## Requirements Mapping

These tools satisfy the following requirements from the spec:

- **Requirement 1.4**: User dataset access with EDA metadata
- **Requirement 5.1**: Dataset retrieval tool
- **Requirement 5.2, 5.3, 5.5**: Query reviews with filters
- **Requirement 5.4**: Semantic search with vector embeddings
- **Requirement 1.3**: Vector embedding search
- **Requirement 2.2**: Simple informational queries
- **Requirement 6.2, 6.3, 6.4**: Visualization generation
- **Requirement 8.1, 8.2, 8.3**: Chart creation and storage
- **Requirement 9.1-9.5**: Tool function implementation

## Dependencies

- `plotly`: For chart generation
- `kaleido==0.2.1`: For PNG export (version pinned for compatibility with plotly 5.18.0)

## Next Steps

These tools will be integrated with:
1. Data Retrieval Agent (Task 6)
2. Visualization Agent (Task 12)
3. Planner Agent for tool selection (Task 5)
4. Workflow orchestration (Task 14)

The mock data will be replaced with real database queries in future tasks.
