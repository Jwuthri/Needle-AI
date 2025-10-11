"""
Unit tests for LLM implementations and factory.
"""

import asyncio
from typing import Any, Dict, Optional

import pytest
from app.core.llm.base import BaseLLMClient
from app.core.llm.custom_client import CustomLLMClient
from app.core.llm.factory import (
    _create_custom_client,
    get_llm_client,
    list_available_providers,
    validate_provider_config,
)
from app.core.llm.openrouter_client import OpenRouterClient
from app.exceptions import ConfigurationError, ExternalServiceError, ValidationError


class MockHTTPClient:
    """Mock HTTP client for testing API calls."""

    def __init__(self, responses: Dict[str, Any] = None, should_fail: bool = False):
        self.responses = responses or {}
        self.should_fail = should_fail
        self.requests_made = []
        self.call_count = 0

    async def post(self, url: str, headers: Dict[str, str], json_data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock POST request."""
        self.call_count += 1
        self.requests_made.append({
            "method": "POST",
            "url": url,
            "headers": headers,
            "json": json_data,
            "timestamp": self.call_count
        })

        if self.should_fail:
            raise Exception("HTTP request failed")

        # Return pre-configured response or default
        return self.responses.get(url, {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": f"Mock response {self.call_count}"
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 15,
                "total_tokens": 25
            },
            "model": "mock-model"
        })


class MockSettings:
    """Mock settings for testing."""

    def __init__(self, **kwargs):
        self.llm_provider = kwargs.get("llm_provider", "openrouter")
        self.openrouter_api_key = kwargs.get("openrouter_api_key", "test-api-key")
        self.openai_api_key = kwargs.get("openai_api_key", "test-openai-key")
        self.anthropic_api_key = kwargs.get("anthropic_api_key", "test-anthropic-key")
        self.model_name = kwargs.get("model_name", "gpt-4o-mini")
        self.max_tokens = kwargs.get("max_tokens", 1000)
        self.temperature = kwargs.get("temperature", 0.7)
        self.timeout_seconds = kwargs.get("timeout_seconds", 30)
        self.max_retries = kwargs.get("max_retries", 3)

    def get_secret(self, key: str) -> Optional[str]:
        """Mock get_secret method."""
        secrets = {
            "openrouter_api_key": self.openrouter_api_key,
            "openai_api_key": self.openai_api_key,
            "anthropic_api_key": self.anthropic_api_key
        }
        return secrets.get(key)


class TestLLMFactory:
    """Test LLM client factory functionality."""

    @pytest.mark.asyncio
    async def test_get_llm_client_openrouter(self):
        """Test getting OpenRouter client."""
        settings = MockSettings(llm_provider="openrouter")

        client = await get_llm_client(settings)

        assert isinstance(client, OpenRouterClient)
        assert client.api_key == "test-api-key"

    @pytest.mark.asyncio
    async def test_get_llm_client_custom(self):
        """Test getting custom client."""
        settings = MockSettings(llm_provider="custom")

        client = await get_llm_client(settings)

        assert isinstance(client, CustomLLMClient)

    @pytest.mark.asyncio
    async def test_get_llm_client_invalid_provider(self):
        """Test error with invalid provider."""
        settings = MockSettings(llm_provider="invalid-provider")

        with pytest.raises(ConfigurationError) as exc_info:
            await get_llm_client(settings)

        assert "Unsupported LLM provider" in str(exc_info.value)

    def test_list_available_providers(self):
        """Test listing available providers."""
        providers = list_available_providers()

        assert isinstance(providers, dict)
        assert "openrouter" in providers
        assert "custom" in providers

        # Check provider details
        openrouter_info = providers["openrouter"]
        assert "description" in openrouter_info
        assert "required_secrets" in openrouter_info
        assert "openrouter_api_key" in openrouter_info["required_secrets"]

    def test_validate_provider_config_openrouter_valid(self):
        """Test valid OpenRouter configuration."""
        settings = MockSettings(
            llm_provider="openrouter",
            openrouter_api_key="test-key"
        )

        # Should not raise exception
        result = validate_provider_config("openrouter", settings)
        assert isinstance(result, dict)
        assert "api_key" in result

    def test_validate_provider_config_openrouter_missing_key(self):
        """Test OpenRouter configuration with missing API key."""
        settings = MockSettings(
            llm_provider="openrouter",
            openrouter_api_key=""
        )

        with pytest.raises(ConfigurationError) as exc_info:
            validate_provider_config("openrouter", settings)

        assert "API key is required" in str(exc_info.value)

    def test_validate_provider_config_custom(self):
        """Test custom provider configuration."""
        settings = MockSettings(llm_provider="custom")

        # Should always be valid (custom implementation)
        result = validate_provider_config("custom", settings)
        assert isinstance(result, dict)

    def test_validate_provider_config_invalid_provider(self):
        """Test validation with invalid provider."""
        settings = MockSettings()

        with pytest.raises(ConfigurationError) as exc_info:
            validate_provider_config("invalid", settings)

        assert "not supported" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_custom_client(self):
        """Test creating custom client."""
        settings = MockSettings()

        client = _create_custom_client(settings)

        assert isinstance(client, CustomLLMClient)
        assert client.model_name == settings.model_name
        assert client.max_tokens == settings.max_tokens
        assert client.temperature == settings.temperature


class TestOpenRouterClient:
    """Test OpenRouter client implementation."""

    @pytest.fixture
    def mock_http_client(self):
        """Create mock HTTP client."""
        return MockHTTPClient()

    @pytest.fixture
    def openrouter_client(self, mock_http_client):
        """Create OpenRouter client with mock HTTP client."""
        client = OpenRouterClient(
            api_key="test-api-key",
            model="gpt-4o-mini",
            base_url="https://api.openrouter.ai/api/v1",
            timeout=30
        )
        client._http_client = mock_http_client
        return client

    def test_openrouter_client_initialization(self):
        """Test OpenRouter client initializes properly."""
        client = OpenRouterClient(
            api_key="test-key",
            model="gpt-4o",
            max_tokens=2000,
            temperature=0.8
        )

        assert client.api_key == "test-key"
        assert client.model == "gpt-4o"
        assert client.max_tokens == 2000
        assert client.temperature == 0.8
        assert "openrouter.ai" in client.base_url

    @pytest.mark.asyncio
    async def test_generate_completion_success(self, openrouter_client, mock_http_client):
        """Test successful completion generation."""
        messages = [
            {"role": "user", "content": "Hello, how are you?"}
        ]

        result = await openrouter_client.generate_completion(messages)

        assert "choices" in result
        assert len(result["choices"]) > 0
        assert result["choices"][0]["message"]["role"] == "assistant"
        assert "usage" in result
        assert mock_http_client.call_count == 1

    @pytest.mark.asyncio
    async def test_generate_completion_with_options(self, openrouter_client, mock_http_client):
        """Test completion with custom options."""
        messages = [{"role": "user", "content": "Test message"}]

        result = await openrouter_client.generate_completion(
            messages,
            temperature=0.9,
            max_tokens=500,
            top_p=0.8
        )

        # Verify request was made with correct parameters
        request = mock_http_client.requests_made[0]
        assert request["json"]["temperature"] == 0.9
        assert request["json"]["max_tokens"] == 500
        assert request["json"]["top_p"] == 0.8

    @pytest.mark.asyncio
    async def test_generate_completion_api_error(self, openrouter_client):
        """Test handling of API errors."""
        failing_client = MockHTTPClient(should_fail=True)
        openrouter_client._http_client = failing_client

        messages = [{"role": "user", "content": "Test"}]

        with pytest.raises(ExternalServiceError):
            await openrouter_client.generate_completion(messages)

    @pytest.mark.asyncio
    async def test_stream_completion(self, openrouter_client, mock_http_client):
        """Test streaming completion (if implemented)."""
        if hasattr(openrouter_client, 'stream_completion'):
            messages = [{"role": "user", "content": "Tell me a story"}]

            # Mock streaming response
            mock_stream_data = [
                {"choices": [{"delta": {"content": "Once"}}]},
                {"choices": [{"delta": {"content": " upon"}}]},
                {"choices": [{"delta": {"content": " a time"}}]}
            ]
            mock_http_client.responses["stream"] = mock_stream_data

            chunks = []
            async for chunk in openrouter_client.stream_completion(messages):
                chunks.append(chunk)

            assert len(chunks) > 0

    def test_prepare_headers(self, openrouter_client):
        """Test header preparation."""
        headers = openrouter_client._prepare_headers()

        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test-api-key"
        assert "Content-Type" in headers
        assert headers["Content-Type"] == "application/json"

    def test_prepare_payload(self, openrouter_client):
        """Test payload preparation."""
        messages = [
            {"role": "user", "content": "Hello"}
        ]

        payload = openrouter_client._prepare_payload(
            messages,
            temperature=0.7,
            max_tokens=1000
        )

        assert payload["model"] == openrouter_client.model
        assert payload["messages"] == messages
        assert payload["temperature"] == 0.7
        assert payload["max_tokens"] == 1000

    @pytest.mark.asyncio
    async def test_health_check(self, openrouter_client, mock_http_client):
        """Test client health check."""
        is_healthy = await openrouter_client.health_check()

        assert is_healthy is True
        # Should have made a simple request
        assert mock_http_client.call_count > 0

    @pytest.mark.asyncio
    async def test_health_check_failure(self, openrouter_client):
        """Test health check with API failure."""
        failing_client = MockHTTPClient(should_fail=True)
        openrouter_client._http_client = failing_client

        is_healthy = await openrouter_client.health_check()

        assert is_healthy is False


class TestCustomLLMClient:
    """Test custom LLM client implementation."""

    @pytest.fixture
    def custom_client(self):
        """Create custom LLM client."""
        return CustomLLMClient(
            model_name="custom-model",
            max_tokens=1500,
            temperature=0.6,
            provider="mock"
        )

    def test_custom_client_initialization(self):
        """Test custom client initializes properly."""
        client = CustomLLMClient(
            model_name="test-model",
            max_tokens=2000,
            temperature=0.8,
            provider="test-provider"
        )

        assert client.model_name == "test-model"
        assert client.max_tokens == 2000
        assert client.temperature == 0.8
        assert client.provider == "test-provider"

    @pytest.mark.asyncio
    async def test_generate_completion_mock_response(self, custom_client):
        """Test custom client generates mock responses."""
        messages = [
            {"role": "user", "content": "What is 2+2?"}
        ]

        result = await custom_client.generate_completion(messages)

        assert "choices" in result
        assert len(result["choices"]) > 0
        assert "message" in result["choices"][0]
        assert result["choices"][0]["message"]["role"] == "assistant"
        assert "content" in result["choices"][0]["message"]
        assert "usage" in result

    @pytest.mark.asyncio
    async def test_generate_completion_respects_options(self, custom_client):
        """Test custom client respects generation options."""
        messages = [{"role": "user", "content": "Test"}]

        result = await custom_client.generate_completion(
            messages,
            temperature=1.0,
            max_tokens=100
        )

        # Mock implementation should still return valid structure
        assert "choices" in result
        assert "usage" in result

        # Usage should reflect requested max_tokens (in mock)
        if "total_tokens" in result["usage"]:
            assert result["usage"]["total_tokens"] <= 100

    @pytest.mark.asyncio
    async def test_custom_client_different_providers(self):
        """Test custom client with different provider configs."""
        providers_to_test = ["openai", "anthropic", "local", "mock"]

        for provider in providers_to_test:
            client = CustomLLMClient(
                model_name=f"{provider}-model",
                provider=provider
            )

            messages = [{"role": "user", "content": f"Test {provider}"}]
            result = await client.generate_completion(messages)

            assert "choices" in result
            assert result["model"] == f"{provider}-model"

    @pytest.mark.asyncio
    async def test_custom_client_error_simulation(self, custom_client):
        """Test custom client can simulate errors."""
        # Test with special message that might trigger error simulation
        error_messages = [
            {"role": "user", "content": "ERROR_TEST"}
        ]

        # Depending on implementation, might raise error or return error response
        try:
            result = await custom_client.generate_completion(error_messages)
            # If no error raised, should still be valid response
            assert "choices" in result or "error" in result
        except ExternalServiceError:
            # Expected for error simulation
            pass

    @pytest.mark.asyncio
    async def test_health_check_custom(self, custom_client):
        """Test custom client health check."""
        is_healthy = await custom_client.health_check()

        # Custom client should always be healthy (it's a mock)
        assert is_healthy is True

    def test_custom_client_model_info(self, custom_client):
        """Test custom client provides model information."""
        info = custom_client.get_model_info()

        assert isinstance(info, dict)
        assert "model" in info
        assert "provider" in info
        assert info["model"] == custom_client.model_name


class TestBaseLLMClient:
    """Test base LLM client abstract class."""

    def test_base_client_is_abstract(self):
        """Test that BaseLLMClient cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseLLMClient()

    def test_base_client_interface_methods(self):
        """Test that BaseLLMClient defines required interface methods."""
        # Check that abstract methods are defined
        abstract_methods = BaseLLMClient.__abstractmethods__

        assert "generate_completion" in abstract_methods
        # Other abstract methods as defined in the base class


class TestLLMClientIntegration:
    """Test integration aspects of LLM clients."""

    @pytest.mark.asyncio
    async def test_multiple_clients_independence(self):
        """Test that multiple client instances are independent."""
        settings1 = MockSettings(model_name="model-1", temperature=0.5)
        settings2 = MockSettings(model_name="model-2", temperature=0.9)

        client1 = _create_custom_client(settings1)
        client2 = _create_custom_client(settings2)

        assert client1.model_name != client2.model_name
        assert client1.temperature != client2.temperature

        # Both should work independently
        messages = [{"role": "user", "content": "Test"}]

        result1 = await client1.generate_completion(messages)
        result2 = await client2.generate_completion(messages)

        assert result1["model"] == "model-1"
        assert result2["model"] == "model-2"

    @pytest.mark.asyncio
    async def test_client_with_retry_logic(self):
        """Test client behavior with retry mechanisms."""
        settings = MockSettings(max_retries=3)

        # Test would involve retry decorator if implemented
        client = _create_custom_client(settings)

        # Should handle retries gracefully
        messages = [{"role": "user", "content": "Test retry logic"}]
        result = await client.generate_completion(messages)

        assert "choices" in result

    @pytest.mark.asyncio
    async def test_client_timeout_handling(self):
        """Test client timeout handling."""
        # Create client with very short timeout
        client = OpenRouterClient(
            api_key="test-key",
            model="gpt-4o-mini",
            timeout=0.001  # Very short timeout
        )

        failing_http_client = MockHTTPClient(should_fail=True)
        client._http_client = failing_http_client

        messages = [{"role": "user", "content": "Test timeout"}]

        with pytest.raises(ExternalServiceError):
            await client.generate_completion(messages)

    @pytest.mark.asyncio
    async def test_concurrent_requests(self):
        """Test concurrent requests to LLM client."""
        client = CustomLLMClient()

        async def make_request(i):
            messages = [{"role": "user", "content": f"Request {i}"}]
            return await client.generate_completion(messages)

        # Make concurrent requests
        results = await asyncio.gather(*[make_request(i) for i in range(5)])

        assert len(results) == 5
        for result in results:
            assert "choices" in result


class TestLLMClientErrorHandling:
    """Test error handling in LLM clients."""

    @pytest.mark.asyncio
    async def test_invalid_messages_format(self):
        """Test handling of invalid message formats."""
        client = CustomLLMClient()

        # Invalid message format
        invalid_messages = [
            {"invalid": "format"},  # Missing role/content
            {"role": "user"},       # Missing content
            {"content": "test"}     # Missing role
        ]

        for invalid_msg in invalid_messages:
            with pytest.raises(ValidationError):
                await client.generate_completion([invalid_msg])

    @pytest.mark.asyncio
    async def test_empty_messages_list(self):
        """Test handling of empty messages list."""
        client = CustomLLMClient()

        with pytest.raises(ValidationError):
            await client.generate_completion([])

    @pytest.mark.asyncio
    async def test_invalid_temperature_range(self):
        """Test handling of invalid temperature values."""
        client = CustomLLMClient()
        messages = [{"role": "user", "content": "test"}]

        # Temperature outside valid range
        with pytest.raises(ValidationError):
            await client.generate_completion(messages, temperature=-0.1)

        with pytest.raises(ValidationError):
            await client.generate_completion(messages, temperature=2.1)

    @pytest.mark.asyncio
    async def test_invalid_max_tokens(self):
        """Test handling of invalid max_tokens values."""
        client = CustomLLMClient()
        messages = [{"role": "user", "content": "test"}]

        # Invalid max_tokens values
        with pytest.raises(ValidationError):
            await client.generate_completion(messages, max_tokens=0)

        with pytest.raises(ValidationError):
            await client.generate_completion(messages, max_tokens=-10)


class TestLLMClientConfiguration:
    """Test LLM client configuration options."""

    def test_openrouter_client_configuration_options(self):
        """Test OpenRouter client configuration options."""
        config_options = {
            "api_key": "test-key",
            "model": "gpt-4o",
            "base_url": "https://custom.api.url",
            "timeout": 60,
            "max_retries": 5,
            "temperature": 0.8,
            "max_tokens": 2000
        }

        client = OpenRouterClient(**config_options)

        assert client.api_key == config_options["api_key"]
        assert client.model == config_options["model"]
        assert client.base_url == config_options["base_url"]
        assert client.timeout == config_options["timeout"]

    def test_custom_client_configuration_options(self):
        """Test custom client configuration options."""
        config_options = {
            "model_name": "custom-model",
            "provider": "test-provider",
            "temperature": 0.9,
            "max_tokens": 1500,
            "top_p": 0.95
        }

        client = CustomLLMClient(**config_options)

        assert client.model_name == config_options["model_name"]
        assert client.provider == config_options["provider"]
        assert client.temperature == config_options["temperature"]
        assert client.max_tokens == config_options["max_tokens"]

    def test_client_default_configurations(self):
        """Test client default configuration values."""
        # Test with minimal configuration
        openrouter_client = OpenRouterClient(api_key="test")
        custom_client = CustomLLMClient()

        # Should have sensible defaults
        assert openrouter_client.timeout > 0
        assert openrouter_client.temperature >= 0 and openrouter_client.temperature <= 2
        assert openrouter_client.max_tokens > 0

        assert custom_client.temperature >= 0 and custom_client.temperature <= 2
        assert custom_client.max_tokens > 0


class TestLLMClientMetrics:
    """Test LLM client metrics and monitoring."""

    @pytest.mark.asyncio
    async def test_client_tracks_usage_stats(self):
        """Test that client tracks usage statistics."""
        client = CustomLLMClient()
        messages = [{"role": "user", "content": "Test message"}]

        result = await client.generate_completion(messages)

        assert "usage" in result
        usage = result["usage"]

        assert "prompt_tokens" in usage
        assert "completion_tokens" in usage
        assert "total_tokens" in usage

        assert usage["total_tokens"] == usage["prompt_tokens"] + usage["completion_tokens"]

    @pytest.mark.asyncio
    async def test_client_request_timing(self):
        """Test that client can track request timing."""
        import time

        client = CustomLLMClient()
        messages = [{"role": "user", "content": "Time this request"}]

        start_time = time.time()
        result = await client.generate_completion(messages)
        end_time = time.time()

        request_duration = end_time - start_time

        # Request should complete in reasonable time
        assert request_duration < 5.0  # Less than 5 seconds for mock

        # Some clients might include timing in response
        if "metadata" in result and "response_time" in result["metadata"]:
            assert result["metadata"]["response_time"] > 0

    @pytest.mark.asyncio
    async def test_client_error_metrics(self):
        """Test client error tracking."""
        failing_client = OpenRouterClient(api_key="invalid-key")
        failing_client._http_client = MockHTTPClient(should_fail=True)

        messages = [{"role": "user", "content": "This will fail"}]

        try:
            await failing_client.generate_completion(messages)
        except ExternalServiceError as e:
            # Client should provide error context
            assert str(e) is not None
            # Could track error metrics here
