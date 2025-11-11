"""
Tests for data retrieval services.
"""

import pytest
from app.workflow.services import DataRetrievalService


def test_format_as_csv():
    """Test CSV formatting."""
    data = [
        {"id": 1, "name": "Test 1"},
        {"id": 2, "name": "Test 2"}
    ]
    
    result = DataRetrievalService._format_as_csv(data)
    
    assert "id,name" in result
    assert "1,Test 1" in result
    assert "2,Test 2" in result


def test_format_as_csv_empty():
    """Test CSV formatting with empty data."""
    result = DataRetrievalService._format_as_csv([])
    assert result == ""


def test_execute_sql_query(mock_db_session):
    """Test SQL query execution."""
    service = DataRetrievalService(mock_db_session)
    
    results = service.execute_sql_query("SELECT * FROM reviews")
    
    assert len(results) == 3
    assert results[0]["company"] == "Netflix"
    assert results[0]["rating"] == 5


def test_execute_retrieval_plan(mock_db_session):
    """Test retrieval plan execution."""
    service = DataRetrievalService(mock_db_session)
    
    plan = {
        "sql_queries": [
            {
                "query": "SELECT * FROM reviews WHERE company = 'Netflix'",
                "purpose": "Get Netflix reviews",
                "result_key": "netflix_reviews"
            }
        ],
        "reasoning": "Fetch all Netflix reviews",
        "expected_data_types": ["reviews"]
    }
    
    result = service.execute_retrieval_plan(plan, format="json")
    
    assert result["total_rows"] == 3
    assert "netflix_reviews" in result["data"]
    assert len(result["data"]["netflix_reviews"]) == 3
    assert result["format"] == "json"


def test_execute_retrieval_plan_csv_format(mock_db_session):
    """Test retrieval plan with CSV format."""
    service = DataRetrievalService(mock_db_session)
    
    plan = {
        "sql_queries": [
            {
                "query": "SELECT * FROM reviews",
                "purpose": "Get reviews",
                "result_key": "reviews"
            }
        ],
        "reasoning": "Test",
        "expected_data_types": ["reviews"]
    }
    
    result = service.execute_retrieval_plan(plan, format="csv")
    
    assert result["format"] == "csv"
    assert isinstance(result["data"]["reviews"], str)
    assert "id,company,review_text,rating" in result["data"]["reviews"]


def test_execute_retrieval_plan_error_handling(mock_db_session):
    """Test error handling in retrieval plan."""
    # Make execute raise an error
    mock_db_session.execute.side_effect = Exception("Database error")
    
    service = DataRetrievalService(mock_db_session)
    
    plan = {
        "sql_queries": [
            {
                "query": "INVALID SQL",
                "purpose": "Test error",
                "result_key": "test"
            }
        ],
        "reasoning": "Test error handling",
        "expected_data_types": []
    }
    
    result = service.execute_retrieval_plan(plan)
    
    # Should handle error gracefully
    assert "test_error" in result["data"]
    assert "Database error" in result["data"]["test_error"]
