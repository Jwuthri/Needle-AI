"""
Data retrieval and processing services for LlamaIndex workflow.
"""

import csv
import io
from typing import Any, Dict, List
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.utils.logging import get_logger

logger = get_logger(__name__)


class DataRetrievalService:
    """Service for executing data retrieval queries."""

    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _format_as_csv(data: List[Dict[str, Any]]) -> str:
        """Convert list of dicts to CSV string."""
        if not data:
            return ""
        
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
        return output.getvalue()

    def execute_sql_query(self, query: str) -> List[Dict[str, Any]]:
        """Execute a SQL query and return results as list of dicts."""
        try:
            result = self.db.execute(text(query))
            columns = result.keys()
            results = []
            for row in result:
                results.append(dict(zip(columns, row)))
            
            logger.info(f"Executed query, returned {len(results)} rows")
            return results
            
        except Exception as e:
            logger.error(f"Query execution failed: {e}", exc_info=True)
            raise

    def execute_retrieval_plan(
        self,
        plan,  # RetrievalPlan or Dict
        format: str = "json"
    ) -> Dict[str, Any]:
        """
        Execute SQL queries from the retrieval plan.
        
        Args:
            plan: Dict with sql_queries, reasoning, expected_data_types
            format: Output format - "csv", "markdown", or "json"
            
        Returns:
            Dict with data, total_rows, and metadata
        """
        # Handle both RetrievalPlan objects and dict format
        if hasattr(plan, 'reasoning'):
            reasoning = plan.reasoning
            sql_queries = plan.sql_queries
            expected_data_types = plan.expected_data_types
        else:
            reasoning = plan.get('reasoning', 'N/A')
            sql_queries = plan.get("sql_queries", [])
            expected_data_types = plan.get("expected_data_types", [])
        
        logger.info(f"Executing retrieval plan: {reasoning}")
        
        results = {}
        total_rows = 0
        
        for sql_query in sql_queries:
            # Handle both SQLQuery objects and dict format
            if hasattr(sql_query, 'query'):
                query_str = sql_query.query
                result_key = sql_query.result_key
                purpose = sql_query.purpose
            else:
                query_str = sql_query.get("query", "")
                result_key = sql_query.get("result_key", "data")
                purpose = sql_query.get('purpose', 'N/A')
            
            logger.info(f"Executing query for '{purpose}'")
            
            try:
                query_results = self.execute_sql_query(query_str)
                
                if format == "csv":
                    results[result_key] = self._format_as_csv(query_results)
                else:
                    results[result_key] = query_results
                
                total_rows += len(query_results)
                logger.info(f"Retrieved {len(query_results)} rows for {result_key}")
            except Exception as e:
                logger.error(f"Query failed: {e}", exc_info=True)
                results[result_key] = []
                results[f"{result_key}_error"] = str(e)
        
        return {
            "data": results,
            "total_rows": total_rows,
            "format": format,
            "reasoning": reasoning,
            "data_types": expected_data_types
        }
