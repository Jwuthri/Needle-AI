"""LLMCall repository for database operations."""

from typing import List, Optional
from datetime import datetime
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from back_end.app.database.models.llm_call import LLMCall
from back_end.app.database.repositories.base_async import BaseAsyncRepository


class LLMCallRepository(BaseAsyncRepository[LLMCall]):
    """Repository for LLMCall model operations."""

    def __init__(self, session: AsyncSession):
        """
        Initialize LLMCall repository.

        Args:
            session: Async database session
        """
        super().__init__(LLMCall, session)

    async def get_by_provider(
        self, provider: str, skip: int = 0, limit: int = 100
    ) -> List[LLMCall]:
        """
        Get LLM calls by provider.

        Args:
            provider: LLM provider name
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of LLM calls for the provider
        """
        result = await self.session.execute(
            select(LLMCall)
            .where(LLMCall.provider == provider)
            .order_by(LLMCall.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_model(
        self, model: str, skip: int = 0, limit: int = 100
    ) -> List[LLMCall]:
        """
        Get LLM calls by model.

        Args:
            model: LLM model name
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of LLM calls for the model
        """
        result = await self.session.execute(
            select(LLMCall)
            .where(LLMCall.model == model)
            .order_by(LLMCall.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_status(
        self, status: str, skip: int = 0, limit: int = 100
    ) -> List[LLMCall]:
        """
        Get LLM calls by status.

        Args:
            status: Call status ('success' or 'error')
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of LLM calls with specified status
        """
        result = await self.session.execute(
            select(LLMCall)
            .where(LLMCall.status == status)
            .order_by(LLMCall.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        skip: int = 0,
        limit: int = 100
    ) -> List[LLMCall]:
        """
        Get LLM calls within a date range.

        Args:
            start_date: Start of date range
            end_date: End of date range
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of LLM calls within the date range
        """
        result = await self.session.execute(
            select(LLMCall)
            .where(
                LLMCall.created_at >= start_date,
                LLMCall.created_at <= end_date
            )
            .order_by(LLMCall.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_total_cost(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        provider: Optional[str] = None
    ) -> float:
        """
        Calculate total cost of LLM calls with optional filters.

        Args:
            start_date: Optional start date filter
            end_date: Optional end date filter
            provider: Optional provider filter

        Returns:
            Total cost as float
        """
        query = select(func.sum(LLMCall.cost))

        if start_date:
            query = query.where(LLMCall.created_at >= start_date)
        if end_date:
            query = query.where(LLMCall.created_at <= end_date)
        if provider:
            query = query.where(LLMCall.provider == provider)

        result = await self.session.execute(query)
        total = result.scalar_one()
        return float(total) if total else 0.0

    async def get_total_tokens(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        provider: Optional[str] = None
    ) -> int:
        """
        Calculate total tokens used with optional filters.

        Args:
            start_date: Optional start date filter
            end_date: Optional end date filter
            provider: Optional provider filter

        Returns:
            Total tokens as integer
        """
        query = select(func.sum(LLMCall.total_tokens))

        if start_date:
            query = query.where(LLMCall.created_at >= start_date)
        if end_date:
            query = query.where(LLMCall.created_at <= end_date)
        if provider:
            query = query.where(LLMCall.provider == provider)

        result = await self.session.execute(query)
        total = result.scalar_one()
        return int(total) if total else 0
