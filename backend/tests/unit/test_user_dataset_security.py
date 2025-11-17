"""
Unit tests for user dataset SQL security validation.
"""

import pytest
from app.services.user_dataset_service import UserDatasetService
from unittest.mock import MagicMock


class TestUserDatasetSQLValidation:
    """Test SQL validation for user dataset queries."""

    def setup_method(self):
        """Set up test fixtures."""
        self.db = MagicMock()
        self.service = UserDatasetService(self.db)

    def test_valid_user_dataset_query(self):
        """Test that valid user dataset queries pass validation."""
        valid_queries = [
            'SELECT * FROM __user_123_my_data LIMIT 10',
            'SELECT id, name FROM "__user_abc_customer_data" WHERE id > 5',
            'SELECT * FROM __user_test_sales JOIN __user_test_products ON id = product_id',
        ]
        
        for query in valid_queries:
            # Should not raise ValueError
            self.service._validate_sql_query_for_user_datasets(query)

    def test_block_reviews_table(self):
        """Test that queries to 'reviews' table are blocked."""
        invalid_queries = [
            'SELECT * FROM reviews LIMIT 10',
            'SELECT id, content FROM "reviews" WHERE id > 5',
            'SELECT * FROM REVIEWS LIMIT 10',  # Case insensitive
        ]
        
        for query in invalid_queries:
            with pytest.raises(ValueError) as exc_info:
                self.service._validate_sql_query_for_user_datasets(query)
            assert "forbidden pattern 'reviews'" in str(exc_info.value).lower()

    def test_block_system_tables(self):
        """Test that system tables are blocked."""
        invalid_queries = [
            'SELECT * FROM users LIMIT 10',
            'SELECT * FROM chat_messages WHERE user_id = 123',
            'SELECT * FROM llm_calls ORDER BY created_at DESC',
            'SELECT * FROM pg_tables',
            'SELECT * FROM information_schema.tables',
        ]
        
        for query in invalid_queries:
            with pytest.raises(ValueError) as exc_info:
                self.service._validate_sql_query_for_user_datasets(query)
            assert "access denied" in str(exc_info.value).lower() or "forbidden pattern" in str(exc_info.value).lower()

    def test_block_non_user_tables(self):
        """Test that non-user tables (not starting with __user_) are blocked."""
        invalid_queries = [
            'SELECT * FROM my_table LIMIT 10',
            'SELECT * FROM customer_data WHERE id > 5',
            'SELECT * FROM products JOIN orders ON product_id = id',
        ]
        
        for query in invalid_queries:
            with pytest.raises(ValueError) as exc_info:
                self.service._validate_sql_query_for_user_datasets(query)
            assert "can only query user datasets" in str(exc_info.value).lower()

    def test_error_message_helpful(self):
        """Test that error messages guide users to correct behavior."""
        query = 'SELECT * FROM reviews LIMIT 10'
        
        with pytest.raises(ValueError) as exc_info:
            self.service._validate_sql_query_for_user_datasets(query)
        
        error_msg = str(exc_info.value)
        assert "get_user_datasets" in error_msg.lower()
        assert "access denied" in error_msg.lower()

    def test_case_insensitive_validation(self):
        """Test that validation is case insensitive."""
        invalid_queries = [
            'SELECT * FROM REVIEWS LIMIT 10',
            'select * from Reviews limit 10',
            'SeLeCt * FrOm reviews LiMiT 10',
        ]
        
        for query in invalid_queries:
            with pytest.raises(ValueError):
                self.service._validate_sql_query_for_user_datasets(query)

    def test_quoted_table_names(self):
        """Test validation works with quoted table names."""
        # Valid: user dataset with quotes
        valid_query = 'SELECT * FROM "__user_123_my_data" LIMIT 10'
        self.service._validate_sql_query_for_user_datasets(valid_query)
        
        # Invalid: reviews table with quotes
        invalid_query = 'SELECT * FROM "reviews" LIMIT 10'
        with pytest.raises(ValueError):
            self.service._validate_sql_query_for_user_datasets(invalid_query)

    def test_join_queries(self):
        """Test validation works with JOIN queries."""
        # Valid: joining user datasets
        valid_query = '''
            SELECT a.*, b.name 
            FROM __user_123_orders a 
            JOIN __user_123_customers b ON a.customer_id = b.id
        '''
        self.service._validate_sql_query_for_user_datasets(valid_query)
        
        # Invalid: joining with system table
        invalid_query = '''
            SELECT a.*, b.name 
            FROM __user_123_orders a 
            JOIN users b ON a.user_id = b.id
        '''
        with pytest.raises(ValueError):
            self.service._validate_sql_query_for_user_datasets(invalid_query)

