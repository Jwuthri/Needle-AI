"""
LLM Call repository for logging and querying LLM API calls.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy import desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database.models.llm_call import LLMCall, LLMCallStatusEnum, LLMCallTypeEnum
from app.utils.logging import get_logger

logger = get_logger("llm_call_repository")


class LLMCallRepository:
    """Repository for LLM call logging and analysis."""

    @staticmethod
    async def create(
        db: AsyncSession,
        call_type: LLMCallTypeEnum,
        provider: str,
        model: str,
        messages: list,
        **kwargs
    ) -> LLMCall:
        """
        Create a new LLM call log entry.
        
        Args:
            messages: Array of message objects with 'role' and 'content'
                Example: [
                    {"role": "system", "content": "You are a helpful assistant"},
                    {"role": "user", "content": "Hello!"}
                ]
        """
        llm_call = LLMCall(
            call_type=call_type,
            provider=provider,
            model=model,
            messages=messages,
            **kwargs
        )
        db.add(llm_call)
        await db.flush()
        await db.refresh(llm_call)
        return llm_call

    @staticmethod
    async def get_by_id(db: AsyncSession, call_id: str) -> Optional[LLMCall]:
        """Get LLM call by ID."""
        result = await db.execute(select(LLMCall).filter(LLMCall.id == call_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def update(db: AsyncSession, call_id: str, **kwargs) -> Optional[LLMCall]:
        """Update an LLM call log entry."""
        llm_call = await LLMCallRepository.get_by_id(db, call_id)
        if not llm_call:
            return None

        for key, value in kwargs.items():
            if hasattr(llm_call, key):
                setattr(llm_call, key, value)

        await db.flush()
        await db.refresh(llm_call)
        return llm_call

    @staticmethod
    async def mark_completed(
        db: AsyncSession,
        call_id: str,
        response_message: dict,
        tokens: Optional[Dict[str, int]] = None,
        latency_ms: Optional[int] = None,
        estimated_cost: Optional[float] = None,
        finish_reason: Optional[str] = None
    ) -> Optional[LLMCall]:
        """
        Mark an LLM call as completed with results.
        
        Args:
            response_message: Response message object
                Example: {
                    "role": "assistant",
                    "content": "Hello! How can I help?",
                    "tool_calls": [...]  # Optional
                }
        """
        update_data = {
            'status': LLMCallStatusEnum.SUCCESS,
            'response_message': response_message,
            'completed_at': datetime.utcnow()
        }

        if tokens:
            update_data.update({
                'prompt_tokens': tokens.get('prompt_tokens'),
                'completion_tokens': tokens.get('completion_tokens'),
                'total_tokens': tokens.get('total_tokens')
            })

        if latency_ms:
            update_data['latency_ms'] = latency_ms

        if estimated_cost:
            update_data['estimated_cost'] = estimated_cost

        if finish_reason:
            update_data['finish_reason'] = finish_reason

        return await LLMCallRepository.update(db, call_id, **update_data)

    @staticmethod
    async def mark_failed(
        db: AsyncSession,
        call_id: str,
        error_message: str,
        error_code: Optional[str] = None,
        status: LLMCallStatusEnum = LLMCallStatusEnum.ERROR
    ) -> Optional[LLMCall]:
        """Mark an LLM call as failed."""
        return await LLMCallRepository.update(
            db,
            call_id,
            status=status,
            error_message=error_message,
            error_code=error_code,
            completed_at=datetime.utcnow()
        )

    @staticmethod
    async def list_by_filters(
        db: AsyncSession,
        call_type: Optional[LLMCallTypeEnum] = None,
        status: Optional[LLMCallStatusEnum] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        company_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[LLMCall]:
        """List LLM calls with various filters."""
        query = select(LLMCall)

        if call_type:
            query = query.filter(LLMCall.call_type == call_type)
        if status:
            query = query.filter(LLMCall.status == status)
        if provider:
            query = query.filter(LLMCall.provider == provider)
        if model:
            query = query.filter(LLMCall.model == model)
        if user_id:
            query = query.filter(LLMCall.user_id == user_id)
        if session_id:
            query = query.filter(LLMCall.session_id == session_id)
        if company_id:
            query = query.filter(LLMCall.company_id == company_id)
        if trace_id:
            query = query.filter(LLMCall.trace_id == trace_id)
        if start_date:
            query = query.filter(LLMCall.created_at >= start_date)
        if end_date:
            query = query.filter(LLMCall.created_at <= end_date)

        query = query.order_by(desc(LLMCall.created_at)).offset(offset).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_cost_stats(
        db: AsyncSession,
        user_id: Optional[str] = None,
        company_id: Optional[str] = None,
        days: int = 30
    ) -> Dict:
        """Get cost statistics for LLM calls."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        query = select(LLMCall).filter(LLMCall.created_at >= cutoff_date)

        if user_id:
            query = query.filter(LLMCall.user_id == user_id)
        if company_id:
            query = query.filter(LLMCall.company_id == company_id)

        result = await db.execute(query)
        calls = list(result.scalars().all())

        total_cost = sum(c.estimated_cost or 0 for c in calls)
        total_tokens = sum(c.total_tokens or 0 for c in calls)
        total_calls = len(calls)
        successful_calls = len([c for c in calls if c.status == LLMCallStatusEnum.SUCCESS])
        failed_calls = len([c for c in calls if c.status == LLMCallStatusEnum.ERROR])

        # Group by call type
        by_type = {}
        for call in calls:
            type_key = call.call_type.value
            if type_key not in by_type:
                by_type[type_key] = {'count': 0, 'cost': 0, 'tokens': 0}
            by_type[type_key]['count'] += 1
            by_type[type_key]['cost'] += call.estimated_cost or 0
            by_type[type_key]['tokens'] += call.total_tokens or 0

        # Group by model
        by_model = {}
        for call in calls:
            if call.model not in by_model:
                by_model[call.model] = {'count': 0, 'cost': 0, 'tokens': 0}
            by_model[call.model]['count'] += 1
            by_model[call.model]['cost'] += call.estimated_cost or 0
            by_model[call.model]['tokens'] += call.total_tokens or 0

        return {
            'total_calls': total_calls,
            'successful_calls': successful_calls,
            'failed_calls': failed_calls,
            'total_cost': round(total_cost, 4),
            'total_tokens': total_tokens,
            'avg_cost_per_call': round(total_cost / total_calls, 4) if total_calls > 0 else 0,
            'by_call_type': by_type,
            'by_model': by_model,
            'period_days': days
        }

    @staticmethod
    async def get_performance_stats(
        db: AsyncSession,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        days: int = 7
    ) -> Dict:
        """Get performance statistics for LLM calls."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        query = select(LLMCall).filter(
            LLMCall.created_at >= cutoff_date,
            LLMCall.status == LLMCallStatusEnum.SUCCESS,
            LLMCall.latency_ms.isnot(None)
        )

        if provider:
            query = query.filter(LLMCall.provider == provider)
        if model:
            query = query.filter(LLMCall.model == model)

        result = await db.execute(query)
        calls = list(result.scalars().all())

        if not calls:
            return {
                'total_calls': 0,
                'avg_latency_ms': 0,
                'min_latency_ms': 0,
                'max_latency_ms': 0,
                'p50_latency_ms': 0,
                'p95_latency_ms': 0,
                'p99_latency_ms': 0
            }

        latencies = sorted([c.latency_ms for c in calls if c.latency_ms])
        
        def percentile(data, p):
            k = (len(data) - 1) * p
            f = int(k)
            c = f + 1 if c < len(data) else f
            return data[f] + (k - f) * (data[c] - data[f]) if c < len(data) else data[f]

        return {
            'total_calls': len(calls),
            'avg_latency_ms': int(sum(latencies) / len(latencies)),
            'min_latency_ms': min(latencies),
            'max_latency_ms': max(latencies),
            'p50_latency_ms': int(percentile(latencies, 0.50)),
            'p95_latency_ms': int(percentile(latencies, 0.95)),
            'p99_latency_ms': int(percentile(latencies, 0.99))
        }

    @staticmethod
    async def get_calls_by_trace(
        db: AsyncSession,
        trace_id: str
    ) -> List[LLMCall]:
        """Get all LLM calls for a specific trace (for debugging)."""
        result = await db.execute(
            select(LLMCall)
            .filter(LLMCall.trace_id == trace_id)
            .order_by(LLMCall.created_at)
        )
        return list(result.scalars().all())

    @staticmethod
    async def cleanup_old_logs(
        db: AsyncSession,
        days_old: int = 90
    ) -> int:
        """Clean up old LLM call logs (keep for analysis)."""
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        
        result = await db.execute(
            select(LLMCall).filter(LLMCall.created_at < cutoff_date)
        )
        old_calls = result.scalars().all()
        
        deleted_count = 0
        for call in old_calls:
            await db.delete(call)
            deleted_count += 1

        await db.flush()
        logger.info(f"Cleaned up {deleted_count} old LLM call logs")
        return deleted_count

