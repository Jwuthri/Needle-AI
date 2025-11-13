"""Company service for business logic."""

from typing import Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from back_end.app.database.repositories.company import CompanyRepository
from back_end.app.models.company import (
    CompanyCreate,
    CompanyUpdate,
    CompanyResponse,
)


class CompanyService:
    """Service for managing companies."""

    def __init__(
        self,
        session: AsyncSession,
        company_repo: CompanyRepository,
    ):
        """
        Initialize company service.

        Args:
            session: Database session for transactions
            company_repo: Repository for companies
        """
        self.session = session
        self.company_repo = company_repo

    async def create_company(self, company_data: CompanyCreate) -> CompanyResponse:
        """
        Create a new company.

        Args:
            company_data: Company creation data

        Returns:
            Created company response

        Raises:
            ValueError: If company with the same name already exists
        """
        # Check if company with name already exists
        existing_company = await self.company_repo.get_by_name(company_data.name)
        if existing_company:
            raise ValueError(f"Company with name '{company_data.name}' already exists")

        # Create company
        company = await self.company_repo.create(
            name=company_data.name,
            description=company_data.description,
            website=company_data.website,
        )

        await self.session.commit()
        return CompanyResponse.model_validate(company)

    async def get_company(self, company_id: UUID) -> Optional[CompanyResponse]:
        """
        Get a company by ID.

        Args:
            company_id: Company identifier

        Returns:
            Company response or None if not found
        """
        company = await self.company_repo.get_by_id(company_id)
        if company is None:
            return None
        return CompanyResponse.model_validate(company)

    async def get_company_by_name(self, name: str) -> Optional[CompanyResponse]:
        """
        Get a company by name.

        Args:
            name: Company name

        Returns:
            Company response or None if not found
        """
        company = await self.company_repo.get_by_name(name)
        if company is None:
            return None
        return CompanyResponse.model_validate(company)

    async def search_companies(
        self, name_pattern: str, limit: int = 10
    ) -> List[CompanyResponse]:
        """
        Search companies by name pattern.

        Args:
            name_pattern: Pattern to search for (case-insensitive)
            limit: Maximum number of results

        Returns:
            List of matching companies
        """
        companies = await self.company_repo.search_by_name(name_pattern, limit=limit)
        return [CompanyResponse.model_validate(company) for company in companies]

    async def get_all_companies(
        self, skip: int = 0, limit: int = 100
    ) -> List[CompanyResponse]:
        """
        Get all companies with pagination.

        Args:
            skip: Number of companies to skip
            limit: Maximum number of companies to return

        Returns:
            List of company responses
        """
        companies = await self.company_repo.get_all(skip=skip, limit=limit)
        return [CompanyResponse.model_validate(company) for company in companies]

    async def update_company(
        self, company_id: UUID, company_data: CompanyUpdate
    ) -> Optional[CompanyResponse]:
        """
        Update a company.

        Args:
            company_id: Company identifier
            company_data: Company update data

        Returns:
            Updated company response or None if not found

        Raises:
            ValueError: If updating name to one that already exists
        """
        # Check if company exists
        existing_company = await self.company_repo.get_by_id(company_id)
        if existing_company is None:
            return None

        # Prepare update data (only include non-None fields)
        update_data = company_data.model_dump(exclude_unset=True)
        if not update_data:
            # No fields to update
            return CompanyResponse.model_validate(existing_company)

        # If updating name, check for conflicts
        if "name" in update_data:
            name_conflict = await self.company_repo.get_by_name(update_data["name"])
            if name_conflict and name_conflict.id != company_id:
                raise ValueError(
                    f"Company with name '{update_data['name']}' already exists"
                )

        # Update company
        updated_company = await self.company_repo.update(company_id, **update_data)
        await self.session.commit()

        if updated_company is None:
            return None
        return CompanyResponse.model_validate(updated_company)

    async def delete_company(self, company_id: UUID) -> bool:
        """
        Delete a company.

        Args:
            company_id: Company identifier

        Returns:
            True if deleted, False if not found
        """
        result = await self.company_repo.delete(company_id)
        if result:
            await self.session.commit()
        return result

    async def get_or_create_company(
        self, company_data: CompanyCreate
    ) -> CompanyResponse:
        """
        Get existing company by name or create new one.

        This is useful for scenarios where we want to ensure
        a company exists without failing if it already does.

        Args:
            company_data: Company creation data

        Returns:
            Existing or newly created company response
        """
        # Try to get existing company
        existing_company = await self.company_repo.get_by_name(company_data.name)
        if existing_company:
            return CompanyResponse.model_validate(existing_company)

        # Create new company
        return await self.create_company(company_data)
