"""
Shared test fixtures for LlamaIndex workflow tests.
"""

import pytest
from unittest.mock import MagicMock
from sqlalchemy.orm import Session


@pytest.fixture
def sample_query():
    """Provide a sample query for testing."""
    return "What are the main product gaps for Netflix based on customer reviews?"


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    session = MagicMock(spec=Session)
    
    # Mock execute to return test data
    mock_result = MagicMock()
    mock_result.keys.return_value = ["id", "company", "review_text", "rating"]
    mock_result.__iter__.return_value = [
        (1, "Netflix", "Great streaming service", 5),
        (2, "Netflix", "Needs more content", 3),
        (3, "Netflix", "Too expensive", 2)
    ]
    session.execute.return_value = mock_result
    
    return session


@pytest.fixture
def sample_table_schemas():
    """Provide sample table schemas."""
    return {
        "reviews": {
            "columns": ["id", "company", "review_text", "rating", "created_at"],
            "description": "Customer reviews for various companies"
        },
        "products": {
            "columns": ["id", "name", "company", "category"],
            "description": "Product information"
        }
    }


@pytest.fixture
def sample_query_analysis():
    """Provide sample query analysis result."""
    from app.llamaindex_workflow.agents import QueryAnalysis
    
    return QueryAnalysis(
        needs_data_retrieval=True,
        needs_nlp_analysis=False,
        company="Netflix",
        query_type="data_only",
        reasoning="Query asks for specific company data",
        analysis_type="none"
    )


@pytest.fixture
def sample_format_detection():
    """Provide sample format detection result."""
    from app.llamaindex_workflow.agents import FormatDetection
    
    return FormatDetection(
        format_type="markdown",
        format_details="Structured report with sections and bullet points"
    )
