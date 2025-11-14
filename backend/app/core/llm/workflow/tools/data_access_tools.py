"""
Data Access Tools for Product Review Analysis Workflow.

This module provides real database access for LLM workflow tools.
All functions query actual PostgreSQL data using SQLAlchemy repositories.

Features:
- Real user dataset queries from user_datasets table
- Review queries with filters (platform, sentiment, dates, company)
- PostgreSQL pgvector semantic search with cosine similarity
- OpenAI embeddings for query generation
- Real-time statistics aggregation from database
- Async/sync compatibility using nest_asyncio

All functions are synchronous wrappers around async database operations,
making them compatible with LLM tool calling frameworks.
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, desc, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.llm.workflow.tools.context_store import (
    get_sync_context_store,
    set_workflow_context_value,
)
from app.database.models.review import Review
from app.database.models.user_dataset import UserDataset
from app.database.repositories.review import ReviewRepository
from app.database.repositories.user_dataset import UserDatasetRepository
from app.database.session import get_async_session
from app.services.embedding_service import get_embedding_service
from app.utils.logging import get_logger

logger = get_logger("data_access_tools")


async def _get_db_session() -> AsyncSession:
    """Get a database session."""
    async with get_async_session() as session:
        return session


def get_user_datasets(user_id: str) -> Dict[str, Any]:
    """List all user datasets with metadata.
    
    Args:
        user_id: User ID to get datasets for
        
    Returns:
        Dict with datasets list and metadata
    """
    async def _fetch_datasets():
        async with get_async_session() as db:
            try:
                # Get all user datasets
                datasets = await UserDatasetRepository.list_user_datasets(db, user_id)
                
                dataset_list = []
                for dataset in datasets:
                    dataset_dict = {
                        "id": dataset.id,
                        "table_name": dataset.table_name,
                        "row_count": dataset.row_count,
                        "description": dataset.description,
                        "origin": dataset.origin,
                        "created_at": dataset.created_at.isoformat() if dataset.created_at else None,
                        "updated_at": dataset.updated_at.isoformat() if dataset.updated_at else None,
                    }
                    
                    # Extract metadata if available
                    if dataset.meta:
                        dataset_dict["meta"] = dataset.meta
                    
                    dataset_list.append(dataset_dict)
                
                result = {
                    "user_id": user_id,
                    "datasets": dataset_list,
                    "total_datasets": len(dataset_list),
                }
                
                return result
            except Exception as e:
                logger.error(f"Error fetching user datasets for {user_id}: {e}")
                return {
                    "user_id": user_id,
                    "datasets": [],
                    "total_datasets": 0,
                    "error": str(e),
                }
    
    # Run async function - handle both with and without event loop
    try:
        try:
            loop = asyncio.get_running_loop()
            # If we have a running loop, we can't use asyncio.run()
            # Use run_coroutine_threadsafe or nest_asyncio
            import nest_asyncio
            nest_asyncio.apply()
            result = asyncio.run(_fetch_datasets())
        except RuntimeError:
            # No running loop, safe to use asyncio.run
            result = asyncio.run(_fetch_datasets())
    except Exception as e:
        logger.error(f"Error in get_user_datasets: {e}")
        result = {
            "user_id": user_id,
            "datasets": [],
            "total_datasets": 0,
            "error": str(e),
        }
    
    # Store in context
    _sync_context_store = get_sync_context_store()
    if user_id not in _sync_context_store:
        _sync_context_store[user_id] = {}
    _sync_context_store[user_id]["user_datasets"] = result
    
    # Try to sync to Context if available
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(set_workflow_context_value(user_id, "user_datasets", result))
    except (RuntimeError, AttributeError):
        pass
    
    return result


def get_table_eda(user_id: str, table_name: str) -> Dict[str, Any]:
    """Get EDA metadata for a user dataset table.
    
    Args:
        user_id: User ID
        table_name: Table name to get EDA for
        
    Returns:
        Dict with EDA metadata including column_stats, summary, insights
    """
    async def _fetch_eda():
        async with get_async_session() as db:
            try:
                # Get dataset by table name
                dataset = await UserDatasetRepository.get_by_table_name(db, table_name, user_id)
                
                if not dataset:
                    return {
                        "error": f"Dataset '{table_name}' not found for user {user_id}",
                        "table_name": table_name,
                    }
                
                # Build result from dataset metadata
                result = {
                    "id": dataset.id,
                    "table_name": dataset.table_name,
                    "row_count": dataset.row_count,
                    "summary": dataset.description or "No description available",
                    "created_at": dataset.created_at.isoformat() if dataset.created_at else None,
                }
                
                # Extract metadata
                if dataset.meta:
                    result["meta"] = dataset.meta
                    
                    # Extract field metadata if available
                    if isinstance(dataset.meta, dict):
                        if "field_metadata" in dataset.meta:
                            result["insights"] = dataset.meta["field_metadata"]
                        if "column_stats" in dataset.meta:
                            result["column_stats"] = dataset.meta["column_stats"]
                
                return result
            except Exception as e:
                logger.error(f"Error fetching table EDA for {table_name}: {e}")
                return {
                    "error": str(e),
                    "table_name": table_name,
                }
    
    # Run async function - handle both with and without event loop
    try:
        try:
            loop = asyncio.get_running_loop()
            import nest_asyncio
            nest_asyncio.apply()
            result = asyncio.run(_fetch_eda())
        except RuntimeError:
            result = asyncio.run(_fetch_eda())
    except Exception as e:
        logger.error(f"Error in get_table_eda: {e}")
        result = {
            "error": str(e),
            "table_name": table_name,
        }
    
    # Store in context
    _sync_context_store = get_sync_context_store()
    if user_id not in _sync_context_store:
        _sync_context_store[user_id] = {}
    _sync_context_store[user_id]["table_eda"] = result
    
    # Try to sync to Context if available
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(set_workflow_context_value(user_id, "table_eda", result))
    except (RuntimeError, AttributeError):
        pass
    
    return result


def query_user_reviews_table(
    user_id: str, query: str, filters: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Query reviews table with filters.
    
    Args:
        user_id: User ID (used for tracking context)
        query: Natural language query description
        filters: Optional filters (platform, date_range, sentiment, company_id, etc.)
        
    Returns:
        Dict with query results
    """
    async def _query_reviews():
        async with get_async_session() as db:
            try:
                filters_dict = filters or {}
                
                # Build query
                stmt = select(Review)
                
                # Apply company filter if specified
                if filters_dict.get("company_id"):
                    stmt = stmt.filter(Review.company_id == filters_dict["company_id"])
                
                # Apply platform/source filter
                if filters_dict.get("platform"):
                    stmt = stmt.filter(Review.platform == filters_dict["platform"])
                
                # Apply sentiment filter
                if filters_dict.get("min_sentiment") is not None:
                    stmt = stmt.filter(Review.sentiment_score >= filters_dict["min_sentiment"])
                if filters_dict.get("max_sentiment") is not None:
                    stmt = stmt.filter(Review.sentiment_score <= filters_dict["max_sentiment"])
                
                # Apply date range filter
                if filters_dict.get("date_from"):
                    stmt = stmt.filter(Review.review_date >= filters_dict["date_from"])
                if filters_dict.get("date_to"):
                    stmt = stmt.filter(Review.review_date <= filters_dict["date_to"])
                
                # Order and limit
                limit = filters_dict.get("limit", 100)
                offset = filters_dict.get("offset", 0)
                stmt = stmt.order_by(desc(Review.scraped_at)).limit(limit).offset(offset)
                
                # Execute query
                result_rows = await db.execute(stmt)
                reviews = result_rows.scalars().all()
                
                # Convert to dict
                results_list = []
                for review in reviews:
                    results_list.append({
                        "id": review.id,
                        "company_id": review.company_id,
                        "content": review.content,
                        "author": review.author,
                        "platform": review.platform,
                        "sentiment_score": review.sentiment_score,
                        "url": review.url,
                        "scraped_at": review.scraped_at.isoformat() if review.scraped_at else None,
                        "review_date": review.review_date.isoformat() if review.review_date else None,
                        "extra_metadata": review.extra_metadata,
                    })
                
                # Get total count for this query
                count_stmt = select(func.count(Review.id))
                if filters_dict.get("company_id"):
                    count_stmt = count_stmt.filter(Review.company_id == filters_dict["company_id"])
                if filters_dict.get("platform"):
                    count_stmt = count_stmt.filter(Review.platform == filters_dict["platform"])
                
                total_count_result = await db.execute(count_stmt)
                total_count = total_count_result.scalar() or 0
                
                result = {
                    "user_id": user_id,
                    "query": query,
                    "filters_applied": filters_dict,
                    "results": results_list,
                    "total_count": total_count,
                    "returned_count": len(results_list),
                }
                
                return result
            except Exception as e:
                logger.error(f"Error querying reviews: {e}")
                return {
                    "user_id": user_id,
                    "query": query,
                    "error": str(e),
                    "results": [],
                    "total_count": 0,
                    "returned_count": 0,
                }
    
    # Run async function - handle both with and without event loop
    try:
        try:
            loop = asyncio.get_running_loop()
            import nest_asyncio
            nest_asyncio.apply()
            result = asyncio.run(_query_reviews())
        except RuntimeError:
            result = asyncio.run(_query_reviews())
    except Exception as e:
        logger.error(f"Error in query_user_reviews_table: {e}")
        result = {
            "user_id": user_id,
            "query": query,
            "error": str(e),
            "results": [],
            "total_count": 0,
            "returned_count": 0,
        }
    
    # Extract schema from first result
    schema = {}
    if result.get("results"):
        first_row = result["results"][0]
        for col_name, col_value in first_row.items():
            schema[col_name] = type(col_value).__name__
    
    # Store in context with schema
    _sync_context_store = get_sync_context_store()
    if user_id not in _sync_context_store:
        _sync_context_store[user_id] = {}
    _sync_context_store[user_id]["reviews_data"] = result
    _sync_context_store[user_id]["reviews_data_schema"] = {
        "columns": list(schema.keys()),
        "types": schema,
        "sample_row": result["results"][0] if result.get("results") else {},
    }
    
    # Try to sync to Context if available
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(set_workflow_context_value(user_id, "reviews_data", result))
            asyncio.create_task(set_workflow_context_value(user_id, "reviews_data_schema", _sync_context_store[user_id]["reviews_data_schema"]))
    except (RuntimeError, AttributeError):
        pass
    
    return result


def semantic_search_reviews(
    user_id: str, 
    query: str, 
    limit: int = 10,
    company_id: Optional[str] = None,
    similarity_threshold: float = 0.7
) -> Dict[str, Any]:
    """Perform semantic search on reviews using PostgreSQL pgvector embeddings.
    
    Args:
        user_id: User ID
        query: Search query
        limit: Maximum number of results
        company_id: Optional company ID filter
        similarity_threshold: Minimum similarity score (0-1)
        
    Returns:
        Dict with search results and similarity scores
    """
    async def _semantic_search():
        async with get_async_session() as db:
            try:
                # Generate embedding for query
                embedding_service = get_embedding_service()
                query_embedding = await embedding_service.generate_embedding(query)
                
                if not query_embedding:
                    return {
                        "user_id": user_id,
                        "query": query,
                        "error": "Failed to generate query embedding",
                        "results": [],
                        "total_found": 0,
                        "returned_count": 0,
                    }
                
                # Use repository's similarity search with pgvector
                reviews_with_scores = await ReviewRepository.similarity_search(
                    db=db,
                    query_embedding=query_embedding,
                    company_id=company_id,
                    limit=limit,
                    similarity_threshold=similarity_threshold
                )
                
                # Convert to dict format
                results_list = []
                for review, similarity_score in reviews_with_scores:
                    results_list.append({
                        "id": review.id,
                        "content": review.content,
                        "company_id": review.company_id,
                        "platform": review.platform,
                        "sentiment_score": review.sentiment_score,
                        "author": review.author,
                        "url": review.url,
                        "similarity_score": round(similarity_score, 4),
                        "scraped_at": review.scraped_at.isoformat() if review.scraped_at else None,
                        "review_date": review.review_date.isoformat() if review.review_date else None,
                    })
                
                result = {
                    "user_id": user_id,
                    "query": query,
                    "company_id": company_id,
                    "similarity_threshold": similarity_threshold,
                    "results": results_list,
                    "total_found": len(results_list),
                    "returned_count": len(results_list),
                }
                
                return result
            except Exception as e:
                logger.error(f"Error in semantic search: {e}")
                return {
                    "user_id": user_id,
                    "query": query,
                    "error": str(e),
                    "results": [],
                    "total_found": 0,
                    "returned_count": 0,
                }
    
    # Run async function - handle both with and without event loop
    try:
        try:
            loop = asyncio.get_running_loop()
            import nest_asyncio
            nest_asyncio.apply()
            result = asyncio.run(_semantic_search())
        except RuntimeError:
            result = asyncio.run(_semantic_search())
    except Exception as e:
        logger.error(f"Error in semantic_search_reviews: {e}")
        result = {
            "user_id": user_id,
            "query": query,
            "error": str(e),
            "results": [],
            "total_found": 0,
            "returned_count": 0,
        }
    
    # Extract schema from first result
    schema = {}
    if result.get("results"):
        first_row = result["results"][0]
        for col_name, col_value in first_row.items():
            schema[col_name] = type(col_value).__name__
    
    # Store in context with schema
    _sync_context_store = get_sync_context_store()
    if user_id not in _sync_context_store:
        _sync_context_store[user_id] = {}
    _sync_context_store[user_id]["semantic_search_results"] = result
    _sync_context_store[user_id]["semantic_search_results_schema"] = {
        "columns": list(schema.keys()),
        "types": schema,
        "sample_row": result["results"][0] if result.get("results") else {},
    }
    
    # Try to sync to Context if available
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(set_workflow_context_value(user_id, "semantic_search_results", result))
            asyncio.create_task(set_workflow_context_value(user_id, "semantic_search_results_schema", _sync_context_store[user_id]["semantic_search_results_schema"]))
    except (RuntimeError, AttributeError):
        pass
    
    return result


def get_review_statistics(
    user_id: str, 
    filters: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Get aggregate statistics for reviews from PostgreSQL.
    
    Args:
        user_id: User ID
        filters: Optional filters (company_id, platform, date_range, etc.)
        
    Returns:
        Dict with statistics
    """
    async def _get_statistics():
        async with get_async_session() as db:
            try:
                filters_dict = filters or {}
                
                # Build base query
                base_filter = []
                if filters_dict.get("company_id"):
                    base_filter.append(Review.company_id == filters_dict["company_id"])
                if filters_dict.get("platform"):
                    base_filter.append(Review.platform == filters_dict["platform"])
                if filters_dict.get("date_from"):
                    base_filter.append(Review.review_date >= filters_dict["date_from"])
                if filters_dict.get("date_to"):
                    base_filter.append(Review.review_date <= filters_dict["date_to"])
                
                # Total count
                count_stmt = select(func.count(Review.id))
                if base_filter:
                    count_stmt = count_stmt.filter(and_(*base_filter))
                total_result = await db.execute(count_stmt)
                total_reviews = total_result.scalar() or 0
                
                # Platform/source distribution
                platform_stmt = select(
                    Review.platform,
                    func.count(Review.id).label('count')
                ).group_by(Review.platform)
                if base_filter:
                    platform_stmt = platform_stmt.filter(and_(*base_filter))
                platform_result = await db.execute(platform_stmt)
                source_distribution = {row.platform or "unknown": row.count for row in platform_result.all()}
                
                # Sentiment distribution (positive/neutral/negative)
                sentiment_stmt = select(
                    func.sum(func.case((Review.sentiment_score > 0.33, 1), else_=0)).label('positive'),
                    func.sum(func.case((and_(Review.sentiment_score >= -0.33, Review.sentiment_score <= 0.33), 1), else_=0)).label('neutral'),
                    func.sum(func.case((Review.sentiment_score < -0.33, 1), else_=0)).label('negative'),
                    func.avg(Review.sentiment_score).label('avg_sentiment')
                ).filter(Review.sentiment_score.isnot(None))
                if base_filter:
                    sentiment_stmt = sentiment_stmt.filter(and_(*base_filter))
                sentiment_result = await db.execute(sentiment_stmt)
                sentiment_row = sentiment_result.one()
                
                # Date range
                date_stmt = select(
                    func.min(Review.review_date).label('earliest'),
                    func.max(Review.review_date).label('latest')
                ).filter(Review.review_date.isnot(None))
                if base_filter:
                    date_stmt = date_stmt.filter(and_(*base_filter))
                date_result = await db.execute(date_stmt)
                date_row = date_result.one()
                
                result = {
                    "user_id": user_id,
                    "filters_applied": filters_dict,
                    "statistics": {
                        "total_reviews": total_reviews,
                        "average_sentiment": round(float(sentiment_row.avg_sentiment), 2) if sentiment_row.avg_sentiment else 0.0,
                        "source_distribution": source_distribution,
                        "sentiment_distribution": {
                            "positive": int(sentiment_row.positive or 0),
                            "neutral": int(sentiment_row.neutral or 0),
                            "negative": int(sentiment_row.negative or 0),
                        },
                        "date_range": {
                            "earliest": date_row.earliest.isoformat() if date_row.earliest else None,
                            "latest": date_row.latest.isoformat() if date_row.latest else None,
                        },
                    },
                }
                
                return result
            except Exception as e:
                logger.error(f"Error fetching review statistics: {e}")
                return {
                    "user_id": user_id,
                    "filters_applied": filters or {},
                    "error": str(e),
                    "statistics": {},
                }
    
    # Run async function - handle both with and without event loop
    try:
        try:
            loop = asyncio.get_running_loop()
            import nest_asyncio
            nest_asyncio.apply()
            result = asyncio.run(_get_statistics())
        except RuntimeError:
            result = asyncio.run(_get_statistics())
    except Exception as e:
        logger.error(f"Error in get_review_statistics: {e}")
        result = {
            "user_id": user_id,
            "filters_applied": filters or {},
            "error": str(e),
            "statistics": {},
        }
    
    # Store in context
    _sync_context_store = get_sync_context_store()
    if user_id not in _sync_context_store:
        _sync_context_store[user_id] = {}
    _sync_context_store[user_id]["review_statistics"] = result
    
    # Try to sync to Context if available
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(set_workflow_context_value(user_id, "review_statistics", result))
    except (RuntimeError, AttributeError):
        pass
    
    return result

