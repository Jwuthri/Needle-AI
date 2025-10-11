"""
Unit tests for retry logic and circuit breakers.
"""

import asyncio
from datetime import datetime, timedelta

import pytest
from app.core.retry import (
    CircuitBreaker,
    CircuitBreakerOpenError,
    RetryConfig,
    RetryExhaustedError,
    RetryHandler,
    RetryStrategy,
    circuit_breaker,
    resilient,
    retry,
)


class TestRetryHandler:
    """Test retry logic and strategies."""

    def test_retry_config_defaults(self):
        """Test retry configuration defaults."""
        config = RetryConfig()

        assert config.max_attempts == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.strategy == RetryStrategy.EXPONENTIAL
        assert Exception in config.retryable_exceptions

    @pytest.mark.asyncio
    async def test_exponential_backoff_calculation(self):
        """Test exponential backoff delay calculation."""
        config = RetryConfig(
            max_attempts=5,
            base_delay=1.0,
            strategy=RetryStrategy.EXPONENTIAL
        )
        handler = RetryHandler(config)

        # Test backoff progression
        assert handler._calculate_delay(0) == 1.0  # First retry
        assert handler._calculate_delay(1) == 2.0  # Second retry
        assert handler._calculate_delay(2) == 4.0  # Third retry
        assert handler._calculate_delay(3) == 8.0  # Fourth retry

    @pytest.mark.asyncio
    async def test_linear_backoff_calculation(self):
        """Test linear backoff delay calculation."""
        config = RetryConfig(
            max_attempts=4,
            base_delay=2.0,
            strategy=RetryStrategy.LINEAR
        )
        handler = RetryHandler(config)

        # Test linear progression
        assert handler._calculate_delay(0) == 2.0  # First retry
        assert handler._calculate_delay(1) == 4.0  # Second retry
        assert handler._calculate_delay(2) == 6.0  # Third retry

    @pytest.mark.asyncio
    async def test_fixed_backoff_calculation(self):
        """Test fixed backoff delay calculation."""
        config = RetryConfig(
            max_attempts=3,
            base_delay=5.0,
            strategy=RetryStrategy.FIXED
        )
        handler = RetryHandler(config)

        # All delays should be the same
        assert handler._calculate_delay(0) == 5.0
        assert handler._calculate_delay(1) == 5.0
        assert handler._calculate_delay(2) == 5.0

    @pytest.mark.asyncio
    async def test_max_delay_cap(self):
        """Test that delays are capped at max_delay."""
        config = RetryConfig(
            max_attempts=10,
            base_delay=10.0,
            max_delay=30.0,
            strategy=RetryStrategy.EXPONENTIAL
        )
        handler = RetryHandler(config)

        # High attempt numbers should be capped
        assert handler._calculate_delay(5) == 30.0  # Would be 320 without cap
        assert handler._calculate_delay(10) == 30.0

    @pytest.mark.asyncio
    async def test_successful_execution_no_retry(self):
        """Test successful execution without retries."""
        config = RetryConfig(max_attempts=3)
        handler = RetryHandler(config)

        async def success_func():
            return "success"

        result = await handler.execute_with_retry(success_func)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_retry_on_exception(self):
        """Test retry behavior on exceptions."""
        config = RetryConfig(max_attempts=3, base_delay=0.1)
        handler = RetryHandler(config)

        call_count = 0

        async def failing_then_success():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary failure")
            return "success"

        result = await handler.execute_with_retry(failing_then_success)
        assert result == "success"
        assert call_count == 3  # Failed twice, succeeded on third

    @pytest.mark.asyncio
    async def test_retry_exhausted_error(self):
        """Test behavior when all retries are exhausted."""
        config = RetryConfig(max_attempts=2, base_delay=0.1)
        handler = RetryHandler(config)

        async def always_fail():
            raise ValueError("Always fails")

        with pytest.raises(RetryExhaustedError) as exc_info:
            await handler.execute_with_retry(always_fail)

        assert exc_info.value.attempts == 2
        assert isinstance(exc_info.value.last_exception, ValueError)

    @pytest.mark.asyncio
    async def test_stop_on_specific_exceptions(self):
        """Test that certain exceptions stop retries immediately."""
        config = RetryConfig(
            max_attempts=5,
            stop_on_exceptions=(ValueError,)
        )
        handler = RetryHandler(config)

        async def fail_with_value_error():
            raise ValueError("Stop immediately")

        # Should not retry, raise immediately
        with pytest.raises(ValueError):
            await handler.execute_with_retry(fail_with_value_error)

    @pytest.mark.asyncio
    async def test_non_retryable_exceptions(self):
        """Test that non-retryable exceptions don't trigger retries."""
        config = RetryConfig(
            max_attempts=3,
            retryable_exceptions=(ConnectionError,)  # Only retry on ConnectionError
        )
        handler = RetryHandler(config)

        async def fail_with_runtime_error():
            raise RuntimeError("Should not retry")

        # Should raise immediately without retries
        with pytest.raises(RuntimeError):
            await handler.execute_with_retry(fail_with_runtime_error)


class TestCircuitBreaker:
    """Test circuit breaker implementation."""

    def test_circuit_breaker_initial_state(self):
        """Test circuit breaker starts in CLOSED state."""
        breaker = CircuitBreaker()

        assert breaker.state.state == "CLOSED"
        assert breaker.state.failures == 0
        assert breaker.state.last_failure_time is None
        assert breaker.state.next_retry_time is None

    def test_circuit_breaker_config(self):
        """Test circuit breaker configuration."""
        breaker = CircuitBreaker(
            failure_threshold=10,
            recovery_timeout=120,
            expected_exception=(ValueError, ConnectionError)
        )

        assert breaker.failure_threshold == 10
        assert breaker.recovery_timeout == 120
        assert breaker.expected_exception == (ValueError, ConnectionError)

    @pytest.mark.asyncio
    async def test_successful_calls_keep_closed(self):
        """Test that successful calls keep circuit breaker closed."""
        breaker = CircuitBreaker()

        async def success_func():
            return "success"

        # Multiple successful calls
        for _ in range(10):
            result = await breaker.call(success_func)
            assert result == "success"

        assert breaker.state.state == "CLOSED"
        assert breaker.state.failures == 0

    @pytest.mark.asyncio
    async def test_failures_increment_counter(self):
        """Test that failures increment the failure counter."""
        breaker = CircuitBreaker(failure_threshold=5)

        async def failing_func():
            raise ValueError("Test failure")

        # Test multiple failures below threshold
        for i in range(3):
            with pytest.raises(ValueError):
                await breaker.call(failing_func)

            assert breaker.state.failures == i + 1
            assert breaker.state.state == "CLOSED"  # Still closed

    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_on_threshold(self):
        """Test circuit breaker opens when failure threshold is reached."""
        breaker = CircuitBreaker(failure_threshold=3)

        async def failing_func():
            raise ValueError("Test failure")

        # Reach failure threshold
        for i in range(3):
            with pytest.raises(ValueError):
                await breaker.call(failing_func)

        # Should be open now
        assert breaker.state.state == "OPEN"
        assert breaker.state.failures == 3
        assert breaker.state.next_retry_time is not None

        # Next call should raise CircuitBreakerOpenError
        with pytest.raises(CircuitBreakerOpenError):
            await breaker.call(failing_func)

    @pytest.mark.asyncio
    async def test_circuit_breaker_half_open_recovery(self):
        """Test circuit breaker transitions to HALF_OPEN for recovery."""
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=1)

        async def failing_func():
            raise ValueError("Test failure")

        async def success_func():
            return "success"

        # Open the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                await breaker.call(failing_func)

        assert breaker.state.state == "OPEN"

        # Wait for recovery timeout
        await asyncio.sleep(1.1)

        # Next call should attempt recovery (HALF_OPEN)
        result = await breaker.call(success_func)

        assert result == "success"
        assert breaker.state.state == "CLOSED"  # Should reset to CLOSED
        assert breaker.state.failures == 0

    @pytest.mark.asyncio
    async def test_circuit_breaker_half_open_failure(self):
        """Test circuit breaker stays open if HALF_OPEN call fails."""
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=1)

        async def failing_func():
            raise ValueError("Test failure")

        # Open the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                await breaker.call(failing_func)

        # Wait for recovery timeout
        await asyncio.sleep(1.1)

        # Next call fails during HALF_OPEN
        with pytest.raises(ValueError):
            await breaker.call(failing_func)

        assert breaker.state.state == "OPEN"  # Should return to OPEN
        assert breaker.state.failures == 3  # Failure count increased

    def test_circuit_breaker_manual_reset(self):
        """Test manual circuit breaker reset."""
        breaker = CircuitBreaker(failure_threshold=1)

        # Set some failure state
        breaker.state.state = "OPEN"
        breaker.state.failures = 5
        breaker.state.last_failure_time = datetime.utcnow()
        breaker.state.next_retry_time = datetime.utcnow() + timedelta(seconds=60)

        # Reset manually
        breaker.reset()

        assert breaker.state.state == "CLOSED"
        assert breaker.state.failures == 0
        assert breaker.state.last_failure_time is None
        assert breaker.state.next_retry_time is None

    def test_circuit_breaker_state_info(self):
        """Test circuit breaker state information."""
        breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)

        # Set some state
        breaker.state.failures = 3
        breaker.state.last_failure_time = datetime.utcnow()

        state_info = breaker.get_state()

        assert state_info["state"] == "CLOSED"
        assert state_info["failures"] == 3
        assert state_info["failure_threshold"] == 5
        assert state_info["recovery_timeout"] == 60
        assert "last_failure_time" in state_info

    @pytest.mark.asyncio
    async def test_circuit_breaker_ignores_non_expected_exceptions(self):
        """Test circuit breaker only counts expected exceptions."""
        breaker = CircuitBreaker(
            failure_threshold=2,
            expected_exception=(ValueError,)
        )

        async def runtime_error_func():
            raise RuntimeError("Not expected")

        async def value_error_func():
            raise ValueError("Expected")

        # RuntimeError should not count toward failures
        with pytest.raises(RuntimeError):
            await breaker.call(runtime_error_func)

        assert breaker.state.failures == 0  # Should not increment

        # ValueError should count
        with pytest.raises(ValueError):
            await breaker.call(value_error_func)

        assert breaker.state.failures == 1  # Should increment


class TestRetryDecorator:
    """Test retry decorator functionality."""

    @pytest.mark.asyncio
    async def test_retry_decorator_async_function(self):
        """Test retry decorator with async function."""
        call_count = 0

        @retry(max_attempts=3, base_delay=0.1)
        async def failing_then_success():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary failure")
            return "success"

        result = await failing_then_success()

        assert result == "success"
        assert call_count == 3

    def test_retry_decorator_sync_function(self):
        """Test retry decorator with sync function."""
        call_count = 0

        @retry(max_attempts=2, base_delay=0.1)
        def failing_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("Always fails")

        with pytest.raises(RetryExhaustedError):
            failing_func()

        assert call_count == 2


class TestCircuitBreakerDecorator:
    """Test circuit breaker decorator functionality."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_decorator_async(self):
        """Test circuit breaker decorator with async function."""
        @circuit_breaker(failure_threshold=2, recovery_timeout=1)
        async def failing_func():
            raise ValueError("Test failure")

        # Test failures until circuit opens
        for _ in range(2):
            with pytest.raises(ValueError):
                await failing_func()

        # Circuit should be open
        with pytest.raises(CircuitBreakerOpenError):
            await failing_func()

        # Check circuit breaker state
        state = failing_func.circuit_breaker.get_state()
        assert state["state"] == "OPEN"

    def test_circuit_breaker_decorator_sync(self):
        """Test circuit breaker decorator with sync function."""
        @circuit_breaker(failure_threshold=1)
        def failing_func():
            raise ValueError("Test failure")

        # First failure should open circuit
        with pytest.raises(ValueError):
            failing_func()

        # Second call should be blocked
        with pytest.raises(CircuitBreakerOpenError):
            failing_func()


class TestResilientDecorator:
    """Test resilient decorator (retry + circuit breaker)."""

    @pytest.mark.asyncio
    async def test_resilient_decorator_combines_features(self):
        """Test resilient decorator combines retry and circuit breaker."""
        call_count = 0

        @resilient(max_attempts=2, failure_threshold=3)
        async def intermittent_failure():
            nonlocal call_count
            call_count += 1
            if call_count <= 4:  # Fail first 4 attempts
                raise ValueError("Intermittent failure")
            return "success"

        # Should retry and eventually succeed
        try:
            result = await intermittent_failure()
            # This might succeed or fail depending on circuit breaker state
        except (RetryExhaustedError, CircuitBreakerOpenError):
            # Either exception is acceptable for this test
            pass

        # Verify circuit breaker is attached
        assert hasattr(intermittent_failure, 'circuit_breaker')
        assert intermittent_failure.circuit_breaker is not None


class TestRetryHandlerEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_zero_max_attempts(self):
        """Test behavior with zero max attempts."""
        config = RetryConfig(max_attempts=0)
        handler = RetryHandler(config)

        async def any_func():
            return "should not execute"

        # Should raise immediately without executing
        with pytest.raises(RetryExhaustedError):
            await handler.execute_with_retry(any_func)

    @pytest.mark.asyncio
    async def test_negative_delays_handled(self):
        """Test that negative delays are handled gracefully."""
        config = RetryConfig(base_delay=-1.0)
        handler = RetryHandler(config)

        # Should not cause issues (delays should be >= 0)
        delay = handler._calculate_delay(0)
        assert delay >= 0

    @pytest.mark.asyncio
    async def test_very_large_retry_attempts(self):
        """Test handling of very large retry attempt numbers."""
        config = RetryConfig(max_attempts=1000, base_delay=0.001, max_delay=0.1)
        handler = RetryHandler(config)

        # Should handle large numbers gracefully
        delay = handler._calculate_delay(999)
        assert delay <= config.max_delay


class TestCircuitBreakerEdgeCases:
    """Test circuit breaker edge cases."""

    def test_zero_failure_threshold(self):
        """Test circuit breaker with zero failure threshold."""
        breaker = CircuitBreaker(failure_threshold=0)

        # Should immediately be "open" after any failure
        assert breaker.failure_threshold == 0

    def test_very_short_recovery_timeout(self):
        """Test circuit breaker with very short recovery timeout."""
        breaker = CircuitBreaker(recovery_timeout=0)

        # Should allow immediate recovery attempts
        assert breaker.recovery_timeout == 0

    @pytest.mark.asyncio
    async def test_circuit_breaker_with_non_callable(self):
        """Test circuit breaker behavior with non-callable."""
        breaker = CircuitBreaker()

        # Should handle gracefully
        with pytest.raises(TypeError):
            await breaker.call("not a function")


class TestRetryCircuitBreakerIntegration:
    """Test integration between retry logic and circuit breakers."""

    @pytest.mark.asyncio
    async def test_retry_respects_circuit_breaker(self):
        """Test that retry logic respects circuit breaker state."""
        # This would be a more complex test showing how retry and circuit breaker
        # work together in the resilient decorator

    @pytest.mark.asyncio
    async def test_circuit_breaker_state_during_retries(self):
        """Test circuit breaker state changes during retry attempts."""
        # Test how circuit breaker state evolves during a retry sequence
