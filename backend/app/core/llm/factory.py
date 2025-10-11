"""
LLM client factory for NeedleAi.
Unified OpenRouter-based LLM access.
"""

from typing import Any, Dict

from app.config import Settings
from app.core.llm.base import BaseLLMClient
from app.exceptions import ValidationError


def get_llm_client(provider: str, settings: Settings) -> BaseLLMClient:
    """
    Factory function to create the appropriate LLM client.

    Args:
        provider: The LLM provider name (now primarily 'openrouter')
        settings: Application settings

    Returns:
        Configured LLM client instance

    Raises:
        ValidationError: If provider is not supported or configuration is invalid
    """
    provider = provider.lower()

    if provider == "openrouter":
        return _create_openrouter_client(settings)
    elif provider == "custom":
        return _create_custom_client(settings)
    else:
        raise ValidationError(
            f"Unsupported LLM provider: {provider}. "
            f"Supported providers: openrouter, custom"
        )


def _create_openrouter_client(settings: Settings) -> BaseLLMClient:
    """Create Agno + OpenRouter client for unified LLM access."""
    from app.core.llm.openrouter_client import AgnoOpenRouterClient

    config = {
        "api_key": getattr(settings, "openrouter_api_key", None),
        "model": getattr(settings, "default_model", "gpt-5"),
        "max_tokens": getattr(settings, "max_tokens", 1000),
        "temperature": getattr(settings, "temperature", 0.7),
        "site_url": getattr(settings, "site_url", settings.app_name),
        "app_name": settings.app_name,
        "use_memory": getattr(settings, "use_agno_memory", True),
        "structured_outputs": getattr(settings, "structured_outputs", False),
        "instructions": getattr(settings, "agent_instructions", None),
    }

    return AgnoOpenRouterClient(config)


def _create_custom_client(settings: Settings) -> BaseLLMClient:
    """Create custom/mock client for development."""
    from app.core.llm.custom_client import CustomLLMClient

    config = {
        "model": "custom-model",
        "echo_mode": getattr(settings, "debug", False)
    }

    return CustomLLMClient(config)


def list_available_providers() -> Dict[str, Dict[str, Any]]:
    """
    List all available LLM providers and their requirements.

    Returns:
        Dictionary with provider information
    """
    return {
        "openrouter": {
            "name": "Agno + OpenRouter (AI Agent Framework)",
            "description": "Access to 500+ models through Agno's powerful agent framework + OpenRouter API",
            "models": [
                "gpt-5", "anthropic/claude-3.7-sonnet", "google/gemini-2.5-pro",
                "openai/gpt-4o", "anthropic/claude-3.5-sonnet", "google/gemini-1.5-pro",
                "openai/gpt-4o-mini", "anthropic/claude-3-haiku", "google/gemini-1.5-flash",
                "meta-llama/llama-3.3-70b-instruct", "deepseek/deepseek-chat"
            ],
            "required_env": ["OPENROUTER_API_KEY"],
            "supports_streaming": True,
            "supports_function_calling": True,
            "supports_agents": True,
            "supports_memory": True,
            "supports_tools": True,
            "supports_workflows": True,
            "unified_api": True,
            "agno_framework": True,
            "pricing": "Pay per token, better prices",
            "uptime": "Higher availability via distributed infrastructure"
        },
        "custom": {
            "name": "Custom/Mock",
            "description": "Mock client for development and testing",
            "models": ["custom-model"],
            "required_env": [],
            "supports_streaming": True,
            "supports_function_calling": False,
            "development_only": True
        }
    }


def validate_provider_config(provider: str, settings: Settings) -> Dict[str, Any]:
    """
    Validate provider configuration.

    Args:
        provider: Provider name
        settings: Application settings

    Returns:
        Validation results

    Raises:
        ValidationError: If configuration is invalid
    """
    providers = list_available_providers()

    if provider not in providers:
        raise ValidationError(f"Unknown provider: {provider}")

    provider_info = providers[provider]
    validation_results = {
        "provider": provider,
        "valid": True,
        "errors": [],
        "warnings": []
    }

    # Check required environment variables
    for env_var in provider_info.get("required_env", []):
        setting_name = env_var.lower().replace("_", "")
        if not getattr(settings, setting_name, None):
            validation_results["errors"].append(f"Missing required setting: {setting_name}")
            validation_results["valid"] = False

    # Provider-specific validations
    if provider == "openrouter":
        model = getattr(settings, "default_model", "")
        available_models = provider_info.get("models", [])

        # Check if it's a known model pattern
        if model and not any(model in available_model for available_model in available_models):
            validation_results["warnings"].append(
                f"Model {model} not in popular list. OpenRouter supports 500+ models."
            )

    return validation_results
