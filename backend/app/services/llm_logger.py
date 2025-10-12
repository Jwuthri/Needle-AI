"""
LLM Call Logger Service

Provides easy-to-use utilities for logging all LLM API calls.
Use this service to wrap your LLM calls for automatic logging.
"""

import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, Optional

from app.database.models.llm_call import LLMCall, LLMCallStatusEnum, LLMCallTypeEnum
from app.database.repositories.llm_call import LLMCallRepository
from app.database.session import get_async_session
from app.utils.logging import get_logger
from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger("llm_logger")


class LLMLogger:
    """
    Service for logging LLM API calls.
    
    Usage:
        # Method 1: Context manager (automatic timing)
        async with LLMLogger.log_call(
            call_type=LLMCallTypeEnum.CHAT,
            provider="openrouter",
            model="gpt-4",
            prompt="Hello",
            user_id=user_id
        ) as log_id:
            response = await llm_client.generate(...)
            await LLMLogger.complete(
                log_id,
                response=response.text,
                tokens={'total_tokens': 100}
            )
        
        # Method 2: Manual logging
        log_id = await LLMLogger.start(...)
        try:
            response = await llm_client.generate(...)
            await LLMLogger.complete(log_id, ...)
        except Exception as e:
            await LLMLogger.fail(log_id, str(e))
    """

    @staticmethod
    @asynccontextmanager
    async def log_call(
        call_type: LLMCallTypeEnum,
        provider: str,
        model: str,
        messages: list,
        db: Optional[AsyncSession] = None,
        **kwargs
    ):
        """
        Context manager for logging an LLM call with automatic timing.
        
        Args:
            call_type: Type of LLM call
            provider: LLM provider (openrouter, openai, etc.)
            model: Model name
            messages: Array of message objects [{"role": "user", "content": "..."}]
            db: Database session (optional, creates one if not provided)
            **kwargs: Additional fields (system_prompt, tools, user_id, session_id, etc.)
        
        Yields:
            log_id: The ID of the created log entry
        """
        start_time = time.time()
        log_id = str(uuid.uuid4())
        
        # Create or use provided session
        should_close = False
        if db is None:
            async with get_async_session() as db:
                should_close = True
                call = await LLMCallRepository.create(
                    db,
                    call_type=call_type,
                    provider=provider,
                    model=model,
                    messages=messages,
                    id=log_id,
                    started_at=datetime.utcnow(),
                    **kwargs
                )
                await db.commit()
        else:
            call = await LLMCallRepository.create(
                db,
                call_type=call_type,
                provider=provider,
                model=model,
                messages=messages,
                id=log_id,
                started_at=datetime.utcnow(),
                **kwargs
            )
            await db.flush()

        try:
            yield log_id
        except Exception as e:
            # Log the error
            latency = int((time.time() - start_time) * 1000)
            async with get_async_session() as error_db:
                await LLMCallRepository.mark_failed(
                    error_db,
                    log_id,
                    error_message=str(e),
                    status=LLMCallStatusEnum.ERROR
                )
                await LLMCallRepository.update(error_db, log_id, latency_ms=latency)
                await error_db.commit()
            raise

    @staticmethod
    async def start(
        call_type: LLMCallTypeEnum,
        provider: str,
        model: str,
        messages: list,
        db: Optional[AsyncSession] = None,
        **kwargs
    ) -> str:
        """
        Start logging an LLM call (manual mode).
        
        Args:
            messages: Array of message objects [{"role": "user", "content": "..."}]
        
        Returns:
            log_id: The ID of the created log entry
        """
        log_id = str(uuid.uuid4())
        
        if db is None:
            async with get_async_session() as db:
                await LLMCallRepository.create(
                    db,
                    call_type=call_type,
                    provider=provider,
                    model=model,
                    messages=messages,
                    id=log_id,
                    started_at=datetime.utcnow(),
                    **kwargs
                )
                await db.commit()
        else:
            await LLMCallRepository.create(
                db,
                call_type=call_type,
                provider=provider,
                model=model,
                messages=messages,
                id=log_id,
                started_at=datetime.utcnow(),
                **kwargs
            )
            await db.flush()
        
        return log_id

    @staticmethod
    async def complete(
        log_id: str,
        response_message: dict,
        tokens: Optional[Dict[str, int]] = None,
        estimated_cost: Optional[float] = None,
        finish_reason: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ):
        """
        Mark an LLM call as completed with results.
        
        Args:
            log_id: The log entry ID
            response_message: Response message dict with 'role', 'content', optional 'tool_calls'
                Example: {"role": "assistant", "content": "Hello!", "tool_calls": [...]}
            tokens: Token usage dict with keys: prompt_tokens, completion_tokens, total_tokens
            estimated_cost: Estimated cost in USD
            finish_reason: Completion reason (stop, tool_calls, length, etc.)
            db: Database session (optional)
        """
        # Calculate latency
        if db is None:
            async with get_async_session() as db:
                call = await LLMCallRepository.get_by_id(db, log_id)
                if call and call.started_at:
                    latency_ms = int((datetime.utcnow() - call.started_at).total_seconds() * 1000)
                else:
                    latency_ms = None
                
                await LLMCallRepository.mark_completed(
                    db,
                    log_id,
                    response_message=response_message,
                    tokens=tokens,
                    latency_ms=latency_ms,
                    estimated_cost=estimated_cost,
                    finish_reason=finish_reason
                )
                await db.commit()
        else:
            call = await LLMCallRepository.get_by_id(db, log_id)
            if call and call.started_at:
                latency_ms = int((datetime.utcnow() - call.started_at).total_seconds() * 1000)
            else:
                latency_ms = None
            
            await LLMCallRepository.mark_completed(
                db,
                log_id,
                response_message=response_message,
                tokens=tokens,
                latency_ms=latency_ms,
                estimated_cost=estimated_cost,
                finish_reason=finish_reason
            )
            await db.flush()

    @staticmethod
    async def fail(
        log_id: str,
        error_message: str,
        error_code: Optional[str] = None,
        status: LLMCallStatusEnum = LLMCallStatusEnum.ERROR,
        db: Optional[AsyncSession] = None
    ):
        """
        Mark an LLM call as failed.
        
        Args:
            log_id: The log entry ID
            error_message: Error message
            error_code: Error code (optional)
            status: Error status (ERROR, TIMEOUT, RATE_LIMITED)
            db: Database session (optional)
        """
        if db is None:
            async with get_async_session() as db:
                # Calculate latency
                call = await LLMCallRepository.get_by_id(db, log_id)
                if call and call.started_at:
                    latency_ms = int((datetime.utcnow() - call.started_at).total_seconds() * 1000)
                    await LLMCallRepository.update(db, log_id, latency_ms=latency_ms)
                
                await LLMCallRepository.mark_failed(
                    db,
                    log_id,
                    error_message=error_message,
                    error_code=error_code,
                    status=status
                )
                await db.commit()
        else:
            # Calculate latency
            call = await LLMCallRepository.get_by_id(db, log_id)
            if call and call.started_at:
                latency_ms = int((datetime.utcnow() - call.started_at).total_seconds() * 1000)
                await LLMCallRepository.update(db, log_id, latency_ms=latency_ms)
            
            await LLMCallRepository.mark_failed(
                db,
                log_id,
                error_message=error_message,
                error_code=error_code,
                status=status
            )
            await db.flush()

    @staticmethod
    async def get_cost_stats(
        user_id: Optional[str] = None,
        company_id: Optional[str] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get cost statistics for LLM calls."""
        async with get_async_session() as db:
            return await LLMCallRepository.get_cost_stats(
                db,
                user_id=user_id,
                company_id=company_id,
                days=days
            )

    @staticmethod
    async def get_performance_stats(
        provider: Optional[str] = None,
        model: Optional[str] = None,
        days: int = 7
    ) -> Dict[str, Any]:
        """Get performance statistics for LLM calls."""
        async with get_async_session() as db:
            return await LLMCallRepository.get_performance_stats(
                db,
                provider=provider,
                model=model,
                days=days
            )


# Convenience functions for common use cases
async def log_chat_call(message: str, model: str, user_id: str, session_id: str, system_prompt: Optional[str] = None, **kwargs) -> str:
    """Quick log for chat calls."""
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": message})
    
    return await LLMLogger.start(
        call_type=LLMCallTypeEnum.CHAT,
        provider=kwargs.get('provider', 'openrouter'),
        model=model,
        messages=messages,
        system_prompt=system_prompt,
        user_id=user_id,
        session_id=session_id,
        **kwargs
    )


async def log_rag_query(query: str, model: str, company_id: str, system_prompt: Optional[str] = None, **kwargs) -> str:
    """Quick log for RAG retrieval queries."""
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": query})
    
    return await LLMLogger.start(
        call_type=LLMCallTypeEnum.RAG_QUERY,
        provider=kwargs.get('provider', 'openrouter'),
        model=model,
        messages=messages,
        system_prompt=system_prompt,
        company_id=company_id,
        **kwargs
    )


async def log_sentiment_analysis(text: str, model: str, review_id: str, **kwargs) -> str:
    """Quick log for sentiment analysis."""
    messages = [{"role": "user", "content": f"Analyze sentiment: {text[:200]}..."}]
    
    return await LLMLogger.start(
        call_type=LLMCallTypeEnum.SENTIMENT_ANALYSIS,
        provider=kwargs.get('provider', 'openrouter'),
        model=model,
        messages=messages,
        review_id=review_id,
        **kwargs
    )

