"""
Data models for SQL query validation and retry system.

These models extend the base workflow models with validation-specific metadata.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from app.optimal_workflow.agents.base import RetrievalPlan, SQLQuery


class EnhancedSQLQuery(SQLQuery):
    """Enhanced SQL query with validation metadata."""
    validation_metadata: Dict[str, Any] = Field(default_factory=dict, description="Validation metadata")
    retry_count: int = Field(default=0, description="Number of retry attempts")
    improvement_history: List[str] = Field(default_factory=list, description="History of improvements")


class EnhancedRetrievalPlan(RetrievalPlan):
    """Enhanced retrieval plan with validation metadata."""
    sql_queries: List[EnhancedSQLQuery] = Field(..., description="List of enhanced SQL queries")
    validation_metadata: Dict[str, Any] = Field(default_factory=dict, description="Plan-level validation metadata")
    retry_count: int = Field(default=0, description="Number of retry attempts for this plan")
    improvement_history: List[str] = Field(default_factory=list, description="History of plan improvements")


class ValidationResult(BaseModel):
    """Result of query validation."""
    is_valid: bool = Field(..., description="Whether the query passed validation")
    syntax_errors: List[str] = Field(default_factory=list, description="SQL syntax errors found")
    schema_errors: List[str] = Field(default_factory=list, description="Database schema errors found")
    performance_warnings: List[str] = Field(default_factory=list, description="Performance warnings")
    suggestions: List[str] = Field(default_factory=list, description="Improvement suggestions")
    validation_timestamp: Optional[str] = Field(None, description="When validation was performed")


class SchemaValidationResult(BaseModel):
    """Result of schema-specific validation."""
    is_valid: bool = Field(..., description="Whether schema validation passed")
    missing_tables: List[str] = Field(default_factory=list, description="Tables that don't exist")
    missing_columns: List[str] = Field(default_factory=list, description="Columns that don't exist")
    invalid_joins: List[str] = Field(default_factory=list, description="Invalid join conditions")
    suggestions: List[str] = Field(default_factory=list, description="Schema correction suggestions")


class DataQualityResult(BaseModel):
    """Result of data quality validation."""
    is_valid: bool = Field(..., description="Whether data quality validation passed")
    completeness_score: float = Field(..., description="Data completeness score (0.0 to 1.0)")
    type_compliance: bool = Field(..., description="Whether data types match expectations")
    quality_issues: List[str] = Field(default_factory=list, description="Specific quality issues found")
    suggestions: List[str] = Field(default_factory=list, description="Quality improvement suggestions")
    row_count: int = Field(default=0, description="Number of rows in result")
    empty_columns: List[str] = Field(default_factory=list, description="Columns with all null/empty values")


class RetryMetadata(BaseModel):
    """Metadata for retry attempts."""
    attempt_number: int = Field(..., description="Current attempt number")
    max_attempts: int = Field(default=3, description="Maximum allowed attempts")
    failure_type: str = Field(..., description="Type of failure that triggered retry")
    error_message: str = Field(..., description="Error message from failed attempt")
    improvement_strategy: Optional[str] = Field(None, description="Strategy used for improvement")
    timestamp: Optional[str] = Field(None, description="When this retry was attempted")


class ValidationConfig(BaseModel):
    """Configuration for validation system."""
    max_retries: int = Field(default=3, description="Maximum number of retry attempts")
    enable_syntax_validation: bool = Field(default=True, description="Enable SQL syntax validation")
    enable_schema_validation: bool = Field(default=True, description="Enable database schema validation")
    enable_performance_checks: bool = Field(default=True, description="Enable performance risk checks")
    enable_data_quality_checks: bool = Field(default=True, description="Enable data quality validation")
    retry_delay_seconds: float = Field(default=1.0, description="Delay between retry attempts")
    performance_timeout_seconds: int = Field(default=30, description="Timeout for performance checks")


class QualityThresholds(BaseModel):
    """Thresholds for data quality validation."""
    min_result_rows: int = Field(default=1, description="Minimum expected rows in result")
    max_result_rows: int = Field(default=10000, description="Maximum allowed rows in result")
    required_completeness_score: float = Field(default=0.8, description="Minimum completeness score required")
    allow_empty_results: bool = Field(default=False, description="Whether to allow empty results")
    max_null_percentage: float = Field(default=0.5, description="Maximum percentage of null values allowed")