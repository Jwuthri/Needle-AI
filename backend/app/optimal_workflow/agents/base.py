"""
Base models and utilities for LlamaIndex agents.
"""

from typing import Dict, Any
from llama_index.llms.openai import OpenAI
from pydantic import BaseModel, Field

from app.config import SETTINGS


class QueryAnalysis(BaseModel):
    """Query analysis result determining workflow execution path."""
    needs_data_retrieval: bool = Field(..., description="Whether to retrieve review data")
    needs_nlp_analysis: bool = Field(..., description="Whether to perform NLP analysis")
    company: str | None = Field(None, description="Company name if applicable")
    query_type: str = Field(..., description="Single word for type of query: <data_only, analysis, general, etc>")
    reasoning: str = Field(..., description="Brief explanation of routing decision")
    analysis_type: str = Field(..., description="What type of analysis is needed")


class FormatDetection(BaseModel):
    """Output format detection result."""
    format_type: str = Field(..., description="Single word format type: <markdown, json, table, etc>")
    format_details: str = Field(..., description="Specific formatting requirements")


class SQLQuery(BaseModel):
    """SQL query definition."""
    query: str = Field(..., description="The SQL query string")
    purpose: str = Field(..., description="Purpose of this query")
    result_key: str = Field(..., description="Key to store results under")


class RetrievalPlan(BaseModel):
    """Data retrieval plan."""
    sql_queries: list[SQLQuery] = Field(..., description="List of SQL queries to execute")
    reasoning: str = Field(..., description="Explanation of the retrieval strategy")
    expected_data_types: list[str] = Field(..., description="List of expected data types")


def get_llm(model: str = "gpt-5-mini") -> OpenAI:
    """Get configured LLM instance."""
    return OpenAI(
        model=model,
        api_key=SETTINGS.OPENAI_API_KEY,
        temperature=0.1
    )