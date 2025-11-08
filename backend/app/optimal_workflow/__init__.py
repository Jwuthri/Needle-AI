"""
LlamaIndex Workflow Implementation

This package contains a reimplementation of the product gap workflow using LlamaIndex.
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
]
