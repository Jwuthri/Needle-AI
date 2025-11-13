"""
Analysis tools for dataset analysis workflow.

These tools perform ML-based analysis on any dataset.
- For review tables: Uses ReviewAnalysisService with pre-written queries
- For user datasets: Uses DatasetAnalysisService with LLM-provided SQL queries
"""

from typing import Any, Dict, Optional

from llama_index.core.workflow import Context

from app.core.llm.simple_workflow.services.dataset_analysis_service import DatasetAnalysisService
from app.core.llm.simple_workflow.services.review_analysis_service import ReviewAnalysisService
from app.services.user_reviews_service import UserReviewsService
from app.utils.logging import get_logger

logger = get_logger(__name__)

from .data_access_tools import _ensure_db_session


def _is_review_table(table_name: str) -> bool:
    """Check if table is a review table."""
    return table_name.endswith("_reviews") or table_name.startswith("__user_") and "_reviews" in table_name


async def detect_product_gaps(
    user_id: str,
    ctx: Optional[Context] = None,
    analysis_params: Optional[Dict[str, Any]] = None,
    table_name: Optional[str] = None,
    sql_query: Optional[str] = None,
    text_column: Optional[str] = None
) -> Dict[str, Any]:
    """Identify gaps, unmet needs, and frequently mentioned issues.
    
    Args:
        user_id: User ID
        ctx: LlamaIndex Context object
        analysis_params: Optional analysis parameters (min_frequency, top_n)
        table_name: Optional table name (for review tables)
        sql_query: SQL query (for user datasets - provided by LLM)
        text_column: Column name containing text content (required if sql_query provided)
        
    Returns:
        Dict with detected gaps
    """
    try:
        db = await _ensure_db_session(ctx)
        analysis_params = analysis_params or {}
        
        # If SQL query provided, use DatasetAnalysisService
        if sql_query:
            if not text_column:
                raise ValueError("text_column is required when sql_query is provided")
            
            service = DatasetAnalysisService(db)
            result = await service.detect_product_gaps(
                user_id=user_id,
                sql_query=sql_query,
                text_column=text_column,
                min_frequency=analysis_params.get("min_frequency", 3),
                top_n=analysis_params.get("top_n", 10)
            )
        else:
            # Use ReviewAnalysisService for review tables
            if not table_name:
                user_reviews_service = UserReviewsService(db)
                table_name = user_reviews_service.get_user_reviews_table_name(user_id)
            
            service = ReviewAnalysisService(db)
            result = await service.detect_product_gaps(
                user_id=user_id,
                table_name=table_name,
                min_frequency=analysis_params.get("min_frequency", 3),
                top_n=analysis_params.get("top_n", 10)
            )
        
        # Store results in context for visualization
        if ctx:
            gap_data = [
                {"x": gap["title"], "y": gap["frequency"]}
                for gap in result.get("gaps_detected", [])
            ]
            await ctx.set("gap_analysis_results", result)
            await ctx.set("gap_analysis_data", gap_data)
            logger.info(f"Stored gap analysis data in context with {len(gap_data)} gaps")
        
        return result
        
    except Exception as e:
        logger.error(f"Error detecting product gaps: {e}")
        raise


async def analyze_sentiment_patterns(
    user_id: str,
    ctx: Optional[Context] = None,
    filters: Optional[Dict[str, Any]] = None,
    table_name: Optional[str] = None,
    sql_query: Optional[str] = None,
    rating_column: Optional[str] = None
) -> Dict[str, Any]:
    """Analyze sentiment patterns and trends.
    
    Args:
        user_id: User ID
        ctx: LlamaIndex Context object
        filters: Optional filters (for review tables)
        table_name: Optional table name (for review tables)
        sql_query: SQL query (for user datasets - provided by LLM)
        rating_column: Column name containing ratings/scores (required if sql_query provided)
        
    Returns:
        Dict with sentiment analysis results
    """
    try:
        db = await _ensure_db_session(ctx)
        
        # If SQL query provided, use DatasetAnalysisService
        if sql_query:
            if not rating_column:
                raise ValueError("rating_column is required when sql_query is provided")
            
            service = DatasetAnalysisService(db)
            result = await service.analyze_sentiment(
                user_id=user_id,
                sql_query=sql_query,
                rating_column=rating_column
            )
        else:
            # Use ReviewAnalysisService for review tables
            if not table_name:
                user_reviews_service = UserReviewsService(db)
                table_name = user_reviews_service.get_user_reviews_table_name(user_id)
            
            service = ReviewAnalysisService(db)
            result = await service.analyze_sentiment_patterns(
                user_id=user_id,
                table_name=table_name,
                filters=filters or {}
            )
        
        # Store results in context for visualization
        if ctx:
            sentiment_analysis = result.get("sentiment_analysis", {})
            overall_sentiment = sentiment_analysis.get("overall_sentiment", {})
            sentiment_dist_data = [
                {"label": "Positive", "value": overall_sentiment.get("positive", 0)},
                {"label": "Neutral", "value": overall_sentiment.get("neutral", 0)},
                {"label": "Negative", "value": overall_sentiment.get("negative", 0)},
            ]
            
            await ctx.set("sentiment_analysis_results", result)
            await ctx.set("sentiment_distribution_data", sentiment_dist_data)
            logger.info("Stored sentiment analysis data in context")
        
        return result
        
    except Exception as e:
        logger.error(f"Error analyzing sentiment patterns: {e}")
        raise


async def detect_trends(
    user_id: str,
    ctx: Optional[Context] = None,
    time_field: str = "date",
    metric: str = "rating",
    period: str = "month",
    table_name: Optional[str] = None,
    sql_query: Optional[str] = None,
    date_column: Optional[str] = None,
    metric_column: Optional[str] = None
) -> Dict[str, Any]:
    """Detect temporal trends in metrics over time.
    
    Args:
        user_id: User ID
        ctx: LlamaIndex Context object
        time_field: Field to use for time analysis (for review tables)
        metric: Metric to analyze (for review tables)
        period: Time period for grouping (for review tables)
        table_name: Optional table name (for review tables)
        sql_query: SQL query (for user datasets - provided by LLM)
        date_column: Column name containing dates (required if sql_query provided)
        metric_column: Column name containing metric values (required if sql_query provided)
        
    Returns:
        Dict with trend analysis
    """
    try:
        db = await _ensure_db_session(ctx)
        
        # If SQL query provided, use DatasetAnalysisService
        if sql_query:
            if not date_column or not metric_column:
                raise ValueError("date_column and metric_column are required when sql_query is provided")
            
            service = DatasetAnalysisService(db)
            result = await service.detect_trends(
                user_id=user_id,
                sql_query=sql_query,
                date_column=date_column,
                metric_column=metric_column,
                period=period
            )
        else:
            # Use ReviewAnalysisService for review tables
            if not table_name:
                user_reviews_service = UserReviewsService(db)
                table_name = user_reviews_service.get_user_reviews_table_name(user_id)
            
            service = ReviewAnalysisService(db)
            result = await service.detect_trends(
                user_id=user_id,
                table_name=table_name,
                time_field=time_field,
                metric=metric,
                period=period
            )
        
        # Store results in context for visualization
        if ctx:
            trends = result.get("trends", [])
            trend_data = [
                {"x": trend.get("period", ""), "y": trend.get("average_rating", trend.get("value", 0))}
                for trend in trends
            ]
            
            sentiment_trend_data = [
                {"x": trend.get("period", ""), "y": trend.get("sentiment_score", 0)}
                for trend in trends
            ]
            
            await ctx.set("trend_analysis_results", result)
            await ctx.set("trend_data", trend_data)
            await ctx.set("sentiment_trend_data", sentiment_trend_data)
            logger.info(f"Stored trend analysis data in context with {len(trend_data)} data points")
        
        return result
        
    except Exception as e:
        logger.error(f"Error detecting trends: {e}")
        raise


async def cluster_reviews(
    user_id: str,
    ctx: Optional[Context] = None,
    n_clusters: int = 5,
    filters: Optional[Dict[str, Any]] = None,
    table_name: Optional[str] = None,
    sql_query: Optional[str] = None,
    text_column: Optional[str] = None
) -> Dict[str, Any]:
    """Cluster similar records to identify common themes.
    
    Args:
        user_id: User ID
        ctx: LlamaIndex Context object
        n_clusters: Number of clusters to create
        filters: Optional filters (for review tables)
        table_name: Optional table name (for review tables)
        sql_query: SQL query (for user datasets - provided by LLM)
        text_column: Column name containing text content (required if sql_query provided)
        
    Returns:
        Dict with clustering results
    """
    try:
        db = await _ensure_db_session(ctx)
        
        # If SQL query provided, use DatasetAnalysisService
        if sql_query:
            if not text_column:
                raise ValueError("text_column is required when sql_query is provided")
            
            service = DatasetAnalysisService(db)
            # HDBSCAN uses min_cluster_size instead of n_clusters
            min_cluster_size = max(3, n_clusters) if n_clusters else 3
            result = await service.cluster_records(
                user_id=user_id,
                sql_query=sql_query,
                text_column=text_column,
                min_cluster_size=min_cluster_size
            )
        else:
            # Use ReviewAnalysisService for review tables
            if not table_name:
                user_reviews_service = UserReviewsService(db)
                table_name = user_reviews_service.get_user_reviews_table_name(user_id)
            
            service = ReviewAnalysisService(db)
            result = await service.cluster_reviews(
                user_id=user_id,
                table_name=table_name,
                n_clusters=n_clusters,
                filters=filters or {}
            )
        
        # Store results in context for visualization
        if ctx:
            clusters = result.get("clusters", [])
            cluster_data = [
                {"label": cluster["theme"], "value": cluster["size"]}
                for cluster in clusters
            ]
            
            await ctx.set("clustering_results", result)
            await ctx.set("cluster_data", cluster_data)
            logger.info(f"Stored clustering data in context with {len(cluster_data)} clusters")
        
        return result
        
    except Exception as e:
        logger.error(f"Error clustering reviews: {e}")
        raise


async def extract_keywords(
    user_id: str,
    ctx: Optional[Context] = None,
    filters: Optional[Dict[str, Any]] = None,
    top_n: int = 20,
    table_name: Optional[str] = None,
    sql_query: Optional[str] = None,
    text_column: Optional[str] = None
) -> Dict[str, Any]:
    """Extract top keywords and phrases.
    
    Args:
        user_id: User ID
        ctx: LlamaIndex Context object
        filters: Optional filters (for review tables)
        top_n: Number of keywords to extract
        table_name: Optional table name (for review tables)
        sql_query: SQL query (for user datasets - provided by LLM)
        text_column: Column name containing text content (required if sql_query provided)
        
    Returns:
        Dict with keywords and frequencies
    """
    try:
        db = await _ensure_db_session(ctx)
        
        # If SQL query provided, use DatasetAnalysisService
        if sql_query:
            if not text_column:
                raise ValueError("text_column is required when sql_query is provided")
            
            service = DatasetAnalysisService(db)
            result = await service.extract_keywords(
                user_id=user_id,
                sql_query=sql_query,
                text_column=text_column,
                top_n=top_n
            )
        else:
            # Use ReviewAnalysisService for review tables
            if not table_name:
                user_reviews_service = UserReviewsService(db)
                table_name = user_reviews_service.get_user_reviews_table_name(user_id)
            
            service = ReviewAnalysisService(db)
            result = await service.extract_keywords(
                user_id=user_id,
                table_name=table_name,
                filters=filters or {},
                top_n=top_n
            )
        
        # Store results in context for visualization
        if ctx:
            keywords = result.get("top_keywords", [])
            keyword_data = [
                {"x": kw["keyword"], "y": kw["frequency"]}
                for kw in keywords[:10]  # Top 10 for visualization
            ]
            
            await ctx.set("keyword_results", result)
            await ctx.set("keyword_data", keyword_data)
            logger.info(f"Stored keyword data in context with {len(keyword_data)} keywords")
        
        return result
        
    except Exception as e:
        logger.error(f"Error extracting keywords: {e}")
        raise


async def semantic_search(
    user_id: str,
    ctx: Optional[Context] = None,
    table_name: Optional[str] = None,
    query_text: Optional[str] = None,
    limit: int = 10
) -> Dict[str, Any]:
    """Perform semantic search on dataset records using pgvector.
    
    Uses OpenAI embeddings and pgvector to find semantically similar records.
    
    Args:
        user_id: User ID
        ctx: LlamaIndex Context object
        table_name: Table name to search (required - provided by LLM)
        query_text: Search query text (required - provided by LLM)
        limit: Maximum number of results to return
        
    Returns:
        Dict with search results and similarity scores
    """
    try:
        db = await _ensure_db_session(ctx)
        
        if not table_name or not query_text:
            raise ValueError("table_name and query_text are required for semantic search")
        
        service = DatasetAnalysisService(db)
        result = await service.semantic_search(
            user_id=user_id,
            table_name=table_name,
            query_text=query_text,
            limit=limit
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error performing semantic search: {e}")
        raise
