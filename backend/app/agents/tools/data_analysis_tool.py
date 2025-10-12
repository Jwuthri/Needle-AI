"""
Data Analysis Tool - Performs statistical operations on tabular data.
"""

from typing import Any, Dict, List, Optional

from app.agents.tools.base_tool import BaseTool, ToolResult
from app.utils.logging import get_logger

logger = get_logger("data_analysis_tool")


class DataAnalysisTool(BaseTool):
    """
    Performs statistical analysis on tabular data.
    
    Supports operations like:
    - Aggregations (sum, mean, median, count)
    - Groupby operations
    - Filtering
    - Sorting
    """
    
    @property
    def name(self) -> str:
        return "data_analysis"
    
    @property
    def description(self) -> str:
        return """Perform statistical analysis on tabular data.

Use this tool when you need to:
- Calculate statistics (sum, mean, median, count, min, max)
- Group data by categories
- Filter data based on conditions
- Sort and rank data

Parameters:
- data: List of dictionaries representing rows
- operation: Type of operation (aggregate, groupby, filter, sort)
- column: Column name to operate on
- group_by: Column name to group by (for groupby operation)
- aggregation: Aggregation function (sum, mean, median, count, min, max)
- condition: Filter condition (for filter operation)

Returns processed data and summary statistics.
"""
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "data": {
                    "type": "array",
                    "description": "List of data rows (dictionaries)"
                },
                "operation": {
                    "type": "string",
                    "enum": ["aggregate", "groupby", "filter", "sort", "stats"],
                    "description": "Type of analysis operation"
                },
                "column": {
                    "type": "string",
                    "description": "Column name to analyze"
                },
                "group_by": {
                    "type": "string",
                    "description": "Column to group by (for groupby)"
                },
                "aggregation": {
                    "type": "string",
                    "enum": ["sum", "mean", "median", "count", "min", "max", "std"],
                    "description": "Aggregation function"
                },
                "sort_descending": {
                    "type": "boolean",
                    "description": "Sort in descending order",
                    "default": True
                }
            },
            "required": ["data", "operation"]
        }
    
    async def execute(
        self,
        data: List[Dict[str, Any]],
        operation: str,
        column: Optional[str] = None,
        group_by: Optional[str] = None,
        aggregation: Optional[str] = "count",
        sort_descending: bool = True,
        **kwargs
    ) -> ToolResult:
        """
        Perform data analysis operation.
        
        Args:
            data: List of data rows
            operation: Type of operation
            column: Column to analyze
            group_by: Column to group by
            aggregation: Aggregation function
            sort_descending: Sort order
            
        Returns:
            ToolResult with analysis results
        """
        try:
            if not data:
                return ToolResult(
                    success=True,
                    data={"result": [], "stats": {}},
                    summary="No data to analyze"
                )
            
            if operation == "stats":
                result = self._calculate_stats(data, column)
            elif operation == "aggregate":
                result = self._aggregate(data, column, aggregation)
            elif operation == "groupby":
                result = self._groupby(data, group_by, column, aggregation)
            elif operation == "sort":
                result = self._sort(data, column, sort_descending)
            elif operation == "filter":
                result = self._filter(data, column, kwargs.get("condition"))
            else:
                return ToolResult(
                    success=False,
                    summary=f"Unknown operation: {operation}",
                    error=f"Operation '{operation}' not supported"
                )
            
            return ToolResult(
                success=True,
                data=result,
                summary=self._generate_summary(operation, result),
                metadata={
                    "operation": operation,
                    "rows_processed": len(data),
                    "column": column
                }
            )
            
        except Exception as e:
            logger.error(f"Data analysis failed: {e}", exc_info=True)
            return ToolResult(
                success=False,
                summary=f"Analysis failed: {str(e)}",
                error=str(e)
            )
    
    def _calculate_stats(self, data: List[Dict], column: Optional[str] = None) -> Dict[str, Any]:
        """Calculate comprehensive statistics."""
        if not column:
            # Overall stats
            return {
                "total_rows": len(data),
                "columns": list(data[0].keys()) if data else [],
                "summary": f"{len(data)} rows available"
            }
        
        # Extract numeric values
        values = []
        for row in data:
            val = row.get(column)
            if isinstance(val, (int, float)):
                values.append(val)
        
        if not values:
            return {
                "column": column,
                "error": "No numeric values found"
            }
        
        import statistics
        
        stats = {
            "column": column,
            "count": len(values),
            "sum": sum(values),
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "min": min(values),
            "max": max(values),
            "std": statistics.stdev(values) if len(values) > 1 else 0
        }
        
        return stats
    
    def _aggregate(self, data: List[Dict], column: str, aggregation: str) -> Dict[str, Any]:
        """Perform aggregation on a column."""
        values = [row.get(column) for row in data if row.get(column) is not None]
        
        if not values:
            return {"result": None, "count": 0}
        
        import statistics
        
        if aggregation == "sum":
            result = sum(v for v in values if isinstance(v, (int, float)))
        elif aggregation == "mean":
            numeric_values = [v for v in values if isinstance(v, (int, float))]
            result = statistics.mean(numeric_values) if numeric_values else None
        elif aggregation == "median":
            numeric_values = [v for v in values if isinstance(v, (int, float))]
            result = statistics.median(numeric_values) if numeric_values else None
        elif aggregation == "count":
            result = len(values)
        elif aggregation == "min":
            result = min(values)
        elif aggregation == "max":
            result = max(values)
        elif aggregation == "std":
            numeric_values = [v for v in values if isinstance(v, (int, float))]
            result = statistics.stdev(numeric_values) if len(numeric_values) > 1 else 0
        else:
            result = None
        
        return {
            "result": result,
            "count": len(values),
            "aggregation": aggregation,
            "column": column
        }
    
    def _groupby(
        self,
        data: List[Dict],
        group_by: str,
        column: Optional[str],
        aggregation: str
    ) -> Dict[str, Any]:
        """Group data and perform aggregation."""
        groups = {}
        
        for row in data:
            key = row.get(group_by, "unknown")
            if key not in groups:
                groups[key] = []
            groups[key].append(row)
        
        results = []
        for group_key, group_data in groups.items():
            if column:
                agg_result = self._aggregate(group_data, column, aggregation)
                results.append({
                    group_by: group_key,
                    "count": len(group_data),
                    f"{aggregation}_{column}": agg_result["result"]
                })
            else:
                results.append({
                    group_by: group_key,
                    "count": len(group_data)
                })
        
        # Sort by count descending
        results.sort(key=lambda x: x.get("count", 0), reverse=True)
        
        return {
            "groups": results,
            "total_groups": len(results),
            "group_by": group_by
        }
    
    def _sort(self, data: List[Dict], column: str, descending: bool) -> Dict[str, Any]:
        """Sort data by column."""
        sorted_data = sorted(
            data,
            key=lambda x: x.get(column, 0),
            reverse=descending
        )
        
        return {
            "data": sorted_data,
            "count": len(sorted_data),
            "sorted_by": column,
            "descending": descending
        }
    
    def _filter(self, data: List[Dict], column: str, condition: Any) -> Dict[str, Any]:
        """Filter data based on condition."""
        # Simple equality filter for now
        filtered_data = [row for row in data if row.get(column) == condition]
        
        return {
            "data": filtered_data,
            "count": len(filtered_data),
            "original_count": len(data),
            "filtered_by": {column: condition}
        }
    
    def _generate_summary(self, operation: str, result: Dict[str, Any]) -> str:
        """Generate human-readable summary."""
        if operation == "stats":
            if "mean" in result:
                return f"Stats for {result['column']}: mean={result['mean']:.2f}, median={result['median']:.2f}"
            return f"Dataset has {result.get('total_rows', 0)} rows"
        
        elif operation == "aggregate":
            agg_type = result.get("aggregation", "")
            value = result.get("result")
            column = result.get("column", "")
            if value is not None:
                return f"{agg_type.capitalize()} of {column}: {value}"
            return f"No data for {column}"
        
        elif operation == "groupby":
            total = result.get("total_groups", 0)
            return f"Grouped into {total} categories"
        
        elif operation == "sort":
            count = result.get("count", 0)
            return f"Sorted {count} rows by {result.get('sorted_by', '')}"
        
        elif operation == "filter":
            count = result.get("count", 0)
            original = result.get("original_count", 0)
            return f"Filtered to {count} of {original} rows"
        
        return "Analysis complete"

