"""
Unit tests for DataRetrievalAgent.

Tests the data retrieval agent's functionality including dataset fetching,
query execution, semantic search, EDA optimization, and caching.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.core.llm.workflow.agents.data_retrieval import DataRetrievalAgent
from app.models.workflow import ExecutionContext
from app.services.redis_client import RedisClient


@pytest.fixture
def mock_redis_client():
    """Create a mock Redis client."""
    redis = AsyncMock(spec=RedisClient)
    redis.get = AsyncMock(return_value=None)  # Default to cache miss
    redis.set = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=True)
    return redis


@pytest.fixture
def mock_stream_callback():
    """Create a mock stream callback."""
    return AsyncMock()


@pytest.fixture
def data_retrieval_agent(mock_redis_client, mock_stream_callback):
    """Create a DataRetrievalAgent instance with mocked dependencies."""
    return DataRetrievalAgent(
        redis_client=mock_redis_client,
        stream_callback=mock_stream_callback,
        cache_ttl=3600
    )


@pytest.fixture
def execution_context():
    """Create a test execution context."""
    return ExecutionContext(
        user_id="test_user",
        session_id="test_session",
        message_id="test_message",
        query="Test query",
        user_datasets=[
            {
                "dataset_id": "dataset-001",
                "table_name": "test_reviews",
                "row_count": 45,
                "eda": {
                    "column_stats": {
                        "rating": {
                            "distinct_count": 5,
                            "min": 1,
                            "max": 5,
                            "top_values": {"2": 12, "3": 10}
                        },
                        "source": {
                            "distinct_count": 3,
                            "top_values": {"app_store": 18, "reddit": 10}
                        },
                        "date": {
                            "min": "2025-09-01",
                            "max": "2025-10-15"
                        }
                    }
                }
            }
        ]
    )


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return AsyncMock()


class TestDataRetrievalAgent:
    """Test suite for DataRetrievalAgent."""
    
    @pytest.mark.asyncio
    async def test_initialization(self, mock_redis_client, mock_stream_callback):
        """Test agent initialization."""
        agent = DataRetrievalAgent(
            redis_client=mock_redis_client,
            stream_callback=mock_stream_callback,
            cache_ttl=7200
        )
        
        assert agent.redis_client == mock_redis_client
        assert agent.stream_callback == mock_stream_callback
        assert agent.cache_ttl == 7200
    
    @pytest.mark.asyncio
    async def test_get_user_datasets_with_eda_cache_miss(
        self,
        data_retrieval_agent,
        execution_context,
        mock_db,
        mock_redis_client,
        mock_stream_callback
    ):
        """Test getting datasets with EDA metadata (cache miss)."""
        # Ensure cache miss
        mock_redis_client.get.return_value = None
        
        # Mock the tool function
        with patch('app.core.llm.workflow.agents.data_retrieval.get_user_datasets_with_eda') as mock_tool:
            mock_datasets = [
                {
                    "dataset_id": "dataset-001",
                    "table_name": "test_reviews",
                    "row_count": 45
                }
            ]
            mock_tool.return_value = mock_datasets
            
            # Mock ChatMessageStepRepository
            with patch('app.core.llm.workflow.agents.data_retrieval.ChatMessageStepRepository') as mock_repo:
                mock_repo.create = AsyncMock()
                
                # Execute
                result = await data_retrieval_agent.get_user_datasets_with_eda(
                    user_id="test_user",
                    context=execution_context,
                    db=mock_db,
                    step_order=1
                )
                
                # Verify result
                assert result == mock_datasets
                assert len(result) == 1
                
                # Verify tool was called
                mock_tool.assert_called_once_with("test_user")
                
                # Verify cache was set
                mock_redis_client.set.assert_called_once()
                
                # Verify step was saved
                mock_repo.create.assert_called_once()
                
                # Verify events were emitted
                assert mock_stream_callback.call_count >= 2  # start and complete
    
    @pytest.mark.asyncio
    async def test_get_user_datasets_with_eda_cache_hit(
        self,
        data_retrieval_agent,
        execution_context,
        mock_db,
        mock_redis_client,
        mock_stream_callback
    ):
        """Test getting datasets with EDA metadata (cache hit)."""
        # Setup cache hit
        cached_datasets = [
            {
                "dataset_id": "dataset-001",
                "table_name": "cached_reviews",
                "row_count": 45
            }
        ]
        mock_redis_client.get.return_value = cached_datasets
        
        # Mock ChatMessageStepRepository
        with patch('app.core.llm.workflow.agents.data_retrieval.ChatMessageStepRepository') as mock_repo:
            mock_repo.create = AsyncMock()
            
            # Execute
            result = await data_retrieval_agent.get_user_datasets_with_eda(
                user_id="test_user",
                context=execution_context,
                db=mock_db,
                step_order=1
            )
            
            # Verify result came from cache
            assert result == cached_datasets
            
            # Verify cache was checked
            mock_redis_client.get.assert_called_once()
            
            # Verify cache was NOT set (already cached)
            mock_redis_client.set.assert_not_called()
            
            # Verify step was saved with cache_hit=True
            mock_repo.create.assert_called_once()
            call_kwargs = mock_repo.create.call_args[1]
            assert "cache_hit" in str(call_kwargs.get("tool_call", {}))
    
    @pytest.mark.asyncio
    async def test_query_reviews_with_filters(
        self,
        data_retrieval_agent,
        execution_context,
        mock_db,
        mock_redis_client
    ):
        """Test querying reviews with various filters."""
        # Ensure cache miss
        mock_redis_client.get.return_value = None
        
        # Mock the tool function
        with patch('app.core.llm.workflow.agents.data_retrieval.query_reviews') as mock_tool:
            mock_result = {
                "reviews": [
                    {"id": 1, "rating": 2, "text": "Test review"}
                ],
                "total_count": 1,
                "returned_count": 1,
                "query_info": {"execution_time_ms": 45.2}
            }
            mock_tool.return_value = mock_result
            
            # Mock ChatMessageStepRepository
            with patch('app.core.llm.workflow.agents.data_retrieval.ChatMessageStepRepository') as mock_repo:
                mock_repo.create = AsyncMock()
                
                # Execute with filters
                result = await data_retrieval_agent.query_reviews(
                    user_id="test_user",
                    context=execution_context,
                    db=mock_db,
                    step_order=2,
                    rating_filter="<=2",
                    date_range=("2025-09-01", "2025-10-15"),
                    source_filter=["app_store", "reddit"],
                    limit=100
                )
                
                # Verify result
                assert result == mock_result
                assert result["returned_count"] == 1
                
                # Verify tool was called with correct parameters
                mock_tool.assert_called_once()
                call_kwargs = mock_tool.call_args[1]
                assert call_kwargs["rating_filter"] == "<=2"
                assert call_kwargs["date_range"] == ("2025-09-01", "2025-10-15")
                assert call_kwargs["source_filter"] == ["app_store", "reddit"]
                assert call_kwargs["limit"] == 100
    
    @pytest.mark.asyncio
    async def test_semantic_search(
        self,
        data_retrieval_agent,
        execution_context,
        mock_db,
        mock_redis_client
    ):
        """Test semantic search functionality."""
        # Ensure cache miss
        mock_redis_client.get.return_value = None
        
        # Mock the tool function
        with patch('app.core.llm.workflow.agents.data_retrieval.semantic_search_reviews') as mock_tool:
            mock_results = [
                {
                    "id": 1,
                    "text": "UI is slow",
                    "rating": 2,
                    "similarity_score": 0.92
                },
                {
                    "id": 2,
                    "text": "Performance issues",
                    "rating": 1,
                    "similarity_score": 0.85
                }
            ]
            mock_tool.return_value = mock_results
            
            # Mock ChatMessageStepRepository
            with patch('app.core.llm.workflow.agents.data_retrieval.ChatMessageStepRepository') as mock_repo:
                mock_repo.create = AsyncMock()
                
                # Execute semantic search
                result = await data_retrieval_agent.semantic_search(
                    user_id="test_user",
                    query_text="slow performance",
                    context=execution_context,
                    db=mock_db,
                    step_order=3,
                    top_k=10,
                    rating_filter="<=2"
                )
                
                # Verify result
                assert result == mock_results
                assert len(result) == 2
                assert result[0]["similarity_score"] == 0.92
                
                # Verify tool was called with correct parameters
                mock_tool.assert_called_once_with(
                    user_id="test_user",
                    query_text="slow performance",
                    top_k=10,
                    rating_filter="<=2"
                )
    
    @pytest.mark.asyncio
    async def test_eda_optimization(
        self,
        data_retrieval_agent,
        execution_context
    ):
        """Test EDA-based query optimization."""
        # Test optimization logic
        optimizations = await data_retrieval_agent._optimize_query_with_eda(
            user_id="test_user",
            context=execution_context,
            rating_filter="<=2",
            date_range=("2025-09-01", "2025-10-15"),
            source_filter=["app_store"]
        )
        
        # Verify optimizations were applied
        assert "rating_optimization" in optimizations
        assert "date_optimization" in optimizations
        assert "source_optimization" in optimizations
        
        # Verify rating optimization (distinct_count = 5, should use IN clause)
        rating_opt = optimizations["rating_optimization"]
        assert rating_opt is not None
        assert rating_opt["strategy"] == "IN_clause"
        
        # Verify date optimization
        date_opt = optimizations["date_optimization"]
        assert date_opt is not None
        assert date_opt["strategy"] == "indexed_range"
        
        # Verify source optimization (distinct_count = 3, should use IN clause)
        source_opt = optimizations["source_optimization"]
        assert source_opt is not None
        assert source_opt["strategy"] == "IN_clause"
    
    @pytest.mark.asyncio
    async def test_cache_invalidation(
        self,
        data_retrieval_agent,
        mock_redis_client
    ):
        """Test cache invalidation for a user."""
        # Execute cache invalidation
        result = await data_retrieval_agent.invalidate_cache("test_user")
        
        # Verify cache was deleted
        assert result is True
        mock_redis_client.delete.assert_called_once_with("datasets_eda:test_user")
    
    def test_generate_query_cache_key(self, data_retrieval_agent):
        """Test query cache key generation."""
        # Generate cache key
        key1 = data_retrieval_agent._generate_query_cache_key(
            user_id="test_user",
            table_name="reviews",
            rating_filter="<=2",
            date_range=("2025-09-01", "2025-10-15"),
            source_filter=["app_store", "reddit"],
            text_contains="slow",
            limit=100
        )
        
        # Generate same key with different source order
        key2 = data_retrieval_agent._generate_query_cache_key(
            user_id="test_user",
            table_name="reviews",
            rating_filter="<=2",
            date_range=("2025-09-01", "2025-10-15"),
            source_filter=["reddit", "app_store"],  # Different order
            text_contains="slow",
            limit=100
        )
        
        # Keys should be identical (sources are sorted)
        assert key1 == key2
        assert key1.startswith("query_reviews:test_user:")
        
        # Different parameters should generate different keys
        key3 = data_retrieval_agent._generate_query_cache_key(
            user_id="test_user",
            table_name="reviews",
            rating_filter=">=4",  # Different filter
            date_range=("2025-09-01", "2025-10-15"),
            source_filter=["app_store", "reddit"],
            text_contains="slow",
            limit=100
        )
        
        assert key1 != key3
    
    def test_generate_search_cache_key(self, data_retrieval_agent):
        """Test semantic search cache key generation."""
        # Generate cache key
        key1 = data_retrieval_agent._generate_search_cache_key(
            user_id="test_user",
            query_text="slow performance",
            top_k=10,
            rating_filter="<=2"
        )
        
        # Generate same key
        key2 = data_retrieval_agent._generate_search_cache_key(
            user_id="test_user",
            query_text="slow performance",
            top_k=10,
            rating_filter="<=2"
        )
        
        # Keys should be identical
        assert key1 == key2
        assert key1.startswith("semantic_search:test_user:")
        
        # Different query should generate different key
        key3 = data_retrieval_agent._generate_search_cache_key(
            user_id="test_user",
            query_text="great features",  # Different query
            top_k=10,
            rating_filter="<=2"
        )
        
        assert key1 != key3
    
    def test_generate_query_thought(self, data_retrieval_agent):
        """Test query thought generation."""
        result = {
            "returned_count": 5,
            "total_count": 10,
            "query_info": {"execution_time_ms": 45.2}
        }
        
        thought = data_retrieval_agent._generate_query_thought(
            result=result,
            rating_filter="<=2",
            date_range=("2025-09-01", "2025-10-15"),
            source_filter=["app_store"],
            optimized_params={
                "rating_optimization": {"strategy": "IN_clause"},
                "date_optimization": {"strategy": "indexed_range"}
            }
        )
        
        # Verify thought contains key information
        assert "5 reviews" in thought
        assert "10 total" in thought
        assert "rating <=2" in thought
        assert "date range" in thought
        assert "app_store" in thought
        assert "IN_clause" in thought
        assert "45.2ms" in thought
    
    @pytest.mark.asyncio
    async def test_error_handling_in_get_datasets(
        self,
        data_retrieval_agent,
        execution_context,
        mock_db,
        mock_redis_client
    ):
        """Test error handling when getting datasets fails."""
        # Ensure cache miss
        mock_redis_client.get.return_value = None
        
        # Mock the tool function to raise an error
        with patch('app.core.llm.workflow.agents.data_retrieval.get_user_datasets_with_eda') as mock_tool:
            mock_tool.side_effect = Exception("Database connection failed")
            
            # Mock ChatMessageStepRepository
            with patch('app.core.llm.workflow.agents.data_retrieval.ChatMessageStepRepository') as mock_repo:
                mock_repo.create = AsyncMock()
                
                # Execute and expect exception
                with pytest.raises(Exception) as exc_info:
                    await data_retrieval_agent.get_user_datasets_with_eda(
                        user_id="test_user",
                        context=execution_context,
                        db=mock_db,
                        step_order=1
                    )
                
                assert "Database connection failed" in str(exc_info.value)
                
                # Verify error was tracked in Chat Message Steps
                mock_repo.create.assert_called_once()
                call_kwargs = mock_repo.create.call_args[1]
                assert "error" in str(call_kwargs.get("tool_call", {}))
    
    @pytest.mark.asyncio
    async def test_query_reviews_without_eda_optimization(
        self,
        data_retrieval_agent,
        execution_context,
        mock_db,
        mock_redis_client
    ):
        """Test querying reviews without EDA optimization."""
        # Ensure cache miss
        mock_redis_client.get.return_value = None
        
        # Mock the tool function
        with patch('app.core.llm.workflow.agents.data_retrieval.query_reviews') as mock_tool:
            mock_result = {
                "reviews": [],
                "total_count": 0,
                "returned_count": 0,
                "query_info": {"execution_time_ms": 10.0}
            }
            mock_tool.return_value = mock_result
            
            # Mock ChatMessageStepRepository
            with patch('app.core.llm.workflow.agents.data_retrieval.ChatMessageStepRepository') as mock_repo:
                mock_repo.create = AsyncMock()
                
                # Execute without EDA optimization
                result = await data_retrieval_agent.query_reviews(
                    user_id="test_user",
                    context=execution_context,
                    db=mock_db,
                    step_order=2,
                    use_eda_optimization=False
                )
                
                # Verify result
                assert result == mock_result
                
                # Verify step was saved without optimization info
                mock_repo.create.assert_called_once()
                call_kwargs = mock_repo.create.call_args[1]
                tool_call = call_kwargs.get("tool_call", {})
                assert tool_call["parameters"]["eda_optimizations"] == {}
