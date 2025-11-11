"""
Utility helper for automatically logging LLM calls.

This module provides a decorator and helper functions to automatically log
all LLM calls to the llm_calls table.
"""

import time
from datetime import datetime
from typing import Any, Dict, Optional
from functools import wraps

from llama_index.core.llms import ChatMessage
from llama_index.llms.openai import OpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.llm_call import LLMCallTypeEnum, LLMCallStatusEnum
from app.database.repositories.llm_call import LLMCallRepository
from app.utils.logging import get_logger

logger = get_logger(__name__)


def extract_provider_and_model(llm: OpenAI) -> tuple[str, str]:
    """
    Extract provider and model name from LLM instance.
    
    Args:
        llm: LlamaIndex OpenAI LLM instance
        
    Returns:
        Tuple of (provider, model)
    """
    # Try to get model from llm instance
    model_name = getattr(llm, 'model', 'unknown')
    
    # Determine provider based on model or API key
    provider = 'openrouter'  # Default for get_llm()
    
    # Check if it's OpenAI directly
    if hasattr(llm, 'api_key') and llm.api_key:
        if 'openai.com' in str(getattr(llm, 'api_base', '')):
            provider = 'openai'
        elif 'anthropic' in str(getattr(llm, 'api_base', '')):
            provider = 'anthropic'
    
    return provider, model_name


def convert_messages_to_dict(messages: list[ChatMessage]) -> list[Dict[str, str]]:
    """
    Convert LlamaIndex ChatMessage objects to dict format for storage.
    
    Args:
        messages: List of ChatMessage objects
        
    Returns:
        List of message dicts
    """
    result = []
    for msg in messages:
        msg_dict = {
            'role': msg.role if isinstance(msg.role, str) else msg.role.value,
            'content': msg.content if isinstance(msg.content, str) else str(msg.content)
        }
        result.append(msg_dict)
    return result


async def log_llm_call(
    llm: OpenAI,
    messages: list[ChatMessage],
    call_type: LLMCallTypeEnum,
    db: AsyncSession,
    user_id: Optional[str] = None,
    **kwargs
) -> str:
    """
    Log an LLM call before execution.
    
    Args:
        llm: LLM instance
        messages: List of ChatMessage objects
        call_type: Type of LLM call
        db: Database session
        user_id: Optional user ID
        **kwargs: Additional metadata (session_id, company_id, etc.)
        
    Returns:
        log_id: The ID of the created log entry
    """
    provider, model = extract_provider_and_model(llm)
    messages_dict = convert_messages_to_dict(messages)
    
    # Extract system prompt if present
    system_prompt = None
    for msg in messages:
        if msg.role == 'system' or (isinstance(msg.role, str) and msg.role == 'system'):
            system_prompt = msg.content if isinstance(msg.content, str) else str(msg.content)
            break
    
    llm_call = await LLMCallRepository.create(
        db,
        call_type=call_type,
        provider=provider,
        model=model,
        messages=messages_dict,
        system_prompt=system_prompt,
        user_id=user_id,
        started_at=datetime.utcnow(),
        **kwargs
    )
    
    return llm_call.id


async def complete_llm_call(
    log_id: str,
    response: Any,
    db: AsyncSession,
    tokens: Optional[Dict[str, int]] = None,
    estimated_cost: Optional[float] = None
):
    """
    Mark an LLM call as completed with response.
    
    Args:
        log_id: Log entry ID
        response: LLM response object (ChatResponse or similar)
        db: Database session
        tokens: Token usage dict
        estimated_cost: Estimated cost in USD
    """
    # Extract response message
    response_message = None
    finish_reason = None
    
    if hasattr(response, 'message'):
        # ChatResponse from LlamaIndex
        msg = response.message
        response_message = {
            'role': msg.role if isinstance(msg.role, str) else msg.role.value,
            'content': msg.content if isinstance(msg.content, str) else str(msg.content)
        }
        if hasattr(msg, 'additional_kwargs'):
            response_message['additional_kwargs'] = msg.additional_kwargs
    elif hasattr(response, 'raw'):
        # Structured output response
        msg = response.raw if hasattr(response, 'raw') else response
        if hasattr(msg, 'message'):
            msg = msg.message
        response_message = {
            'role': 'assistant',
            'content': str(msg) if not isinstance(msg, dict) else msg
        }
    elif isinstance(response, dict):
        response_message = response
    else:
        response_message = {
            'role': 'assistant',
            'content': str(response)
        }
    
    # Extract finish reason if available
    if hasattr(response, 'raw_response'):
        raw = response.raw_response
        if hasattr(raw, 'choices') and raw.choices:
            finish_reason = getattr(raw.choices[0], 'finish_reason', None)
    
    await LLMCallRepository.mark_completed(
        db,
        log_id,
        response_message=response_message,
        tokens=tokens,
        estimated_cost=estimated_cost,
        finish_reason=finish_reason
    )


async def fail_llm_call(
    log_id: str,
    error: Exception,
    db: AsyncSession,
    status: LLMCallStatusEnum = LLMCallStatusEnum.ERROR
):
    """
    Mark an LLM call as failed.
    
    Args:
        log_id: Log entry ID
        error: Exception that occurred
        db: Database session
        status: Error status
    """
    await LLMCallRepository.mark_failed(
        db,
        log_id,
        error_message=str(error),
        error_code=type(error).__name__,
        status=status
    )

