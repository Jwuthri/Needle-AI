"""Data Analyst Agent - performs computations on datasets."""
from typing import Optional
from langchain_core.tools import tool
from app.core.llm.lg_workflow.tools.analytics import clustering_tool, tfidf_tool, describe_tool
from app.core.llm.lg_workflow.tools.ml import sentiment_analysis_tool, embedding_tool, linear_regression_tool, trend_analysis_tool, product_gap_detection_tool, negative_review_gap_detector, semantic_search_tool
from .base import create_agent, llm

def create_analyst_node(user_id: str, dataset_table_name: Optional[str] = None):
    """Create analyst agent with tools bound to user_id and optional focused dataset."""
    
    # Create wrapper tools with user_id bound (and optional default table_name)
    @tool
    async def clustering(table_name: str, target_column: str, n_clusters: int = 3) -> str:
        """
        Performs K-Means clustering on a numeric column of a dataset.
        
        Returns a comprehensive clustering analysis report with:
        - Cluster distribution and sizes
        - Statistical summary for each cluster
        - Sample data from each cluster
        - Insights about cluster characteristics
        
        Updates the dataset with a new 'cluster' column containing cluster IDs (0 to n_clusters-1).
        
        Args:
            table_name: Name of the dataset to cluster
            target_column: Numeric column to cluster on
            n_clusters: Number of clusters to create (default: 3)
        """
        actual_table = dataset_table_name if dataset_table_name else table_name
        return await clustering_tool.coroutine(table_name=actual_table, target_column=target_column, user_id=user_id, n_clusters=n_clusters)
    
    @tool
    async def tfidf_analysis(table_name: str, text_column: str, max_features: int = 10) -> str:
        """
        Computes TF-IDF (Term Frequency-Inverse Document Frequency) analysis for a text column.
        
        Identifies the most important terms/keywords based on their frequency and uniqueness.
        Returns a comprehensive report with top terms, scores, and vocabulary statistics.
        
        Args:
            table_name: Name of the dataset
            text_column: Text column to analyze
            max_features: Number of top terms to return (default: 10)
        """
        actual_table = dataset_table_name if dataset_table_name else table_name
        return await tfidf_tool.coroutine(table_name=actual_table, text_column=text_column, user_id=user_id, max_features=max_features)
    
    @tool
    async def describe_dataset(table_name: str) -> str:
        """
        Returns descriptive statistics and metadata for a dataset.
        
        Includes:
        - Field descriptions and data types
        - Column statistics (min, max, mean, etc.)
        - Sample data (first 5 rows)
        
        Args:
            table_name: Name of the dataset to describe
        """
        actual_table = dataset_table_name if dataset_table_name else table_name
        return await describe_tool.coroutine(table_name=actual_table, user_id=user_id)
    
    @tool
    async def sentiment_analysis(table_name: str, text_column: str) -> str:
        """
        Analyzes the sentiment of a text column in a dataset.
        
        Returns a comprehensive sentiment analysis report with:
        - Overall sentiment distribution (positive/negative/neutral)
        - Statistical summary (mean, std, min, max polarity)
        - Subjectivity analysis
        - Most positive and negative examples
        
        Adds sentiment_polarity, sentiment_subjectivity, and sentiment_label columns to the dataset.
        
        Args:
            table_name: Name of the dataset
            text_column: Text column to analyze (e.g., 'text', 'review', 'comment')
        """
        actual_table = dataset_table_name if dataset_table_name else table_name
        return await sentiment_analysis_tool.coroutine(table_name=actual_table, text_column=text_column, user_id=user_id)
    
    @tool
    async def generate_embeddings(table_name: str, text_column: str) -> str:
        """
        Generates vector embeddings for a text column using OpenAI's embedding model.
        
        Adds a new '__embedding__' column to the dataset.
        WARNING: This can be slow and cost money for large datasets.
        
        Args:
            table_name: Name of the dataset
            text_column: Text column to generate embeddings for
        """
        actual_table = dataset_table_name if dataset_table_name else table_name
        return await embedding_tool.coroutine(table_name=actual_table, text_column=text_column, user_id=user_id)
    
    @tool
    async def linear_regression(table_name: str, target_column: str, feature_columns: list[str]) -> str:
        """
        Performs a simple linear regression to predict a target column based on feature columns.
        
        Returns regression results including R2 score, MSE, and coefficients.
        
        Args:
            table_name: Name of the dataset
            target_column: Column to predict (dependent variable)
            feature_columns: List of columns to use as features (independent variables)
        """
        actual_table = dataset_table_name if dataset_table_name else table_name
        return await linear_regression_tool.coroutine(table_name=actual_table, target_column=target_column, feature_columns=feature_columns, user_id=user_id)
    
    @tool
    async def trend_analysis(table_name: str, date_column: str, value_column: str, period: str = "M") -> str:
        """
        Analyzes trends in a value column over time.
        
        Returns a comprehensive trend analysis report with:
        - Trend direction (increasing/decreasing/stable)
        - Statistical summary (first, last, mean, std, min, max)
        - Percentage change over time
        - Volatility detection
        - Recent time series data
        
        Args:
            table_name: Name of the dataset
            date_column: Column containing datetime values
            value_column: Numeric column to track over time
            period: Aggregation period - 'D' (daily), 'W' (weekly), 'M' (monthly), 'Q' (quarterly), 'Y' (yearly)
        """
        actual_table = dataset_table_name if dataset_table_name else table_name
        return await trend_analysis_tool.coroutine(table_name=actual_table, date_column=date_column, value_column=value_column, user_id=user_id, period=period)
    
    @tool
    async def product_gap_detection(table_name: str, min_cluster_size: int = 5, eps: float = 0.3) -> str:
        """
        Detects gaps in a product catalog by clustering on embeddings.
        
        Uses DBSCAN clustering on the __embedding__ column to identify:
        1. Underrepresented product clusters (gaps)
        2. Outlier products (niche or edge cases)
        3. Missing product themes
        
        Note: Dataset must have '__embedding__' column. Use generate_embeddings first if needed.
        
        Args:
            table_name: Name of the product dataset (must have __embedding__ column)
            min_cluster_size: Minimum cluster size for DBSCAN (default: 5)
            eps: DBSCAN epsilon parameter for clustering (default: 0.3)
        """
        actual_table = dataset_table_name if dataset_table_name else table_name
        return await product_gap_detection_tool.coroutine(table_name=actual_table, user_id=user_id, min_cluster_size=min_cluster_size, eps=eps)
    
    @tool
    async def detect_gaps_from_reviews(
        table_name: str, 
        text_column: str = "text",
        rating_column: str | None = None,
        max_clusters: int = 100,
        min_rating: int = 1,
        max_rating: int = 3
    ) -> str:
        """
        Detects product gaps from reviews using HDBSCAN clustering + LLM.
        
        Process:
        1. If rating_column provided: filters reviews by rating range
        2. Clusters reviews into groups (targets min(n_reviews/2, 100) clusters)
        3. Finds the most representative review per cluster
        4. Sends to LLM to extract actionable product gaps
        
        Note: Dataset must have '__embedding__' column. Use generate_embeddings first if needed.
        
        Args:
            table_name: Name of the reviews dataset
            text_column: Column with review text (default: "text")
            rating_column: Column with ratings (optional - if not provided, analyzes all reviews)
            max_clusters: Maximum clusters to create (default: 100)
            min_rating: Minimum rating when filtering (default: 1)
            max_rating: Maximum rating when filtering (default: 3)
        """
        actual_table = dataset_table_name if dataset_table_name else table_name
        return await negative_review_gap_detector.coroutine(
            table_name=actual_table, 
            user_id=user_id, 
            text_column=text_column,
            rating_column=rating_column,
            max_clusters=max_clusters,
            min_rating=min_rating,
            max_rating=max_rating
        )
    
    @tool
    async def semantic_search(
        table_name: str,
        query: str,
        text_column: str = "text",
        top_k: int = 1000
    ) -> str:
        """
        Performs semantic search to find reviews matching a query.
        
        IMPORTANT: Query is for EMBEDDING SEARCH - keep it SHORT (2-5 words)!
        
        Args:
            table_name: Name of the dataset to search
            query: SHORT phrase only! Examples:
                   ✓ "slow search"
                   ✓ "bad support" 
                   ✓ "expensive pricing"
                   ✗ "reviews about slow search" (TOO LONG)
            text_column: Column containing review text (default: "text")
            top_k: Maximum results to return (default: 1000)
        """
        actual_table = dataset_table_name if dataset_table_name else table_name
        return await semantic_search_tool.coroutine(
            table_name=actual_table,
            user_id=user_id,
            query=query,
            text_column=text_column,
            top_k=top_k
        )
    
    analyst_tools = [
        clustering, tfidf_analysis, describe_dataset, 
        sentiment_analysis, generate_embeddings, linear_regression,
        trend_analysis, detect_gaps_from_reviews, semantic_search
    ]

    # - product_gap_detection - Product gaps (DBSCAN-based)
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
- detect_gaps_from_reviews - Extract product gaps from reviews using HDBSCAN + LLM (optional rating filter)
- semantic_search - Find reviews matching a SHORT query (2-5 words like "slow search", NOT verbose sentences)

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
