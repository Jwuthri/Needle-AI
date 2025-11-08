"""
Event definitions for LlamaIndex workflow.

Events are used to pass data between workflow steps.
"""

from typing import Any, Dict, List, Optional
from llama_index.core.workflow import Event

from app.workflow.agents.base import RetrievalPlan


class QueryAnalysisEvent(Event):
    """Trigger event for query analysis step."""
    pass


class FormatDetectionEvent(Event):
    """Trigger event for format detection step."""
    pass


class RetrievalPlanEvent(Event):
    """Trigger event for retrieval planning step."""
    pass


class DataRetrievalEvent(Event):
    """Trigger event for data retrieval step."""
    pass


class NLPAnalysisEvent(Event):
    """Trigger event for NLP analysis step."""
    pass


class WriterContextEvent(Event):
    """Trigger event for answer generation step."""
    pass


# Enhanced Events for SQL Query Validation and Retry System

class QueryValidationEvent(Event):
    """
    Event for query validation step.
    
    Triggered when a retrieval plan needs to be validated before execution.
    Contains the original query context and plan to be validated.
    """
    query: str
    analysis: Any
    format_info: Any
    plan: RetrievalPlan
    retry_count: int = 0


class QueryFailedEvent(Event):
    """
    Event when query validation or execution fails.
    
    Triggered when validation fails, query execution fails, or data quality
    checks fail. Contains error details and failure classification to guide
    the improvement process.
    """
    original_plan: RetrievalPlan
    error_details: Dict[str, Any]
    retry_count: int
    failure_type: str  # "validation", "execution", "data_quality"
    query: str
    analysis: Any
    format_info: Any


class QueryImprovedEvent(Event):
    """
    Event when query has been improved.
    
    Triggered after the query improver generates a better version of the
    failed query. Contains the improved plan and reasoning for the changes.
    """
    improved_plan: RetrievalPlan
    improvement_reasoning: str
    retry_count: int
    query: str
    analysis: Any
    format_info: Any


class ValidationFailedEvent(Event):
    """
    Event when max retries reached or improvement impossible.
    
    Triggered when the retry limit is exceeded or when the query improver
    cannot generate a better version. Terminates the validation loop.
    """
    final_error: str
    retry_history: List[Dict[str, Any]]
    query: str
    analysis: Any
    format_info: Any


class DataQualityFailedEvent(Event):
    """
    Event when data quality validation fails.
    
    Triggered after successful query execution when the retrieved data
    doesn't meet quality criteria. Initiates retry with improved queries.
    """
    retrieved_data: Dict[str, Any]
    quality_issues: List[str]
    original_plan: RetrievalPlan
    retry_count: int
    query: str
    analysis: Any
    format_info: Any


class ValidationSuccessEvent(Event):
    """
    Event when query validation passes.
    
    Triggered when all validation checks pass and the query is ready
    for execution. Contains validation results for logging and monitoring.
    """
    validated_plan: RetrievalPlan
    validation_results: Dict[str, Any]
    query: str
    analysis: Any
    format_info: Any
