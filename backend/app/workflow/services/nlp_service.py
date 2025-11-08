"""
NLP Service for executing NLP analysis tool calls.
"""

from typing import Dict, Any, List
from app import get_logger
from app.workflow.tools.nlp_tools import (
    execute_tfidf,
    execute_clustering,
    execute_sentiment_analysis,
    execute_feature_extraction
)

logger = get_logger(__name__)


class NLPService:
    """Service for executing NLP analysis on retrieved data."""
    
    def _make_hashable(self, obj: Any) -> Any:
        """Recursively convert an object to a hashable type."""
        if isinstance(obj, dict):
            return tuple(sorted((k, self._make_hashable(v)) for k, v in obj.items()))
        elif isinstance(obj, list):
            return tuple(self._make_hashable(item) for item in obj)
        elif isinstance(obj, set):
            return frozenset(self._make_hashable(item) for item in obj)
        else:
            return obj
    
    def execute_tool_calls(
        self,
        tool_calls: List[Dict[str, Any]],
        retrieved_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute NLP tool calls on the retrieved data (with deduplication).
        
        Args:
            tool_calls: List of tool call specifications from the agent
            retrieved_data: Retrieved data containing datasets
            
        Returns:
            Dictionary with results from all tool executions
        """
        results = {}
        seen_calls = set()
        deduplicated_count = 0
        
        for tool_call in tool_calls:
            tool_name = tool_call.get("tool")
            dataset_name = tool_call.get("dataset_name")
            parameters = tool_call.get("parameters", {})
            
            # Create a unique key for deduplication
            # Convert parameters to a hashable format (handles lists, dicts, etc.)
            param_key = self._make_hashable(parameters)
            call_signature = (tool_name, dataset_name, param_key)
            
            # Skip if we've already executed this exact call
            if call_signature in seen_calls:
                logger.info(f"Skipping duplicate call: {tool_name} on {dataset_name}")
                deduplicated_count += 1
                continue
            
            seen_calls.add(call_signature)
            logger.info(f"Executing {tool_name} on dataset {dataset_name}")
            
            # Get the dataset from retrieved_data
            if "data" not in retrieved_data or dataset_name not in retrieved_data["data"]:
                logger.warning(f"Dataset {dataset_name} not found in retrieved data")
                results[f"{tool_name}_{dataset_name}"] = {
                    "error": f"Dataset {dataset_name} not found"
                }
                continue
            
            data = retrieved_data["data"][dataset_name]
            
            try:
                # Execute the appropriate tool
                if tool_name == "compute_tfidf":
                    result = execute_tfidf(data, **parameters)
                elif tool_name == "cluster_reviews":
                    result = execute_clustering(data, **parameters)
                elif tool_name == "analyze_sentiment":
                    result = execute_sentiment_analysis(data, **parameters)
                elif tool_name == "identify_features":
                    result = execute_feature_extraction(data, **parameters)
                else:
                    logger.warning(f"Unknown tool: {tool_name}")
                    result = {"error": f"Unknown tool: {tool_name}"}
                
                results[f"{tool_name}@{dataset_name}"] = result
                logger.info(f"✓ {tool_name} completed successfully")
                
            except Exception as e:
                logger.error(f"Error executing {tool_name}: {e}", exc_info=True)
                results[f"{tool_name}_{dataset_name}"] = {
                    "error": str(e)
                }
        
        return {
            "tool_results": results,
            "total_tools_requested": len(tool_calls),
            "total_tools_executed": len(seen_calls),
            "deduplicated": deduplicated_count,
            "successful": sum(1 for r in results.values() if "error" not in r),
            "seen_calls": list(seen_calls)
        }
        