"""
Base models and utilities for LlamaIndex agents.
"""

from typing import Dict, Any
from llama_index.llms.openai import OpenAI
from pydantic import BaseModel, Field

from app.core.config.settings import get_settings


class QueryAnalysis(BaseModel):
    """Query analysis result determining workflow execution path."""
    needs_data_retrieval: bool = Field(..., description="Whether to retrieve review data")
    needs_nlp_analysis: bool = Field(..., description="Whether to perform NLP analysis")
    company: str | None = Field(None, description="Company name if applicable")
    query_type: str = Field(..., description="Single word for type of query: <data_only, analysis, general, etc>")
    reasoning: str = Field(..., description="Brief explanation of routing decision keep it concise and to the point")
    analysis_type: str = Field(..., description="What type of analysis is needed")


class FormatDetection(BaseModel):
    """Output format detection result."""
    format_type: str = Field(..., description="Single word format type: <markdown, json, table, etc>")
    format_details: str = Field(..., description="Specific formatting requirements, keep it concise and to the point")


class SQLQuery(BaseModel):
    """SQL query definition."""
    query: str = Field(..., description="The SQL query string")
    purpose: str = Field(..., description="Purpose of this query, keep it concise and to the point")
    result_key: str = Field(..., description="Key to store results under")


class RetrievalPlan(BaseModel):
    """Data retrieval plan."""
    sql_queries: list[SQLQuery] = Field(..., description="List of SQL queries to execute")
    reasoning: str = Field(..., description="Explanation of the retrieval strategy, keep it concise and to the point")
    expected_data_types: list[str] = Field(..., description="List of expected data types")


def get_llm(model: str = None) -> OpenAI:
    """
    Get configured LLM instance using OpenAI.
    
    Args:
        model: Optional model name override. If None, uses default from settings.
    
    Returns:
        Configured OpenAI LLM instance
    """
    settings = get_settings()
    
    # Get API key from settings
    api_key = settings.get_secret("openai_api_key")
    if not api_key:
        raise ValueError("OpenAI API key not configured")
    
    # Convert SecretStr to str if needed
    api_key_str = str(api_key) if hasattr(api_key, '__str__') else api_key
    
    # Use provided model or default from settings
    model_name = model or settings.default_model
    
    return OpenAI(
        model=model_name,
        api_key=api_key_str,
        max_tokens=4096,
        temperature=0.1
    )