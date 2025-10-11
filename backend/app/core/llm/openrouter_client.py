"""
Agno + OpenRouter LLM client implementation for NeedleAi.
Unified access to 500+ models through Agno's powerful agent framework.
"""

import os
from typing import Any, AsyncGenerator, Dict, List, Optional

from app.core.llm.base import BaseLLMClient
from app.exceptions import LLMError
from app.models.chat import ChatMessage
from app.utils.logging import get_logger

try:
    from agno.agent import Agent
    from agno.models.message import Message
    from agno.models.openrouter import OpenRouter
except ImportError:
    Agent = None
    OpenRouter = None
    Message = None

logger = get_logger("openrouter_client")


class AgnoOpenRouterClient(BaseLLMClient):
    """Agno + OpenRouter unified LLM client implementation."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)

        if Agent is None or OpenRouter is None:
            raise ImportError("Agno package not installed. Install with: uv add agno")

        self.api_key = config.get("api_key") or os.getenv("OPENROUTER_API_KEY")
        self.model = config.get("model", "gpt-5")
        self.max_tokens = config.get("max_tokens", 1000)
        self.temperature = config.get("temperature", 0.7)
        self.site_url = config.get("site_url", "NeedleAi")
        self.app_name = config.get("app_name", "NeedleAi")

        if not self.api_key:
            raise ValueError("OpenRouter API key is required")

        # Set OpenRouter API key as environment variable for Agno
        os.environ["OPENROUTER_API_KEY"] = self.api_key

        # Initialize Agno agent with OpenRouter model
        self.agent = Agent(
            model=OpenRouter(id=self.model),
            markdown=True,
            show_tool_calls=True,
            # Add memory and other Agno capabilities
            memory=config.get("use_memory", True),
            # Enable structured outputs
            structured_outputs=config.get("structured_outputs", False),
            # Add instructions/system prompt support
            instructions=config.get("instructions", None)
        )

        logger.info(f"Agno OpenRouter agent initialized with model: {self.model}")

    async def generate_response(
        self,
        message: str,
        conversation_history: Optional[List[ChatMessage]] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        """Generate a response using Agno + OpenRouter."""
        try:
            # Update agent instructions if system prompt provided
            if system_prompt and system_prompt != self.agent.instructions:
                self.agent.instructions = system_prompt

            # Add conversation history to agent memory if provided
            if conversation_history:
                for msg in conversation_history:
                    # Add previous messages to agent's memory
                    self.agent.memory.add(
                        role=msg.role.value,
                        content=msg.content
                    )

            # Generate response using Agno agent
            response = self.agent.run(message)

            # Return the agent's response content
            if hasattr(response, 'content'):
                return response.content
            elif isinstance(response, str):
                return response
            else:
                return str(response)

        except Exception as e:
            logger.error(f"Error generating Agno response: {e}")
            raise LLMError(f"Failed to generate response: {str(e)}")

    async def generate_completion(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        stop_sequences: Optional[List[str]] = None,
        system_message: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs
    ) -> str:
        """Generate a completion using Agno + OpenRouter."""
        try:
            # Create a new agent if model specified is different
            agent_to_use = self.agent
            if model and model != self.model:
                agent_to_use = Agent(
                    model=OpenRouter(id=model),
                    markdown=True,
                    instructions=system_message
                )
            elif system_message:
                agent_to_use.instructions = system_message

            # Generate completion using Agno agent
            response = agent_to_use.run(prompt)

            # Return the agent's response content
            if hasattr(response, 'content'):
                return response.content
            elif isinstance(response, str):
                return response
            else:
                return str(response)

        except Exception as e:
            logger.error(f"Error generating Agno completion: {e}")
            raise LLMError(f"Failed to generate completion: {str(e)}")

    async def generate_streaming_completion(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        stop_sequences: Optional[List[str]] = None,
        system_message: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Generate a streaming completion using Agno + OpenRouter."""
        try:
            # For now, Agno doesn't support streaming, so we'll return the full response
            # in chunks. In the future, Agno may add streaming support.
            response = await self.generate_completion(
                prompt, max_tokens, temperature, top_p, stop_sequences, system_message, model, **kwargs
            )

            # Simulate streaming by yielding chunks
            chunk_size = 10  # characters per chunk
            for i in range(0, len(response), chunk_size):
                yield response[i:i + chunk_size]

        except Exception as e:
            logger.error(f"Error generating streaming Agno completion: {e}")
            raise LLMError(f"Failed to generate streaming completion: {str(e)}")

    def get_model_name(self) -> str:
        """Get the current model name."""
        return self.model

    async def health_check(self) -> bool:
        """Check Agno + OpenRouter health."""
        try:
            # Simple test request using Agno
            response = self.agent.run("Hello")
            return bool(response)
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    def get_provider_info(self) -> Dict[str, Any]:
        """Get Agno + OpenRouter provider information."""
        return {
            "provider": "Agno + OpenRouter",
            "model": self.model,
            "api_configured": bool(self.api_key),
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "available_models": self.get_available_models(),
            "supports_streaming": True,
            "unified_api": True,
            "supports_agents": True,
            "supports_memory": True,
            "supports_tools": True,
            "agno_framework": True
        }

    def get_available_models(self) -> List[str]:
        """Get list of popular available models on OpenRouter via Agno."""
        return [
            # Latest and Greatest
            "gpt-5",  # New GPT-5
            "anthropic/claude-3.7-sonnet",
            "google/gemini-2.5-pro",

            # Production Ready
            "openai/gpt-4o",
            "anthropic/claude-3.5-sonnet",
            "google/gemini-1.5-pro",

            # Fast & Efficient
            "openai/gpt-4o-mini",
            "anthropic/claude-3-haiku",
            "google/gemini-1.5-flash",

            # Open Source Leaders
            "meta-llama/llama-3.3-70b-instruct",
            "deepseek/deepseek-chat",
            "qwen/qwen-2.5-72b-instruct"
        ]

    def switch_model(self, model: str) -> None:
        """Switch to a different model by creating a new Agno agent."""
        self.model = model

        # Create new agent with the new model
        self.agent = Agent(
            model=OpenRouter(id=model),
            markdown=True,
            show_tool_calls=True,
            memory=True,
            instructions=self.agent.instructions if hasattr(self.agent, 'instructions') else None
        )

        logger.info(f"Switched Agno agent to model: {model}")

    def get_model_info(self, model: str) -> Dict[str, Any]:
        """Get information about a specific model via Agno + OpenRouter."""
        return {
            "model": model,
            "provider": "Agno + OpenRouter",
            "supports_streaming": True,
            "supports_function_calling": True,
            "supports_agents": True,
            "supports_memory": True,
            "supports_tools": True,
            "context_length": "varies",  # Model-dependent
            "agno_enhanced": True
        }
