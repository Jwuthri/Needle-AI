"""User repository for database operations."""

from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from back_end.app.database.models.user import User
from back_end.app.database.repositories.base_async import BaseAsyncRepository


class UserRepository(BaseAsyncRepository[User]):
    """Repository for User model operations."""

    def __init__(self, session: AsyncSession):
        """
        Initialize User repository.

        Args:
            session: Async database session
        """
        super().__init__(User, session)

    async def get_by_clerk_id(self, clerk_user_id: str) -> Optional[User]:
        """
        Get user by Clerk user ID.

        Args:
            clerk_user_id: Clerk user identifier

        Returns:
            User instance or None if not found
        """
        result = await self.session.execute(
            select(User).where(User.clerk_user_id == clerk_user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email address.

        Args:
            email: User email address

        Returns:
            User instance or None if not found
        """
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()
