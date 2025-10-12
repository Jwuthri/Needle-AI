"""
Company repository for product review analysis.
"""

from typing import List, Optional

from sqlalchemy import desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database.models.company import Company
from app.utils.logging import get_logger

logger = get_logger("company_repository")


class CompanyRepository:
    """Repository for Company model operations."""

    @staticmethod
    async def create(
        db: AsyncSession,
        name: str,
        created_by: str,
        domain: Optional[str] = None,
        industry: Optional[str] = None,
        description: Optional[str] = None
    ) -> Company:
        """Create a new company."""
        company = Company(
            name=name,
            domain=domain,
            industry=industry,
            description=description,
            created_by=created_by
        )
        db.add(company)
        await db.flush()
        await db.refresh(company)
        logger.info(f"Created company: {company.id} - {company.name}")
        return company

    @staticmethod
    async def get_by_id(db: AsyncSession, company_id: str) -> Optional[Company]:
        """Get company by ID."""
        result = await db.execute(select(Company).filter(Company.id == company_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_domain(db: AsyncSession, domain: str) -> Optional[Company]:
        """Get company by domain."""
        result = await db.execute(select(Company).filter(Company.domain == domain))
        return result.scalar_one_or_none()

    @staticmethod
    async def list_user_companies(
        db: AsyncSession,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Company]:
        """List user's companies."""
        result = await db.execute(
            select(Company)
            .filter(Company.created_by == user_id)
            .order_by(desc(Company.created_at))
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    @staticmethod
    async def update(
        db: AsyncSession,
        company_id: str,
        **kwargs
    ) -> Optional[Company]:
        """Update company."""
        company = await CompanyRepository.get_by_id(db, company_id)
        if not company:
            return None

        for key, value in kwargs.items():
            if hasattr(company, key) and value is not None:
                setattr(company, key, value)

        await db.flush()
        await db.refresh(company)
        return company

    @staticmethod
    async def delete(db: AsyncSession, company_id: str) -> bool:
        """Delete company."""
        company = await CompanyRepository.get_by_id(db, company_id)
        if not company:
            return False

        await db.delete(company)
        await db.flush()
        logger.info(f"Deleted company: {company_id}")
        return True

    @staticmethod
    async def count_user_companies(db: AsyncSession, user_id: str) -> int:
        """Count user's companies."""
        result = await db.execute(
            select(Company).filter(Company.created_by == user_id)
        )
        return len(list(result.scalars().all()))

