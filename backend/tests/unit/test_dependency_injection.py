"""
Unit tests for Dependency Injection Container.
"""

import asyncio
from typing import Protocol
from unittest.mock import MagicMock

import pytest
from app.core.container import (
    CircularDependencyError,
    DIContainer,
    ServiceDescriptor,
    ServiceLifetime,
    ServiceNotFoundError,
    _configure_services,
    get_container,
)


# Test interfaces and implementations
class ITestService(Protocol):
    """Test service interface."""
    def get_value(self) -> str: ...


class TestService:
    """Simple test service implementation."""

    def __init__(self, value: str = "default"):
        self.value = value
        self.created_at = id(self)  # Unique identifier for instance tracking

    def get_value(self) -> str:
        return self.value


class DependentService:
    """Service that depends on TestService."""

    def __init__(self, test_service: TestService):
        self.test_service = test_service
        self.created_at = id(self)

    def get_dependent_value(self) -> str:
        return f"dependent-{self.test_service.get_value()}"


class AsyncTestService:
    """Async test service."""

    def __init__(self):
        self.created_at = id(self)

    async def get_async_value(self) -> str:
        await asyncio.sleep(0.01)  # Simulate async work
        return "async-value"


async def async_factory() -> TestService:
    """Async factory function."""
    await asyncio.sleep(0.01)  # Simulate async work
    return TestService("factory-created")


def sync_factory() -> TestService:
    """Sync factory function."""
    return TestService("sync-factory")


class TestDIContainer:
    """Test DI container functionality."""

    def test_container_initialization(self):
        """Test container initializes properly."""
        container = DIContainer()

        assert container._services == {}
        assert container._singletons == {}
        assert container._scoped_instances == {}
        assert container._resolution_chain == []

    def test_register_singleton(self):
        """Test singleton service registration."""
        container = DIContainer()

        container.register_singleton(TestService)

        assert TestService in container._services
        descriptor = container._services[TestService]
        assert descriptor.service_type == TestService
        assert descriptor.implementation == TestService
        assert descriptor.lifetime == ServiceLifetime.SINGLETON

    def test_register_scoped(self):
        """Test scoped service registration."""
        container = DIContainer()

        container.register_scoped(TestService)

        descriptor = container._services[TestService]
        assert descriptor.lifetime == ServiceLifetime.SCOPED

    def test_register_transient(self):
        """Test transient service registration."""
        container = DIContainer()

        container.register_transient(TestService)

        descriptor = container._services[TestService]
        assert descriptor.lifetime == ServiceLifetime.TRANSIENT

    def test_register_with_implementation(self):
        """Test registering service with specific implementation."""
        container = DIContainer()

        container.register_singleton(ITestService, TestService)

        descriptor = container._services[ITestService]
        assert descriptor.service_type == ITestService
        assert descriptor.implementation == TestService

    def test_register_with_factory_function(self):
        """Test registering service with factory function."""
        container = DIContainer()

        container.register_singleton(TestService, factory=sync_factory)

        descriptor = container._services[TestService]
        assert descriptor.factory == sync_factory
        assert descriptor.implementation is None

    @pytest.mark.asyncio
    async def test_register_with_async_factory(self):
        """Test registering service with async factory function."""
        container = DIContainer()

        container.register_singleton(TestService, factory=async_factory)

        service = await container.get_service(TestService)
        assert service.get_value() == "factory-created"

    @pytest.mark.asyncio
    async def test_singleton_lifetime(self):
        """Test singleton lifetime - same instance returned."""
        container = DIContainer()
        container.register_singleton(TestService)

        service1 = await container.get_service(TestService)
        service2 = await container.get_service(TestService)

        assert service1 is service2  # Same instance
        assert service1.created_at == service2.created_at

    @pytest.mark.asyncio
    async def test_transient_lifetime(self):
        """Test transient lifetime - new instance each time."""
        container = DIContainer()
        container.register_transient(TestService)

        service1 = await container.get_service(TestService)
        service2 = await container.get_service(TestService)

        assert service1 is not service2  # Different instances
        assert service1.created_at != service2.created_at

    @pytest.mark.asyncio
    async def test_scoped_lifetime_same_scope(self):
        """Test scoped lifetime - same instance within scope."""
        container = DIContainer()
        container.register_scoped(TestService)

        async with container.scope():
            service1 = await container.get_service(TestService)
            service2 = await container.get_service(TestService)

            assert service1 is service2  # Same instance within scope

    @pytest.mark.asyncio
    async def test_scoped_lifetime_different_scopes(self):
        """Test scoped lifetime - different instances across scopes."""
        container = DIContainer()
        container.register_scoped(TestService)

        async with container.scope():
            service1 = await container.get_service(TestService)

        async with container.scope():
            service2 = await container.get_service(TestService)

        assert service1 is not service2  # Different instances across scopes
        assert service1.created_at != service2.created_at

    @pytest.mark.asyncio
    async def test_dependency_injection(self):
        """Test automatic dependency injection."""
        container = DIContainer()

        container.register_singleton(TestService)
        container.register_transient(DependentService)

        dependent = await container.get_service(DependentService)

        assert dependent.get_dependent_value() == "dependent-default"
        assert isinstance(dependent.test_service, TestService)

    @pytest.mark.asyncio
    async def test_service_not_found_error(self):
        """Test error when requesting unregistered service."""
        container = DIContainer()

        with pytest.raises(ServiceNotFoundError) as exc_info:
            await container.get_service(TestService)

        assert "TestService" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_circular_dependency_detection(self):
        """Test circular dependency detection."""
        class ServiceA:
            def __init__(self, service_b): pass

        class ServiceB:
            def __init__(self, service_a): pass

        container = DIContainer()
        container.register_singleton(ServiceA)
        container.register_singleton(ServiceB)

        with pytest.raises(CircularDependencyError):
            await container.get_service(ServiceA)

    def test_get_dependencies_from_constructor(self):
        """Test dependency extraction from constructor."""
        container = DIContainer()

        deps = container._get_dependencies(DependentService)

        assert len(deps) == 1
        assert deps[0] == TestService

    def test_get_dependencies_no_constructor(self):
        """Test dependency extraction with no constructor parameters."""
        container = DIContainer()

        deps = container._get_dependencies(TestService)

        # Should handle optional parameters gracefully
        assert isinstance(deps, list)

    @pytest.mark.asyncio
    async def test_factory_with_dependencies(self):
        """Test factory function that requires dependencies."""
        def dependent_factory(test_service: TestService) -> DependentService:
            return DependentService(test_service)

        container = DIContainer()
        container.register_singleton(TestService)
        container.register_singleton(DependentService, factory=dependent_factory)

        dependent = await container.get_service(DependentService)

        assert dependent.get_dependent_value() == "dependent-default"

    @pytest.mark.asyncio
    async def test_create_instance_with_dependencies(self):
        """Test instance creation with dependency resolution."""
        container = DIContainer()
        container.register_singleton(TestService)

        descriptor = ServiceDescriptor(
            service_type=DependentService,
            implementation=DependentService,
            lifetime=ServiceLifetime.TRANSIENT
        )

        dependent = await container._create_instance(descriptor)

        assert isinstance(dependent, DependentService)
        assert isinstance(dependent.test_service, TestService)

    @pytest.mark.asyncio
    async def test_scoped_cleanup(self):
        """Test that scoped instances are cleaned up."""
        container = DIContainer()
        container.register_scoped(TestService)

        scope_context = container.scope()

        async with scope_context:
            service = await container.get_service(TestService)
            service.created_at

            # Service should be in scoped instances
            assert len(container._scoped_instances) > 0

        # After scope exit, scoped instances should be cleared
        assert len(container._scoped_instances) == 0

    def test_service_descriptor_equality(self):
        """Test ServiceDescriptor equality comparison."""
        desc1 = ServiceDescriptor(
            service_type=TestService,
            implementation=TestService,
            lifetime=ServiceLifetime.SINGLETON
        )

        desc2 = ServiceDescriptor(
            service_type=TestService,
            implementation=TestService,
            lifetime=ServiceLifetime.SINGLETON
        )

        desc3 = ServiceDescriptor(
            service_type=TestService,
            implementation=TestService,
            lifetime=ServiceLifetime.TRANSIENT
        )

        assert desc1.service_type == desc2.service_type
        assert desc1.lifetime != desc3.lifetime

    @pytest.mark.asyncio
    async def test_factory_error_handling(self):
        """Test factory function error handling."""
        def failing_factory() -> TestService:
            raise ValueError("Factory failed")

        container = DIContainer()
        container.register_singleton(TestService, factory=failing_factory)

        with pytest.raises(ValueError):
            await container.get_service(TestService)

    @pytest.mark.asyncio
    async def test_async_service_creation(self):
        """Test creating async services."""
        container = DIContainer()
        container.register_singleton(AsyncTestService)

        service = await container.get_service(AsyncTestService)

        assert isinstance(service, AsyncTestService)
        result = await service.get_async_value()
        assert result == "async-value"


class TestContainerConfiguration:
    """Test container configuration and service registration."""

    def test_get_container_singleton(self):
        """Test that get_container returns singleton instance."""
        container1 = get_container()
        container2 = get_container()

        assert container1 is container2  # Same instance

    def test_configure_services_registration(self):
        """Test that _configure_services registers expected services."""
        container = DIContainer()

        # Mock the services to avoid import issues in tests
        with pytest.mock.patch.multiple(
            'app.core.container',
            RedisClient=MagicMock(),
            KafkaClient=MagicMock(),
            RabbitMQClient=MagicMock(),
            UserRepository=MagicMock(),
            ChatSessionRepository=MagicMock(),
            ConversationService=MagicMock()
        ):
            _configure_services(container)

        # Should have registered some services
        assert len(container._services) > 0

        # Check that ChatService is registered with special key
        assert "ChatService" in container._services

    @pytest.mark.asyncio
    async def test_container_factory_functions(self):
        """Test container factory functions work correctly."""
        container = DIContainer()

        # Mock factory function
        async def mock_factory():
            return TestService("factory-test")

        container._services["TestFactory"] = ServiceDescriptor(
            service_type=object,
            implementation=None,
            lifetime=ServiceLifetime.SINGLETON,
            factory=mock_factory
        )

        # Should be able to get service from factory
        descriptor = container._services["TestFactory"]
        result = await container._get_singleton(descriptor)

        assert result.get_value() == "factory-test"


class TestContainerEdgeCases:
    """Test container edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_register_none_service_type(self):
        """Test registering with None service type."""
        container = DIContainer()

        with pytest.raises((ValueError, TypeError)):
            container.register_singleton(None)

    @pytest.mark.asyncio
    async def test_deep_dependency_chain(self):
        """Test container handles deep dependency chains."""
        class Level1:
            pass

        class Level2:
            def __init__(self, level1: Level1):
                self.level1 = level1

        class Level3:
            def __init__(self, level2: Level2):
                self.level2 = level2

        class Level4:
            def __init__(self, level3: Level3):
                self.level3 = level3

        container = DIContainer()
        container.register_singleton(Level1)
        container.register_singleton(Level2)
        container.register_singleton(Level3)
        container.register_singleton(Level4)

        # Should resolve deep dependency chain
        level4 = await container.get_service(Level4)

        assert isinstance(level4, Level4)
        assert isinstance(level4.level3, Level3)
        assert isinstance(level4.level3.level2, Level2)
        assert isinstance(level4.level3.level2.level1, Level1)

    @pytest.mark.asyncio
    async def test_container_with_primitive_types(self):
        """Test container behavior with primitive types."""
        container = DIContainer()

        # Should not be able to register primitive types
        with pytest.raises((ValueError, TypeError)):
            container.register_singleton(str)

    @pytest.mark.asyncio
    async def test_multiple_scopes_isolation(self):
        """Test that multiple concurrent scopes are isolated."""
        container = DIContainer()
        container.register_scoped(TestService)

        results = []

        async def get_service_in_scope(scope_id):
            async with container.scope():
                service = await container.get_service(TestService)
                results.append((scope_id, service.created_at))

        # Run multiple scopes concurrently
        await asyncio.gather(
            get_service_in_scope(1),
            get_service_in_scope(2),
            get_service_in_scope(3)
        )

        # Should have different instances in each scope
        instance_ids = [result[1] for result in results]
        assert len(set(instance_ids)) == 3  # All different

    def test_service_lifetime_enum(self):
        """Test ServiceLifetime enum values."""
        assert ServiceLifetime.SINGLETON == "singleton"
        assert ServiceLifetime.SCOPED == "scoped"
        assert ServiceLifetime.TRANSIENT == "transient"

    @pytest.mark.asyncio
    async def test_container_reset_state(self):
        """Test container state can be reset."""
        container = DIContainer()
        container.register_singleton(TestService)

        # Get a service to populate singletons
        await container.get_service(TestService)

        assert len(container._singletons) > 0

        # Clear container state (if such method existed)
        container._services.clear()
        container._singletons.clear()

        assert len(container._services) == 0
        assert len(container._singletons) == 0


class TestContainerPerformance:
    """Test container performance characteristics."""

    @pytest.mark.asyncio
    async def test_singleton_performance(self):
        """Test singleton resolution performance."""
        import time

        container = DIContainer()
        container.register_singleton(TestService)

        # First resolution (should be slower - creates instance)
        start = time.time()
        service1 = await container.get_service(TestService)
        first_time = time.time() - start

        # Second resolution (should be faster - returns cached)
        start = time.time()
        service2 = await container.get_service(TestService)
        second_time = time.time() - start

        # Second resolution should be significantly faster
        assert second_time < first_time
        assert service1 is service2

    @pytest.mark.asyncio
    async def test_concurrent_service_resolution(self):
        """Test concurrent service resolution."""
        container = DIContainer()
        container.register_singleton(TestService)

        # Resolve service concurrently
        services = await asyncio.gather(
            container.get_service(TestService),
            container.get_service(TestService),
            container.get_service(TestService)
        )

        # All should be the same instance
        assert all(service is services[0] for service in services)

    @pytest.mark.asyncio
    async def test_large_number_of_services(self):
        """Test container with large number of services."""
        container = DIContainer()

        # Register many services
        for i in range(100):
            service_name = f"TestService{i}"
            service_class = type(service_name, (), {"value": i})
            container.register_singleton(service_class)

        # Should handle large number of services
        assert len(container._services) == 100
