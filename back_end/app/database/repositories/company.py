"""Company repository for database operations."""

from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from back_end.app.database.models.company import Company
from back_end.app.database.repositories.base_async import BaseAsyncRepository


class CompanyRepository(BaseAsyncRepository[Company]):
    """Repository for Company model operations."""

    def __init__(self, session: AsyncSession):
        """
        Initialize Company repository.

        Args:
            session: Async database session
        """
        super().__init__(Company, session)

    async def get_by_name(self, name: str) -> Optional[Company]:
        """
        Get company by name.

        Args:
            name: Company name

        Returns:
            Company instance or None if not found
        """
        result = await self.session.execute(
            select(Company).where(Company.name == name)
        )
        return result.scalar_one_or_none()

    async def search_by_name(self, name_pattern: str, limit: int = 10) -> List[Company]:
        """
        Search companies by name pattern.

        Args:
            name_pattern: Pattern to search for (case-insensitive)
            limit: Maximum number of results

        Returns:
            List of matching companies
        """
        result = await self.session.execute(
            select(Company)
            .where(Company.name.ilike(f"%{name_pattern}%"))
            .limit(limit)
        )
        return list(result.scalars().all())
