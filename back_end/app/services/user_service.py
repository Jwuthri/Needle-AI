"""User service for business logic."""

from typing import Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from back_end.app.database.repositories.user import UserRepository
from back_end.app.models.user import (
    UserCreate,
    UserUpdate,
    UserResponse,
)


class UserService:
    """Service for managing users."""

    def __init__(
        self,
        session: AsyncSession,
        user_repo: UserRepository,
    ):
        """
        Initialize user service.

        Args:
            session: Database session for transactions
            user_repo: Repository for users
        """
        self.session = session
        self.user_repo = user_repo

    async def create_user(self, user_data: UserCreate) -> UserResponse:
        """
        Create a new user.

        Args:
            user_data: User creation data

        Returns:
            Created user response

        Raises:
            ValueError: If user with clerk_user_id or email already exists
        """
        # Check if user with clerk_user_id already exists
        existing_user = await self.user_repo.get_by_clerk_id(user_data.clerk_user_id)
        if existing_user:
            raise ValueError(
                f"User with clerk_user_id {user_data.clerk_user_id} already exists"
            )

        # Check if user with email already exists
        existing_email = await self.user_repo.get_by_email(user_data.email)
        if existing_email:
            raise ValueError(f"User with email {user_data.email} already exists")

        # Create user
        user = await self.user_repo.create(
            clerk_user_id=user_data.clerk_user_id,
            email=user_data.email,
            full_name=user_data.full_name,
            is_active=True,
        )

        await self.session.commit()
        return UserResponse.model_validate(user)

    async def get_user(self, user_id: UUID) -> Optional[UserResponse]:
        """
        Get a user by ID.

        Args:
            user_id: User identifier

        Returns:
            User response or None if not found
        """
        user = await self.user_repo.get_by_id(user_id)
        if user is None:
            return None
        return UserResponse.model_validate(user)

    async def get_user_by_clerk_id(self, clerk_user_id: str) -> Optional[UserResponse]:
        """
        Get a user by Clerk user ID.

        Args:
            clerk_user_id: Clerk user identifier

        Returns:
            User response or None if not found
        """
        user = await self.user_repo.get_by_clerk_id(clerk_user_id)
        if user is None:
            return None
        return UserResponse.model_validate(user)

    async def get_user_by_email(self, email: str) -> Optional[UserResponse]:
        """
        Get a user by email address.

        Args:
            email: User email address

        Returns:
            User response or None if not found
        """
        user = await self.user_repo.get_by_email(email)
        if user is None:
            return None
        return UserResponse.model_validate(user)

    async def get_all_users(
        self, skip: int = 0, limit: int = 100
    ) -> List[UserResponse]:
        """
        Get all users with pagination.

        Args:
            skip: Number of users to skip
            limit: Maximum number of users to return

        Returns:
            List of user responses
        """
        users = await self.user_repo.get_all(skip=skip, limit=limit)
        return [UserResponse.model_validate(user) for user in users]

    async def update_user(
        self, user_id: UUID, user_data: UserUpdate
    ) -> Optional[UserResponse]:
        """
        Update a user.

        Args:
            user_id: User identifier
            user_data: User update data

        Returns:
            Updated user response or None if not found
        """
        # Check if user exists
        existing_user = await self.user_repo.get_by_id(user_id)
        if existing_user is None:
            return None

        # Prepare update data (only include non-None fields)
        update_data = user_data.model_dump(exclude_unset=True)
        if not update_data:
            # No fields to update
            return UserResponse.model_validate(existing_user)

        # Update user
        updated_user = await self.user_repo.update(user_id, **update_data)
        await self.session.commit()

        if updated_user is None:
            return None
        return UserResponse.model_validate(updated_user)

    async def delete_user(self, user_id: UUID) -> bool:
        """
        Delete a user.

        Args:
            user_id: User identifier

        Returns:
            True if deleted, False if not found
        """
        result = await self.user_repo.delete(user_id)
        if result:
            await self.session.commit()
        return result

    async def get_or_create_user(self, user_data: UserCreate) -> UserResponse:
        """
        Get existing user by clerk_user_id or create new one.

        This is useful for authentication flows where we want to ensure
        a user exists without failing if they already do.

        Args:
            user_data: User creation data

        Returns:
            Existing or newly created user response
        """
        # Try to get existing user
        existing_user = await self.user_repo.get_by_clerk_id(user_data.clerk_user_id)
        if existing_user:
            return UserResponse.model_validate(existing_user)

        # Create new user
        return await self.create_user(user_data)
