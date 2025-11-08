"""
Database Query Tool - Query PostgreSQL database for structured data.
"""

from typing import Any, Dict, List, Optional
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.base_tool import BaseTool, ToolResult
from app.database.models.company import Company
from app.database.models.review import Review
from app.database.models.scraping_job import ScrapingJob
from app.utils.logging import get_logger

logger = get_logger("database_query_tool")


class DatabaseQueryTool(BaseTool):
    """
    Query the database for companies, reviews, scraping jobs, and analytics.
    
    Provides safe, structured access to the database without SQL injection risks.
    """
    
    def __init__(self, db_session: Optional[AsyncSession] = None):
        super().__init__()
        self.db = db_session
    
    @property
    def name(self) -> str:
        return "database_query"
    
    @property
    def description(self) -> str:
        return """Query the database for structured data about companies, reviews, and scraping jobs.

Use this tool when:
- Need to count reviews, companies, or jobs
- Want to get company information by name or ID
- Need to filter reviews by various criteria
- Want aggregated statistics (counts, averages, etc.)

Parameters:
- query_type: "companies" | "reviews" | "jobs" | "analytics"
- filters: Dict of filter parameters (company_id, sentiment, source, etc.)
- aggregation: Optional aggregation (count, avg, sum, min, max)
- group_by: Optional field to group results by
- limit: Max results (default 100, max 1000)
- offset: Number of results to skip (for pagination)

Returns structured data matching the query.
"""
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query_type": {
                    "type": "string",
                    "enum": ["companies", "reviews", "jobs", "analytics"],
                    "description": "Type of query to execute"
                },
                "filters": {
                    "type": "object",
                    "description": "Filter parameters",
                    "properties": {
                        "company_id": {"type": "string"},
                        "company_name": {"type": "string"},
                        "sentiment": {"type": "string"},
                        "source": {"type": "string"},
                        "min_rating": {"type": "number"},
                        "max_rating": {"type": "number"},
                        "date_from": {"type": "string"},
                        "date_to": {"type": "string"}
                    }
                },
                "aggregation": {
                    "type": "string",
                    "enum": ["count", "avg", "sum", "min", "max"],
                    "description": "Aggregation function to apply"
                },
                "group_by": {
                    "type": "string",
                    "description": "Field to group by"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum results",
                    "default": 100,
                    "minimum": 1,
                    "maximum": 1000
                },
                "offset": {
                    "type": "integer",
                    "description": "Results to skip",
                    "default": 0,
                    "minimum": 0
                }
            },
            "required": ["query_type"]
        }
    
    def set_db_session(self, db: AsyncSession):
        """Set database session (needed for execution)."""
        self.db = db
    
    async def execute(
        self,
        query_type: str,
        filters: Optional[Dict[str, Any]] = None,
        aggregation: Optional[str] = None,
        group_by: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        **kwargs
    ) -> ToolResult:
        """
        Execute database query.
        
        Args:
            query_type: Type of query (companies, reviews, jobs, analytics)
            filters: Filter parameters
            aggregation: Aggregation function
            group_by: Field to group by
            limit: Maximum results
            offset: Results to skip
            
        Returns:
            ToolResult with query results
        """
        if not self.db:
            return ToolResult(
                success=False,
                summary="Database session not available",
                error="No database session configured"
            )
        
        filters = filters or {}
        limit = min(limit, 1000)  # Hard cap
        
        try:
            if query_type == "companies":
                return await self._query_companies(filters, limit, offset)
            elif query_type == "reviews":
                return await self._query_reviews(filters, aggregation, group_by, limit, offset)
            elif query_type == "jobs":
                return await self._query_jobs(filters, limit, offset)
            elif query_type == "analytics":
                return await self._query_analytics(filters)
            else:
                return ToolResult(
                    success=False,
                    summary=f"Unknown query type: {query_type}",
                    error=f"Supported types: companies, reviews, jobs, analytics"
                )
                
        except Exception as e:
            logger.error(f"Database query failed: {e}", exc_info=True)
            return ToolResult(
                success=False,
                summary=f"Database query failed: {str(e)}",
                error=str(e)
            )
    
    async def _query_companies(
        self, 
        filters: Dict[str, Any], 
        limit: int, 
        offset: int
    ) -> ToolResult:
        """Query companies table."""
        query = select(Company)
        
        # Apply filters
        if "company_id" in filters:
            query = query.where(Company.id == filters["company_id"])
        if "company_name" in filters:
            query = query.where(Company.name.ilike(f"%{filters['company_name']}%"))
        
        query = query.limit(limit).offset(offset)
        
        result = await self.db.execute(query)
        companies = result.scalars().all()
        
        data = {
            "companies": [
                {
                    "id": str(c.id),
                    "name": c.name,
                    "domain": c.domain,
                    "created_at": c.created_at.isoformat() if c.created_at else None
                }
                for c in companies
            ],
            "count": len(companies),
            "limit": limit,
            "offset": offset
        }
        
        summary = f"Found {len(companies)} companies"
        if "company_name" in filters:
            summary += f" matching '{filters['company_name']}'"
        
        return ToolResult(
            success=True,
            data=data,
            summary=summary
        )
    
    async def _query_reviews(
        self,
        filters: Dict[str, Any],
        aggregation: Optional[str],
        group_by: Optional[str],
        limit: int,
        offset: int
    ) -> ToolResult:
        """Query reviews table."""
        
        # Handle aggregation queries
        if aggregation:
            return await self._aggregate_reviews(filters, aggregation, group_by)
        
        # Regular select query
        query = select(Review)
        
        # Apply filters
        conditions = []
        if "company_id" in filters:
            conditions.append(Review.company_id == filters["company_id"])
        if "source" in filters:
            conditions.append(Review.source.ilike(f"%{filters['source']}%"))
        if "min_rating" in filters:
            conditions.append(Review.rating >= filters["min_rating"])
        if "max_rating" in filters:
            conditions.append(Review.rating <= filters["max_rating"])
        
        if conditions:
            query = query.where(and_(*conditions))
        
        query = query.limit(limit).offset(offset)
        
        result = await self.db.execute(query)
        reviews = result.scalars().all()
        
        data = {
            "reviews": [
                {
                    "id": str(r.id),
                    "company_id": str(r.company_id),
                    "content": r.content[:200] + "..." if r.content and len(r.content) > 200 else r.content,
                    "rating": r.rating,
                    "sentiment_score": r.sentiment_score,
                    "source": r.source,
                    "created_at": r.created_at.isoformat() if r.created_at else None
                }
                for r in reviews
            ],
            "count": len(reviews),
            "limit": limit,
            "offset": offset
        }
        
        summary = f"Found {len(reviews)} reviews"
        if "company_id" in filters:
            summary += f" for company {filters['company_id']}"
        
        return ToolResult(
            success=True,
            data=data,
            summary=summary
        )
    
    async def _aggregate_reviews(
        self,
        filters: Dict[str, Any],
        aggregation: str,
        group_by: Optional[str]
    ) -> ToolResult:
        """Execute aggregation query on reviews."""
        
        # Build aggregation expression
        if aggregation == "count":
            agg_expr = func.count(Review.id)
        elif aggregation == "avg":
            agg_expr = func.avg(Review.rating)
        elif aggregation == "sum":
            agg_expr = func.sum(Review.rating)
        elif aggregation == "min":
            agg_expr = func.min(Review.rating)
        elif aggregation == "max":
            agg_expr = func.max(Review.rating)
        else:
            return ToolResult(
                success=False,
                summary=f"Unknown aggregation: {aggregation}",
                error=f"Supported: count, avg, sum, min, max"
            )
        
        # Build query
        if group_by:
            if group_by == "source":
                query = select(Review.source, agg_expr.label("value"))
                query = query.group_by(Review.source)
            elif group_by == "company_id":
                query = select(Review.company_id, agg_expr.label("value"))
                query = query.group_by(Review.company_id)
            else:
                return ToolResult(
                    success=False,
                    summary=f"Unknown group_by field: {group_by}",
                    error="Supported: source, company_id"
                )
        else:
            query = select(agg_expr.label("value"))
        
        # Apply filters
        conditions = []
        if "company_id" in filters:
            conditions.append(Review.company_id == filters["company_id"])
        if "source" in filters:
            conditions.append(Review.source.ilike(f"%{filters['source']}%"))
        
        if conditions:
            query = query.where(and_(*conditions))
        
        result = await self.db.execute(query)
        rows = result.all()
        
        # Format results
        if group_by:
            data = {
                "aggregation": aggregation,
                "group_by": group_by,
                "results": [
                    {
                        group_by: str(row[0]),
                        "value": float(row[1]) if row[1] is not None else 0
                    }
                    for row in rows
                ]
            }
            summary = f"Aggregated {aggregation} of reviews grouped by {group_by}: {len(rows)} groups"
        else:
            value = float(rows[0][0]) if rows and rows[0][0] is not None else 0
            data = {
                "aggregation": aggregation,
                "value": value
            }
            summary = f"Review {aggregation}: {value}"
        
        return ToolResult(
            success=True,
            data=data,
            summary=summary
        )
    
    async def _query_jobs(
        self,
        filters: Dict[str, Any],
        limit: int,
        offset: int
    ) -> ToolResult:
        """Query scraping jobs table."""
        query = select(ScrapingJob)
        
        # Apply filters
        if "company_id" in filters:
            query = query.where(ScrapingJob.company_id == filters["company_id"])
        
        query = query.limit(limit).offset(offset).order_by(ScrapingJob.created_at.desc())
        
        result = await self.db.execute(query)
        jobs = result.scalars().all()
        
        data = {
            "jobs": [
                {
                    "id": str(j.id),
                    "company_id": str(j.company_id),
                    "source_type": j.source_type,
                    "status": j.status,
                    "progress": j.progress,
                    "created_at": j.created_at.isoformat() if j.created_at else None
                }
                for j in jobs
            ],
            "count": len(jobs),
            "limit": limit,
            "offset": offset
        }
        
        summary = f"Found {len(jobs)} scraping jobs"
        
        return ToolResult(
            success=True,
            data=data,
            summary=summary
        )
    
    async def _query_analytics(self, filters: Dict[str, Any]) -> ToolResult:
        """Get analytics summary."""
        company_id = filters.get("company_id")
        
        # Count companies
        company_count_query = select(func.count(Company.id))
        company_result = await self.db.execute(company_count_query)
        total_companies = company_result.scalar()
        
        # Count reviews
        review_count_query = select(func.count(Review.id))
        if company_id:
            review_count_query = review_count_query.where(Review.company_id == company_id)
        review_result = await self.db.execute(review_count_query)
        total_reviews = review_result.scalar()
        
        # Average rating
        avg_rating_query = select(func.avg(Review.rating))
        if company_id:
            avg_rating_query = avg_rating_query.where(Review.company_id == company_id)
        avg_result = await self.db.execute(avg_rating_query)
        avg_rating = avg_result.scalar() or 0
        
        data = {
            "total_companies": total_companies,
            "total_reviews": total_reviews,
            "average_rating": float(avg_rating),
            "company_id": company_id
        }
        
        summary = f"Analytics: {total_companies} companies, {total_reviews} reviews, avg rating {avg_rating:.2f}"
        
        return ToolResult(
            success=True,
            data=data,
            summary=summary
        )

