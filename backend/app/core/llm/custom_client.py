"""
Custom/Mock LLM client for development and testing.
"""

import asyncio
from typing import Any, AsyncGenerator, Dict, List, Optional

from app.core.llm.base import BaseLLMClient
from app.models.chat import ChatMessage


class CustomLLMClient(BaseLLMClient):
    """Custom LLM client for development and testing."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.model = config.get("model", "custom-model")
        self.echo_mode = config.get("echo_mode", True)

    async def generate_response(
        self,
        message: str,
        conversation_history: Optional[List[ChatMessage]] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        """Generate a mock response."""
        # Simulate API delay
        await asyncio.sleep(0.5)

        if self.echo_mode:
            return f"Echo: {message}"

        # Simple mock responses based on message content
        message_lower = message.lower()

        if "hello" in message_lower or "hi" in message_lower:
            return "Hello! How can I help you today?"
        elif "help" in message_lower:
            return "I'm a custom LLM client for development. I can help you test the chat functionality."
        elif "weather" in message_lower:
            return "I'm sorry, I don't have access to real weather data. This is a mock response for testing."
        elif "name" in message_lower:
            return f"I'm a custom AI assistant powered by {self.model}."
        else:
            return f"Thank you for your message: '{message}'. This is a mock response from the custom LLM client."

    async def generate_completion(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        stop_sequences: Optional[List[str]] = None,
        system_message: Optional[str] = None,
        **kwargs
    ) -> str:
        """Generate a mock completion."""
        # Simulate API delay
        await asyncio.sleep(0.3)

        if self.echo_mode:
            return f"Completion for: {prompt}"

        # Generate a simple completion based on prompt
        if prompt.endswith("?"):
            return "That's an interesting question. This is a mock completion response."
        elif "write" in prompt.lower():
            return "Here's a mock written response for your prompt."
        elif "explain" in prompt.lower():
            return "This is a mock explanation. In a real implementation, this would provide detailed information."
        else:
            return f"Mock completion: {prompt[:50]}{'...' if len(prompt) > 50 else ''}"

    async def generate_streaming_completion(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        stop_sequences: Optional[List[str]] = None,
        system_message: Optional[str] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Generate a streaming mock completion."""
        response = await self.generate_completion(prompt, **kwargs)

        # Stream the response word by word
        words = response.split()
        for word in words:
            await asyncio.sleep(0.1)  # Simulate streaming delay
            yield word + " "

    def get_model_name(self) -> str:
        """Get the custom model name."""
        return self.model

    async def health_check(self) -> bool:
        """Custom client is always healthy."""
        return True

    def get_provider_info(self) -> Dict[str, Any]:
        """Get custom provider information."""
        return {
            "provider": "Custom",
            "model": self.model,
            "api_configured": True,
            "echo_mode": self.echo_mode,
            "development_only": True
        }
