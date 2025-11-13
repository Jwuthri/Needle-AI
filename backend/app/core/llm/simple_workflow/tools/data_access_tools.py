"""
Generic data access tools for dataset analysis workflow.

These tools provide database access and schema information for any dataset.
"""

from typing import Any, Dict, Optional

from llama_index.core.workflow import Context
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_async_db_session
from app.services.user_dataset_service import UserDatasetService
from app.utils.logging import get_logger

logger = get_logger(__name__)


async def _ensure_db_session(ctx: Optional[Context] = None) -> AsyncSession:
    """Get database session from context or create new one.
    
    Args:
        ctx: LlamaIndex Context object
        
    Returns:
        Async database session
    """
    if ctx:
        try:
            db_session = await ctx.get("db_session")
            if db_session:
                return db_session
        except Exception as e:
            logger.warning(f"Failed to get db_session from context: {e}")
    
    # Create new session (will be managed by caller)
    async for session in get_async_db_session():
        return session


async def get_user_datasets(user_id: str, ctx: Optional[Context] = None) -> Dict[str, Any]:
    """Get all datasets available for a user."""
    try:
        db = await _ensure_db_session(ctx)
        service = UserDatasetService(db)
        
        datasets = await service.list_datasets(user_id, limit=100)
        
        return {
            "user_id": user_id,
            "datasets": datasets,
            "total_datasets": len(datasets),
        }
        
    except Exception as e:
        logger.error(f"Error getting user datasets: {e}")
        raise


async def get_table_eda(user_id: str, table_name: str, ctx: Optional[Context] = None) -> Dict[str, Any]:
    """Get exploratory data analysis (EDA) for a specific table."""
    try:
        db = await _ensure_db_session(ctx)
        service = UserDatasetService(db)
        
        dataset = await service.get_dataset_by_table_name(user_id, table_name)
        
        if dataset:
            return {
                "table_name": dataset["table_name"],
                "dynamic_table_name": dataset["dynamic_table_name"],
                "row_count": dataset["row_count"],
                "description": dataset.get("description"),
                "meta": dataset.get("meta"),
            }
        
        return {
            "table_name": table_name,
            "row_count": 0,
            "error": "Table not found",
        }
        
    except Exception as e:
        logger.error(f"Error getting table EDA: {e}")
        raise


async def query_user_reviews_table(
    user_id: str,
    query: str,
    filters: Optional[Dict[str, Any]] = None,
    table_name: Optional[str] = None,
    ctx: Optional[Context] = None
) -> Dict[str, Any]:
    """Query any user dataset table."""
    try:
        db = await _ensure_db_session(ctx)
        filters = filters or {}
        
        if not table_name:
            from app.services.user_reviews_service import UserReviewsService
            reviews_service = UserReviewsService(db)
            table_name = reviews_service.get_user_reviews_table_name(user_id)
        
        where_clauses = []
        params = {}
        
        if filters.get("source"):
            where_clauses.append("source = :source")
            params["source"] = filters["source"]
        
        if filters.get("min_rating"):
            where_clauses.append("rating >= :min_rating")
            params["min_rating"] = filters["min_rating"]
        
        if filters.get("max_rating"):
            where_clauses.append("rating <= :max_rating")
            params["max_rating"] = filters["max_rating"]
        
        if filters.get("date_from"):
            where_clauses.append("date >= :date_from")
            params["date_from"] = filters["date_from"]
        
        if filters.get("date_to"):
            where_clauses.append("date <= :date_to")
            params["date_to"] = filters["date_to"]
        
        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        limit = filters.get("limit", 100)
        
        sql_query = f'SELECT {query} FROM "{table_name}" {where_sql} LIMIT {limit}'
        
        result = await db.execute(text(sql_query), params)
        rows = result.fetchall()
        
        data = []
        for row in rows:
            row_dict = {}
            for col in row.keys():
                row_dict[col] = getattr(row, col)
            data.append(row_dict)
        
        return {
            "data": data,
            "count": len(data),
        }
        
    except Exception as e:
        logger.error(f"Error querying table: {e}")
        raise


async def get_review_statistics(
    user_id: str,
    filters: Optional[Dict[str, Any]] = None,
    ctx: Optional[Context] = None
) -> Dict[str, Any]:
    """Get aggregate statistics for any user dataset."""
    try:
        db = await _ensure_db_session(ctx)
        filters = filters or {}
        
        from app.services.user_reviews_service import UserReviewsService
        reviews_service = UserReviewsService(db)
        table_name = reviews_service.get_user_reviews_table_name(user_id)
        
        where_clauses = []
        params = {}
        
        if filters.get("source"):
            where_clauses.append("source = :source")
            params["source"] = filters["source"]
        
        if filters.get("min_rating"):
            where_clauses.append("rating >= :min_rating")
            params["min_rating"] = filters["min_rating"]
        
        if filters.get("max_rating"):
            where_clauses.append("rating <= :max_rating")
            params["max_rating"] = filters["max_rating"]
        
        if filters.get("date_from"):
            where_clauses.append("date >= :date_from")
            params["date_from"] = filters["date_from"]
        
        if filters.get("date_to"):
            where_clauses.append("date <= :date_to")
            params["date_to"] = filters["date_to"]
        
        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        
        stats_query = text(f"""
            SELECT 
                COUNT(*) as total,
                AVG(rating) as avg_rating,
                MIN(rating) as min_rating,
                MAX(rating) as max_rating,
                MIN(date) as min_date,
                MAX(date) as max_date
            FROM "{table_name}"
            {where_sql}
        """)
        
        result = await db.execute(stats_query, params)
        stats_row = result.fetchone()
        
        return {
            "total_count": stats_row.total or 0,
            "average_rating": float(stats_row.avg_rating) if stats_row.avg_rating else None,
            "min_rating": float(stats_row.min_rating) if stats_row.min_rating else None,
            "max_rating": float(stats_row.max_rating) if stats_row.max_rating else None,
            "date_range": {
                "start": stats_row.min_date.isoformat() if stats_row.min_date else None,
                "end": stats_row.max_date.isoformat() if stats_row.max_date else None,
            },
        }
        
    except Exception as e:
        logger.error(f"Error getting review statistics: {e}")
        raise


async def semantic_search_reviews(
    user_id: str,
    query: str,
    limit: int = 10,
    ctx: Optional[Context] = None
) -> Dict[str, Any]:
    """Search any user dataset using semantic similarity."""
    try:
        db = await _ensure_db_session(ctx)
        
        from app.services.user_reviews_service import UserReviewsService
        reviews_service = UserReviewsService(db)
        table_name = reviews_service.get_user_reviews_table_name(user_id)
        
        # Check if table has embedding column
        check_query = text("""
            SELECT column_name 
            FROM information_schema.columns
            WHERE table_schema = 'public' 
            AND table_name = :table_name
            AND column_name = 'embedding'
        """)
        result = await db.execute(check_query, {"table_name": table_name})
        has_embedding = result.scalar() is not None
        
        if not has_embedding:
            # Fallback to text search
            search_query = text(f"""
                SELECT *
                FROM "{table_name}"
                WHERE text ILIKE :query
                LIMIT :limit
            """)
            search_result = await db.execute(search_query, {"query": f"%{query}%", "limit": limit})
        else:
            # Vector search not yet implemented
            return {
                "results": [],
                "count": 0,
                "note": "Vector search not yet implemented",
            }
        
        rows = search_result.fetchall()
        results = []
        for row in rows:
            row_dict = {}
            for col in row.keys():
                row_dict[col] = getattr(row, col)
            results.append(row_dict)
        
        return {
            "results": results,
            "count": len(results),
        }
        
    except Exception as e:
        logger.error(f"Error performing semantic search: {e}")
        raise

