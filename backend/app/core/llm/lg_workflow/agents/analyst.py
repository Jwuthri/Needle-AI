"""Data Analyst Agent - performs computations on datasets."""
from typing import Optional
from langchain_core.tools import tool
from app.core.llm.lg_workflow.tools.analytics import clustering_tool, tfidf_tool, describe_tool
from app.core.llm.lg_workflow.tools.ml import sentiment_analysis_tool, embedding_tool, linear_regression_tool, trend_analysis_tool, product_gap_detection_tool
from .base import create_agent, llm

def create_analyst_node(user_id: str, dataset_table_name: Optional[str] = None):
    """Create analyst agent with tools bound to user_id and optional focused dataset."""
    
    # Create wrapper tools with user_id bound (and optional default table_name)
    @tool
    async def clustering(table_name: str, target_column: str, n_clusters: int = 3) -> str:
        """Perform K-means clustering on a dataset."""
        actual_table = dataset_table_name if dataset_table_name else table_name
        return await clustering_tool.coroutine(table_name=actual_table, target_column=target_column, user_id=user_id, n_clusters=n_clusters)
    
    @tool
    async def tfidf_analysis(table_name: str, text_column: str, max_features: int = 10) -> str:
        """Perform TF-IDF analysis on a text column."""
        actual_table = dataset_table_name if dataset_table_name else table_name
        return await tfidf_tool.coroutine(table_name=actual_table, text_column=text_column, user_id=user_id, max_features=max_features)
    
    @tool
    async def describe_dataset(table_name: str) -> str:
        """Get descriptive statistics and metadata for a dataset."""
        actual_table = dataset_table_name if dataset_table_name else table_name
        return await describe_tool.coroutine(table_name=actual_table, user_id=user_id)
    
    @tool
    async def sentiment_analysis(table_name: str, text_column: str) -> str:
        """Perform sentiment analysis on a text column."""
        actual_table = dataset_table_name if dataset_table_name else table_name
        return await sentiment_analysis_tool.coroutine(table_name=actual_table, text_column=text_column, user_id=user_id)
    
    @tool
    async def generate_embeddings(table_name: str, text_column: str) -> str:
        """Generate embeddings for a text column."""
        actual_table = dataset_table_name if dataset_table_name else table_name
        return await embedding_tool.coroutine(table_name=actual_table, text_column=text_column, user_id=user_id)
    
    @tool
    async def linear_regression(table_name: str, target_column: str, feature_columns: list[str]) -> str:
        """Perform linear regression analysis."""
        actual_table = dataset_table_name if dataset_table_name else table_name
        return await linear_regression_tool.coroutine(table_name=actual_table, target_column=target_column, feature_columns=feature_columns, user_id=user_id)
    
    @tool
    async def trend_analysis(table_name: str, date_column: str, value_column: str, period: str = "M") -> str:
        """Analyze trends in time series data."""
        actual_table = dataset_table_name if dataset_table_name else table_name
        return await trend_analysis_tool.coroutine(table_name=actual_table, date_column=date_column, value_column=value_column, user_id=user_id, period=period)
    
    @tool
    async def product_gap_detection(table_name: str, min_cluster_size: int = 5, eps: float = 0.3) -> str:
        """Detect gaps in product catalog using clustering on embeddings."""
        actual_table = dataset_table_name if dataset_table_name else table_name
        return await product_gap_detection_tool.coroutine(table_name=actual_table, user_id=user_id, min_cluster_size=min_cluster_size, eps=eps)
    
    analyst_tools = [
        clustering, tfidf_analysis, describe_dataset, 
        sentiment_analysis, generate_embeddings, linear_regression,
        trend_analysis, product_gap_detection
    ]
    
    # Build prompt with optional focused mode notice
    base_prompt = """You are a Data Analyst - perform analysis on datasets.

AVAILABLE TOOLS:
- sentiment_analysis - Analyze sentiment (adds sentiment_polarity, sentiment_subjectivity, sentiment_label)
- clustering - K-means clustering (adds cluster column)
- tfidf_analysis - Extract top keywords
- trend_analysis - Time series analysis
- describe_dataset - Statistical summary
- linear_regression - Predictions
- generate_embeddings - Vector embeddings
- product_gap_detection - Product gaps

WORKFLOW:
1. Get table_name from conversation
2. Call appropriate tool with correct parameters
3. Tool returns comprehensive markdown report
4. Say: "Analysis done, see previous message."

COLUMN HINTS:
- Text: text, review, comment, content, description
- Date: date, created_at, timestamp, time
- Numeric: rating, score, price, amount, value

CRITICAL RULES:
- Tools return complete markdown reports with stats, insights, recommendations
- DO NOT summarize or explain the tool output
- After tool execution, ONLY say: "Analysis done, see previous message."
- Nothing more

Example:
User: "What's the sentiment?"
You: [Call sentiment_analysis(table_name="reviews", text_column="text")]
[Tool returns full sentiment report with stats and insights]
You: "Analysis done, see previous message."

Remember: Tools do all the work. You just call them and say "Analysis done, see previous message." That's it."""

    if dataset_table_name:
        focused_notice = f"""

⚠️ FOCUSED MODE ACTIVE ⚠️
You are working exclusively with dataset: '{dataset_table_name}'
- ALWAYS use table_name='{dataset_table_name}' for all tool calls
- Do NOT reference or analyze other datasets
- The table_name parameter will auto-redirect to this dataset"""
        base_prompt += focused_notice
    
    return create_agent(llm, analyst_tools, base_prompt)
