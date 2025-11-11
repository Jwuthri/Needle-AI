"""
LlamaIndex Workflow Implementation

This package contains a multi-tier workflow system with intelligent routing:
- Simple workflow (gpt-5-nano): For general queries and casual conversation
- Medium workflow (gpt-5-mini): For follow-up questions using conversation history
- Complex workflow (full pipeline): For queries requiring data retrieval and analysis
"""

from .events import (
    QueryAnalysisEvent,
    FormatDetectionEvent,
    RetrievalPlanEvent,
    DataRetrievalEvent,
    NLPAnalysisEvent,
    WriterContextEvent,
    # Enhanced validation events
    QueryValidationEvent,
    QueryFailedEvent,
    QueryImprovedEvent,
    ValidationFailedEvent,
    DataQualityFailedEvent,
    ValidationSuccessEvent,
)

from .validation_models import (
    EnhancedSQLQuery,
    EnhancedRetrievalPlan,
    ValidationResult,
    SchemaValidationResult,
    DataQualityResult,
    RetryMetadata,
    ValidationConfig,
    QualityThresholds,
)

from .query_classifier import QueryComplexity, QueryClassification, classify_query
from .main import run_workflow, run_workflow_streaming

__all__ = [
    # Original events
    "QueryAnalysisEvent",
    "FormatDetectionEvent", 
    "RetrievalPlanEvent",
    "DataRetrievalEvent",
    "NLPAnalysisEvent",
    "WriterContextEvent",
    # Enhanced validation events
    "QueryValidationEvent",
    "QueryFailedEvent",
    "QueryImprovedEvent",
    "ValidationFailedEvent",
    "DataQualityFailedEvent",
    "ValidationSuccessEvent",
    # Validation models
    "EnhancedSQLQuery",
    "EnhancedRetrievalPlan",
    "ValidationResult",
    "SchemaValidationResult",
    "DataQualityResult",
    "RetryMetadata",
    "ValidationConfig",
    "QualityThresholds",
    # Multi-tier workflow components
    "QueryComplexity",
    "QueryClassification",
    "classify_query",
    "run_workflow",
    "run_workflow_streaming",
]
