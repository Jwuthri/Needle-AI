"""User dataset service for business logic."""

from typing import Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from back_end.app.database.repositories.user_dataset import UserDatasetRepository
from back_end.app.database.repositories.user import UserRepository
from back_end.app.models.user_dataset import (
    UserDatasetCreate,
    UserDatasetUpdate,
    UserDatasetResponse,
)


class UserDatasetService:
    """Service for managing user datasets."""

    def __init__(
        self,
        session: AsyncSession,
        user_dataset_repo: UserDatasetRepository,
        user_repo: UserRepository,
    ):
        """
        Initialize user dataset service.

        Args:
            session: Database session for transactions
            user_dataset_repo: Repository for user datasets
            user_repo: Repository for users
        """
        self.session = session
        self.user_dataset_repo = user_dataset_repo
        self.user_repo = user_repo

    async def create_dataset(
        self, dataset_data: UserDatasetCreate
    ) -> UserDatasetResponse:
        """
        Create a new user dataset.

        Args:
            dataset_data: Dataset creation data

        Returns:
            Created dataset response

        Raises:
            ValueError: If user does not exist
        """
        # Verify user exists
        user = await self.user_repo.get_by_id(dataset_data.user_id)
        if user is None:
            raise ValueError(f"User {dataset_data.user_id} not found")

        # Create dataset
        dataset = await self.user_dataset_repo.create(
            user_id=dataset_data.user_id,
            name=dataset_data.name,
            description=dataset_data.description,
            file_path=dataset_data.file_path,
            file_size=dataset_data.file_size,
            row_count=dataset_data.row_count,
            metadata=dataset_data.metadata_,
        )

        await self.session.commit()
        return UserDatasetResponse.model_validate(dataset)

    async def get_dataset(self, dataset_id: UUID) -> Optional[UserDatasetResponse]:
        """
        Get a dataset by ID.

        Args:
            dataset_id: Dataset identifier

        Returns:
            Dataset response or None if not found
        """
        dataset = await self.user_dataset_repo.get_by_id(dataset_id)
        if dataset is None:
            return None
        return UserDatasetResponse.model_validate(dataset)

    async def get_user_datasets(
        self, user_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[UserDatasetResponse]:
        """
        Get all datasets for a user.

        Args:
            user_id: User identifier
            skip: Number of datasets to skip
            limit: Maximum number of datasets to return

        Returns:
            List of dataset responses
        """
        datasets = await self.user_dataset_repo.get_by_user_id(
            user_id, skip=skip, limit=limit
        )
        return [UserDatasetResponse.model_validate(dataset) for dataset in datasets]

    async def search_user_datasets(
        self, user_id: UUID, name_pattern: str
    ) -> List[UserDatasetResponse]:
        """
        Search datasets by name for a user.

        Args:
            user_id: User identifier
            name_pattern: Pattern to search for (case-insensitive)

        Returns:
            List of matching datasets
        """
        datasets = await self.user_dataset_repo.get_by_name(user_id, name_pattern)
        return [UserDatasetResponse.model_validate(dataset) for dataset in datasets]

    async def update_dataset(
        self, dataset_id: UUID, dataset_data: UserDatasetUpdate
    ) -> Optional[UserDatasetResponse]:
        """
        Update a dataset.

        Args:
            dataset_id: Dataset identifier
            dataset_data: Dataset update data

        Returns:
            Updated dataset response or None if not found
        """
        # Check if dataset exists
        existing_dataset = await self.user_dataset_repo.get_by_id(dataset_id)
        if existing_dataset is None:
            return None

        # Prepare update data (only include non-None fields)
        update_data = dataset_data.model_dump(exclude_unset=True)
        if not update_data:
            # No fields to update
            return UserDatasetResponse.model_validate(existing_dataset)

        # Update dataset
        updated_dataset = await self.user_dataset_repo.update(dataset_id, **update_data)
        await self.session.commit()

        if updated_dataset is None:
            return None
        return UserDatasetResponse.model_validate(updated_dataset)

    async def delete_dataset(self, dataset_id: UUID) -> bool:
        """
        Delete a dataset.

        Args:
            dataset_id: Dataset identifier

        Returns:
            True if deleted, False if not found
        """
        result = await self.user_dataset_repo.delete(dataset_id)
        if result:
            await self.session.commit()
        return result

    async def get_dataset_stats(self, user_id: UUID) -> dict:
        """
        Get statistics about user's datasets.

        Args:
            user_id: User identifier

        Returns:
            Dictionary with dataset statistics
        """
        datasets = await self.user_dataset_repo.get_by_user_id(user_id, skip=0, limit=1000)

        total_datasets = len(datasets)
        total_size = sum(d.file_size or 0 for d in datasets)
        total_rows = sum(d.row_count or 0 for d in datasets)

        return {
            "total_datasets": total_datasets,
            "total_size_bytes": total_size,
            "total_rows": total_rows,
            "average_size_bytes": total_size // total_datasets if total_datasets > 0 else 0,
            "average_rows": total_rows // total_datasets if total_datasets > 0 else 0,
        }
