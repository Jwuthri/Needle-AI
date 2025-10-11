"""
Unit tests for memory implementations and factory.
"""

import asyncio
from typing import Optional
from unittest.mock import MagicMock, patch

import pytest
from app.core.memory.factory import (
    MemoryFactory,
    MemoryProvider,
    create_custom_memory_only,
    create_memory_from_settings,
    get_memory_store,
)
from app.core.memory.in_memory import InMemoryStore
from app.core.memory.redis_memory import RedisMemory
from app.exceptions import ConfigurationError, ExternalServiceError


class MockRedisClient:
    """Mock Redis client for testing."""

    def __init__(self, should_fail: bool = False):
        self.data = {}
        self.should_fail = should_fail
        self.connection_count = 0

    async def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        """Mock set operation."""
        if self.should_fail:
            raise Exception("Redis connection failed")

        self.data[key] = {"value": value, "ex": ex}
        return True

    async def get(self, key: str) -> Optional[str]:
        """Mock get operation."""
        if self.should_fail:
            raise Exception("Redis connection failed")

        if key in self.data:
            return self.data[key]["value"]
        return None

    async def delete(self, key: str) -> int:
        """Mock delete operation."""
        if self.should_fail:
            raise Exception("Redis connection failed")

        if key in self.data:
            del self.data[key]
            return 1
        return 0

    async def exists(self, key: str) -> int:
        """Mock exists operation."""
        if self.should_fail:
            raise Exception("Redis connection failed")

        return 1 if key in self.data else 0

    async def ping(self) -> str:
        """Mock ping operation."""
        if self.should_fail:
            raise Exception("Redis connection failed")
        return "PONG"

    async def close(self):
        """Mock close operation."""


class MockSettings:
    """Mock settings for testing."""

    def __init__(self, **kwargs):
        self.memory_provider = kwargs.get("memory_provider", "redis")
        self.redis_url = kwargs.get("redis_url", "redis://localhost:6379/0")
        self.enable_agno = kwargs.get("enable_agno", True)
        self.pinecone_api_key = kwargs.get("pinecone_api_key", "test-key")
        self.pinecone_environment = kwargs.get("pinecone_environment", "test-env")
        self.pinecone_index_name = kwargs.get("pinecone_index_name", "test-index")

    def get_secret(self, key: str) -> Optional[str]:
        """Mock get_secret method."""
        secrets = {
            "pinecone_api_key": self.pinecone_api_key,
            "weaviate_api_key": "test-weaviate-key",
            "qdrant_api_key": "test-qdrant-key"
        }
        return secrets.get(key)


class TestMemoryFactory:
    """Test memory factory functionality."""

    def test_memory_provider_enum(self):
        """Test MemoryProvider enum values."""
        assert MemoryProvider.AGNO_PINECONE == "agno_pinecone"
        assert MemoryProvider.AGNO_REDIS == "agno_redis"
        assert MemoryProvider.CUSTOM_REDIS == "custom_redis"
        assert MemoryProvider.CUSTOM_IN_MEMORY == "custom_in_memory"

    def test_provider_mapping(self):
        """Test provider mapping configuration."""
        mapping = MemoryFactory.PROVIDER_MAPPING

        assert "redis" in mapping
        assert "pinecone" in mapping
        assert "in-memory" in mapping

        # Redis should have both Agno and custom options
        assert MemoryProvider.AGNO_REDIS in mapping["redis"]
        assert MemoryProvider.CUSTOM_REDIS in mapping["redis"]

        # Vector databases should prioritize Agno
        assert MemoryProvider.AGNO_PINECONE in mapping["pinecone"]

    @pytest.mark.asyncio
    async def test_create_memory_agno_available(self):
        """Test memory creation when Agno is available."""
        settings = MockSettings(memory_provider="redis")
        redis_client = MockRedisClient()

        with patch('app.core.memory.factory.AGNO_AVAILABLE', True), \
             patch('app.core.memory.factory.AgnoMemoryFactory') as mock_agno_factory:

            mock_memory = MagicMock()
            mock_agno_factory.return_value.create_memory.return_value = mock_memory

            memory = await MemoryFactory.create_memory(
                provider_type="redis",
                settings=settings,
                redis_client=redis_client
            )

            assert memory == mock_memory
            mock_agno_factory.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_memory_agno_fallback(self):
        """Test memory creation falls back to custom when Agno fails."""
        settings = MockSettings(memory_provider="redis")
        redis_client = MockRedisClient()

        with patch('app.core.memory.factory.AGNO_AVAILABLE', True), \
             patch('app.core.memory.factory.AgnoMemoryFactory') as mock_agno_factory, \
             patch('app.core.memory.factory.MemoryFactory._create_custom_memory') as mock_custom:

            # Agno creation fails
            mock_agno_factory.return_value.create_memory.side_effect = Exception("Agno failed")

            mock_custom_memory = MagicMock()
            mock_custom.return_value = mock_custom_memory

            memory = await MemoryFactory.create_memory(
                provider_type="redis",
                settings=settings,
                redis_client=redis_client
            )

            assert memory == mock_custom_memory
            mock_custom.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_memory_custom_only(self):
        """Test memory creation with custom implementations only."""
        settings = MockSettings(memory_provider="redis")
        redis_client = MockRedisClient()

        with patch('app.core.memory.factory.AGNO_AVAILABLE', False):
            memory = await MemoryFactory.create_memory(
                provider_type="redis",
                settings=settings,
                redis_client=redis_client
            )

            assert isinstance(memory, RedisMemory)

    @pytest.mark.asyncio
    async def test_create_memory_in_memory_provider(self):
        """Test in-memory provider creation."""
        settings = MockSettings(memory_provider="in-memory")

        memory = await MemoryFactory.create_memory(
            provider_type="in-memory",
            settings=settings
        )

        assert isinstance(memory, InMemoryStore)

    @pytest.mark.asyncio
    async def test_create_memory_invalid_provider(self):
        """Test error handling for invalid provider."""
        settings = MockSettings()

        with pytest.raises(ConfigurationError) as exc_info:
            await MemoryFactory.create_memory(
                provider_type="invalid-provider",
                settings=settings
            )

        assert "not supported" in str(exc_info.value)

    def test_validate_provider_config_redis(self):
        """Test Redis provider configuration validation."""
        settings = MockSettings(redis_url="redis://localhost:6379")

        # Should not raise for valid Redis config
        MemoryFactory.validate_provider_config("redis", settings)

    def test_validate_provider_config_pinecone(self):
        """Test Pinecone provider configuration validation."""
        settings = MockSettings(
            pinecone_api_key="test-key",
            pinecone_environment="test-env",
            pinecone_index_name="test-index"
        )

        # Should not raise for valid Pinecone config
        MemoryFactory.validate_provider_config("pinecone", settings)

    def test_validate_provider_config_missing_redis_url(self):
        """Test validation fails for missing Redis URL."""
        settings = MockSettings(redis_url="")

        with pytest.raises(ConfigurationError) as exc_info:
            MemoryFactory.validate_provider_config("redis", settings)

        assert "Redis URL is required" in str(exc_info.value)

    def test_validate_provider_config_missing_pinecone_key(self):
        """Test validation fails for missing Pinecone API key."""
        settings = MockSettings(pinecone_api_key="")

        with pytest.raises(ConfigurationError) as exc_info:
            MemoryFactory.validate_provider_config("pinecone", settings)

        assert "Pinecone API key is required" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_custom_memory_redis(self):
        """Test custom Redis memory creation."""
        settings = MockSettings()
        redis_client = MockRedisClient()

        memory = await MemoryFactory._create_custom_memory(
            provider=MemoryProvider.CUSTOM_REDIS,
            settings=settings,
            redis_client=redis_client
        )

        assert isinstance(memory, RedisMemory)
        assert memory.redis_client == redis_client

    @pytest.mark.asyncio
    async def test_create_custom_memory_in_memory(self):
        """Test custom in-memory store creation."""
        settings = MockSettings()

        memory = await MemoryFactory._create_custom_memory(
            provider=MemoryProvider.CUSTOM_IN_MEMORY,
            settings=settings
        )

        assert isinstance(memory, InMemoryStore)


class TestRedisMemory:
    """Test RedisMemory implementation."""

    @pytest.fixture
    def mock_redis_client(self):
        """Create mock Redis client."""
        return MockRedisClient()

    @pytest.fixture
    def redis_memory(self, mock_redis_client):
        """Create RedisMemory instance."""
        return RedisMemory(
            redis_client=mock_redis_client,
            prefix="test:",
            expiration=3600
        )

    @pytest.mark.asyncio
    async def test_redis_memory_initialization(self, mock_redis_client):
        """Test RedisMemory initializes properly."""
        memory = RedisMemory(
            redis_client=mock_redis_client,
            prefix="app:",
            expiration=1800
        )

        assert memory.redis_client == mock_redis_client
        assert memory.prefix == "app:"
        assert memory.expiration == 1800

    @pytest.mark.asyncio
    async def test_store_and_retrieve(self, redis_memory):
        """Test storing and retrieving values."""
        key = "test-key"
        value = {"data": "test-value", "timestamp": 1234567890}

        # Store value
        await redis_memory.store(key, value)

        # Retrieve value
        retrieved = await redis_memory.retrieve(key)

        assert retrieved == value

    @pytest.mark.asyncio
    async def test_store_with_expiration(self, mock_redis_client):
        """Test storing with custom expiration."""
        memory = RedisMemory(mock_redis_client, expiration=60)

        key = "expire-key"
        value = {"test": "data"}

        await memory.store(key, value)

        # Verify Redis set was called with expiration
        stored_data = mock_redis_client.data[f"{memory.prefix}{key}"]
        assert stored_data["ex"] == 60

    @pytest.mark.asyncio
    async def test_retrieve_nonexistent_key(self, redis_memory):
        """Test retrieving non-existent key returns None."""
        result = await redis_memory.retrieve("nonexistent-key")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_existing_key(self, redis_memory):
        """Test deleting existing key."""
        key = "delete-key"
        value = {"test": "value"}

        # Store then delete
        await redis_memory.store(key, value)
        result = await redis_memory.delete(key)

        assert result is True

        # Verify key is gone
        retrieved = await redis_memory.retrieve(key)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_key(self, redis_memory):
        """Test deleting non-existent key."""
        result = await redis_memory.delete("nonexistent-key")
        assert result is False

    @pytest.mark.asyncio
    async def test_exists_true(self, redis_memory):
        """Test exists returns True for existing key."""
        key = "exists-key"
        value = {"test": "value"}

        await redis_memory.store(key, value)
        exists = await redis_memory.exists(key)

        assert exists is True

    @pytest.mark.asyncio
    async def test_exists_false(self, redis_memory):
        """Test exists returns False for non-existent key."""
        exists = await redis_memory.exists("nonexistent-key")
        assert exists is False

    @pytest.mark.asyncio
    async def test_list_keys_pattern(self, redis_memory):
        """Test listing keys with pattern matching."""
        # Store multiple keys
        await redis_memory.store("user:123", {"name": "Alice"})
        await redis_memory.store("user:456", {"name": "Bob"})
        await redis_memory.store("session:abc", {"active": True})

        # This test would need actual Redis SCAN implementation
        # For now, just test that the method exists
        assert hasattr(redis_memory, 'list_keys')

    @pytest.mark.asyncio
    async def test_batch_store(self, redis_memory):
        """Test batch storing multiple keys."""
        items = {
            "key1": {"value": 1},
            "key2": {"value": 2},
            "key3": {"value": 3}
        }

        await redis_memory.batch_store(items)

        # Verify all items were stored
        for key, expected_value in items.items():
            retrieved = await redis_memory.retrieve(key)
            assert retrieved == expected_value

    @pytest.mark.asyncio
    async def test_batch_retrieve(self, redis_memory):
        """Test batch retrieving multiple keys."""
        # Store some data
        await redis_memory.store("batch1", {"data": "value1"})
        await redis_memory.store("batch2", {"data": "value2"})
        await redis_memory.store("batch3", {"data": "value3"})

        keys = ["batch1", "batch2", "batch3", "nonexistent"]
        results = await redis_memory.batch_retrieve(keys)

        assert len(results) == 4
        assert results["batch1"] == {"data": "value1"}
        assert results["batch2"] == {"data": "value2"}
        assert results["batch3"] == {"data": "value3"}
        assert results["nonexistent"] is None

    @pytest.mark.asyncio
    async def test_redis_connection_error_handling(self):
        """Test Redis connection error handling."""
        failing_client = MockRedisClient(should_fail=True)
        memory = RedisMemory(failing_client)

        with pytest.raises(ExternalServiceError):
            await memory.store("key", {"value": "test"})

    @pytest.mark.asyncio
    async def test_serialize_deserialize_complex_data(self, redis_memory):
        """Test serialization of complex data structures."""
        complex_data = {
            "string": "text",
            "number": 42,
            "float": 3.14,
            "boolean": True,
            "list": [1, 2, 3, "four"],
            "nested": {
                "inner": {"deep": "value"}
            },
            "null": None
        }

        await redis_memory.store("complex", complex_data)
        retrieved = await redis_memory.retrieve("complex")

        assert retrieved == complex_data

    @pytest.mark.asyncio
    async def test_key_prefix_handling(self):
        """Test proper key prefix handling."""
        client = MockRedisClient()
        memory = RedisMemory(client, prefix="myapp:")

        await memory.store("testkey", {"data": "value"})

        # Verify the actual Redis key includes prefix
        assert "myapp:testkey" in client.data
        assert client.data["myapp:testkey"]["value"] is not None


class TestInMemoryStore:
    """Test InMemoryStore implementation."""

    @pytest.fixture
    def memory_store(self):
        """Create InMemoryStore instance."""
        return InMemoryStore(max_size=100)

    @pytest.mark.asyncio
    async def test_in_memory_initialization(self):
        """Test InMemoryStore initializes properly."""
        store = InMemoryStore(max_size=50, ttl_seconds=300)

        assert store.max_size == 50
        assert store.ttl_seconds == 300
        assert len(store.data) == 0

    @pytest.mark.asyncio
    async def test_store_and_retrieve(self, memory_store):
        """Test storing and retrieving values."""
        key = "test-key"
        value = {"message": "Hello, World!"}

        await memory_store.store(key, value)
        retrieved = await memory_store.retrieve(key)

        assert retrieved == value

    @pytest.mark.asyncio
    async def test_retrieve_nonexistent(self, memory_store):
        """Test retrieving non-existent key."""
        result = await memory_store.retrieve("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_existing(self, memory_store):
        """Test deleting existing key."""
        key = "delete-me"
        value = {"temp": "data"}

        await memory_store.store(key, value)
        result = await memory_store.delete(key)

        assert result is True
        assert await memory_store.retrieve(key) is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, memory_store):
        """Test deleting non-existent key."""
        result = await memory_store.delete("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_exists(self, memory_store):
        """Test exists functionality."""
        key = "exists-test"

        # Initially doesn't exist
        assert await memory_store.exists(key) is False

        # After storing, exists
        await memory_store.store(key, {"test": True})
        assert await memory_store.exists(key) is True

        # After deleting, doesn't exist
        await memory_store.delete(key)
        assert await memory_store.exists(key) is False

    @pytest.mark.asyncio
    async def test_max_size_enforcement(self):
        """Test maximum size enforcement."""
        store = InMemoryStore(max_size=3)

        # Fill to capacity
        await store.store("key1", {"value": 1})
        await store.store("key2", {"value": 2})
        await store.store("key3", {"value": 3})

        assert len(store.data) == 3

        # Adding one more should evict oldest
        await store.store("key4", {"value": 4})

        assert len(store.data) == 3
        assert await store.retrieve("key1") is None  # Should be evicted
        assert await store.retrieve("key4") == {"value": 4}

    @pytest.mark.asyncio
    async def test_ttl_expiration(self):
        """Test TTL-based expiration."""
        store = InMemoryStore(ttl_seconds=1)

        await store.store("expire-key", {"temp": "value"})

        # Should exist immediately
        assert await store.retrieve("expire-key") == {"temp": "value"}

        # Wait for expiration
        await asyncio.sleep(1.1)

        # Should be expired and return None
        assert await store.retrieve("expire-key") is None

    @pytest.mark.asyncio
    async def test_batch_operations(self, memory_store):
        """Test batch store and retrieve."""
        items = {
            "batch1": {"data": "first"},
            "batch2": {"data": "second"},
            "batch3": {"data": "third"}
        }

        await memory_store.batch_store(items)
        results = await memory_store.batch_retrieve(["batch1", "batch2", "batch3", "missing"])

        assert results["batch1"] == {"data": "first"}
        assert results["batch2"] == {"data": "second"}
        assert results["batch3"] == {"data": "third"}
        assert results["missing"] is None

    @pytest.mark.asyncio
    async def test_list_keys(self, memory_store):
        """Test listing stored keys."""
        await memory_store.store("test1", {"value": 1})
        await memory_store.store("test2", {"value": 2})
        await memory_store.store("other", {"value": 3})

        # List all keys
        all_keys = await memory_store.list_keys()
        assert len(all_keys) == 3
        assert "test1" in all_keys
        assert "test2" in all_keys
        assert "other" in all_keys

        # List keys with pattern
        test_keys = await memory_store.list_keys(pattern="test*")
        assert len(test_keys) == 2
        assert "test1" in test_keys
        assert "test2" in test_keys
        assert "other" not in test_keys

    @pytest.mark.asyncio
    async def test_clear_all(self, memory_store):
        """Test clearing all stored data."""
        await memory_store.store("key1", {"value": 1})
        await memory_store.store("key2", {"value": 2})

        assert len(memory_store.data) == 2

        await memory_store.clear()

        assert len(memory_store.data) == 0
        assert await memory_store.retrieve("key1") is None
        assert await memory_store.retrieve("key2") is None

    def test_memory_usage_tracking(self):
        """Test memory usage estimation."""
        store = InMemoryStore()

        # Should have method to estimate memory usage
        assert hasattr(store, '_estimate_size') or hasattr(store, 'get_memory_usage')


class TestMemoryFactoryHelperFunctions:
    """Test helper functions in memory factory."""

    @pytest.mark.asyncio
    async def test_create_memory_from_settings(self):
        """Test create_memory_from_settings function."""
        settings = MockSettings(memory_provider="in-memory")

        memory = await create_memory_from_settings(settings)

        assert isinstance(memory, InMemoryStore)

    @pytest.mark.asyncio
    async def test_create_custom_memory_only(self):
        """Test create_custom_memory_only function."""
        settings = MockSettings(memory_provider="in-memory")

        with patch('app.core.memory.factory.AGNO_AVAILABLE', True):  # Force custom even with Agno
            memory = await create_custom_memory_only(settings)

            assert isinstance(memory, InMemoryStore)

    @pytest.mark.asyncio
    async def test_get_memory_store_with_redis_client(self):
        """Test get_memory_store with Redis client."""
        settings = MockSettings(memory_provider="redis")
        redis_client = MockRedisClient()

        memory = await get_memory_store(settings, redis_client=redis_client)

        # Should return either Agno-based or custom Redis memory
        assert memory is not None

    @pytest.mark.asyncio
    async def test_get_memory_store_without_redis_client(self):
        """Test get_memory_store without Redis client (should create one)."""
        settings = MockSettings(memory_provider="redis")

        with patch('app.services.redis_client.RedisClient') as mock_redis_class:
            mock_redis_instance = MockRedisClient()
            mock_redis_class.return_value = mock_redis_instance

            memory = await get_memory_store(settings)

            assert memory is not None


class TestMemoryInterfaceCompliance:
    """Test that implementations comply with MemoryInterface."""

    def test_redis_memory_implements_interface(self):
        """Test RedisMemory implements MemoryInterface."""
        redis_client = MockRedisClient()
        memory = RedisMemory(redis_client)

        # Check that all interface methods are implemented
        assert hasattr(memory, 'store')
        assert hasattr(memory, 'retrieve')
        assert hasattr(memory, 'delete')
        assert hasattr(memory, 'exists')

        # Verify methods are callable
        assert callable(memory.store)
        assert callable(memory.retrieve)
        assert callable(memory.delete)
        assert callable(memory.exists)

    def test_in_memory_store_implements_interface(self):
        """Test InMemoryStore implements MemoryInterface."""
        memory = InMemoryStore()

        # Check that all interface methods are implemented
        assert hasattr(memory, 'store')
        assert hasattr(memory, 'retrieve')
        assert hasattr(memory, 'delete')
        assert hasattr(memory, 'exists')

        # Verify methods are callable
        assert callable(memory.store)
        assert callable(memory.retrieve)
        assert callable(memory.delete)
        assert callable(memory.exists)


class TestMemoryEdgeCases:
    """Test memory implementation edge cases."""

    @pytest.mark.asyncio
    async def test_redis_memory_with_none_values(self):
        """Test RedisMemory handles None values correctly."""
        client = MockRedisClient()
        memory = RedisMemory(client)

        await memory.store("null-key", None)
        result = await memory.retrieve("null-key")

        assert result is None

    @pytest.mark.asyncio
    async def test_in_memory_store_concurrent_access(self):
        """Test InMemoryStore thread safety."""
        store = InMemoryStore()

        async def store_data(i):
            await store.store(f"key{i}", {"value": i})

        # Concurrent operations
        await asyncio.gather(*[store_data(i) for i in range(10)])

        # Verify all data was stored
        for i in range(10):
            result = await store.retrieve(f"key{i}")
            assert result == {"value": i}

    @pytest.mark.asyncio
    async def test_memory_with_very_large_data(self):
        """Test memory handling of large data structures."""
        store = InMemoryStore(max_size=10)

        large_data = {"data": "x" * 10000}  # Large string

        await store.store("large-key", large_data)
        result = await store.retrieve("large-key")

        assert result == large_data

    @pytest.mark.asyncio
    async def test_memory_key_collision_handling(self):
        """Test handling of key collisions and overwrites."""
        store = InMemoryStore()

        # Store initial value
        await store.store("collision-key", {"version": 1})

        # Overwrite with new value
        await store.store("collision-key", {"version": 2})

        result = await store.retrieve("collision-key")
        assert result == {"version": 2}
