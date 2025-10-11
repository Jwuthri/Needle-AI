"""
Base LLM interface for NeedleAi.
"""

from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Dict, List, Optional

from app.models.chat import ChatMessage


class BaseLLMClient(ABC):
    """Base class for all LLM client implementations."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    @abstractmethod
    async def generate_response(
        self,
        message: str,
        conversation_history: Optional[List[ChatMessage]] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Generate a response from the LLM.

        Args:
            message: The user's input message
            conversation_history: Previous messages in the conversation
            system_prompt: Optional system prompt to guide the AI's behavior
            **kwargs: Additional parameters specific to the LLM

        Returns:
            The generated response string
        """

    @abstractmethod
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
        """
        Generate a text completion.

        Args:
            prompt: The input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            top_p: Top-p sampling parameter
            stop_sequences: Sequences that stop generation
            system_message: Optional system message
            **kwargs: Additional parameters

        Returns:
            The generated completion text
        """

    @abstractmethod
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
        """
        Generate a streaming text completion.

        Args:
            prompt: The input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            top_p: Top-p sampling parameter
            stop_sequences: Sequences that stop generation
            system_message: Optional system message
            **kwargs: Additional parameters

        Yields:
            Completion text chunks as they're generated
        """

    @abstractmethod
    def get_model_name(self) -> str:
        """Get the name of the model being used."""

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the LLM service is healthy."""

    def get_provider_info(self) -> Dict[str, Any]:
        """Get information about the LLM provider."""
        return {
            "provider": self.__class__.__name__,
            "model": self.get_model_name(),
            "config": {k: v for k, v in self.config.items() if "key" not in k.lower()}
        }

    def _prepare_messages(
        self,
        message: str,
        conversation_history: Optional[List[ChatMessage]] = None,
        system_prompt: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """
        Prepare messages in the format expected by most LLM APIs.

        Args:
            message: Current user message
            conversation_history: Previous conversation
            system_prompt: Optional system prompt

        Returns:
            List of message dictionaries
        """
        messages = []

        # Add system prompt if provided
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        # Add conversation history
        if conversation_history:
            for msg in conversation_history[-10:]:  # Keep last 10 messages
                messages.append({
                    "role": msg.role.value,
                    "content": msg.content
                })

        # Add current message
        messages.append({"role": "user", "content": message})

        return messages

    def _get_default_system_prompt(self) -> str:
        """Get default system prompt."""
        return "You are a helpful AI assistant. Provide clear, concise, and helpful responses."

    def _validate_parameters(
        self,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Validate and normalize parameters.

        Returns:
            Dictionary of validated parameters
        """
        params = {}

        if max_tokens is not None:
            if max_tokens <= 0:
                raise ValueError("max_tokens must be positive")
            params["max_tokens"] = min(max_tokens, 4000)  # Reasonable upper limit

        if temperature is not None:
            if not 0 <= temperature <= 2:
                raise ValueError("temperature must be between 0 and 2")
            params["temperature"] = temperature

        if top_p is not None:
            if not 0 < top_p <= 1:
                raise ValueError("top_p must be between 0 and 1")
            params["top_p"] = top_p

        return params
