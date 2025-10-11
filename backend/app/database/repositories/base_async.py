"""
Async base repository with proper transaction management.
"""

from abc import ABC
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar
from uuid import uuid4

from app.exceptions import DatabaseError, ValidationError
from app.utils.logging import get_logger
from sqlalchemy import and_, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

# Type variables for generic repository
T = TypeVar("T")  # Model type
CreateSchemaType = TypeVar("CreateSchemaType")
UpdateSchemaType = TypeVar("UpdateSchemaType")

logger = get_logger("async_repository")


class AsyncBaseRepository(Generic[T], ABC):
    """
    Async base repository with CRUD operations and transaction management.

    Provides common database operations with proper error handling,
    transaction management, and logging.
    """

    def __init__(self, model: Type[T]):
        self.model = model
        self.model_name = model.__name__

    async def create(
        self,
        session: AsyncSession,
        obj_in: CreateSchemaType,
        **kwargs
    ) -> T:
        """
        Create a new record.

        Args:
            session: Database session
            obj_in: Creation data (Pydantic model or dict)
            **kwargs: Additional fields to set

        Returns:
            Created model instance

        Raises:
            ValidationError: If data is invalid
            DatabaseError: If database operation fails
        """
        try:
            # Convert Pydantic model to dict if necessary
            if hasattr(obj_in, "dict"):
                create_data = obj_in.dict(exclude_unset=True)
            elif isinstance(obj_in, dict):
                create_data = obj_in
            else:
                create_data = obj_in.__dict__

            # Add any additional kwargs
            create_data.update(kwargs)

            # Generate UUID if model has id field and none provided
            if hasattr(self.model, 'id') and 'id' not in create_data:
                create_data['id'] = str(uuid4())

            # Create instance
            db_obj = self.model(**create_data)

            # Add to session and flush to get the ID
            session.add(db_obj)
            await session.flush()
            await session.refresh(db_obj)

            logger.debug(f"Created {self.model_name} with id: {getattr(db_obj, 'id', 'N/A')}")
            return db_obj

        except IntegrityError as e:
            logger.error(f"Integrity error creating {self.model_name}: {e}")
            raise ValidationError(f"Duplicate or invalid data: {str(e)}")
        except Exception as e:
            logger.error(f"Error creating {self.model_name}: {e}")
            raise DatabaseError(f"Failed to create {self.model_name}: {str(e)}")

    async def get_by_id(
        self,
        session: AsyncSession,
        id: Any,
        eager_load: Optional[List[str]] = None
    ) -> Optional[T]:
        """
        Get record by ID with optional eager loading.

        Args:
            session: Database session
            id: Record ID
            eager_load: List of relationship names to eager load

        Returns:
            Model instance or None if not found
        """
        try:
            query = select(self.model).where(self.model.id == id)

            # Add eager loading if specified
            if eager_load:
                for relationship in eager_load:
                    query = query.options(selectinload(getattr(self.model, relationship)))

            result = await session.execute(query)
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(f"Error getting {self.model_name} by id {id}: {e}")
            raise DatabaseError(f"Failed to get {self.model_name}: {str(e)}")

    async def get_by_field(
        self,
        session: AsyncSession,
        field_name: str,
        value: Any,
        eager_load: Optional[List[str]] = None
    ) -> Optional[T]:
        """
        Get record by specific field.

        Args:
            session: Database session
            field_name: Name of the field to filter by
            value: Value to match
            eager_load: List of relationship names to eager load

        Returns:
            Model instance or None if not found
        """
        try:
            field = getattr(self.model, field_name)
            query = select(self.model).where(field == value)

            # Add eager loading if specified
            if eager_load:
                for relationship in eager_load:
                    query = query.options(selectinload(getattr(self.model, relationship)))

            result = await session.execute(query)
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(f"Error getting {self.model_name} by {field_name}={value}: {e}")
            raise DatabaseError(f"Failed to get {self.model_name}: {str(e)}")

    async def list_with_filters(
        self,
        session: AsyncSession,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        desc: bool = False,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        eager_load: Optional[List[str]] = None
    ) -> List[T]:
        """
        List records with filtering, ordering, and pagination.

        Args:
            session: Database session
            filters: Dictionary of field_name: value filters
            order_by: Field name to order by
            desc: Whether to order descending
            limit: Maximum number of records
            offset: Number of records to skip
            eager_load: List of relationship names to eager load

        Returns:
            List of model instances
        """
        try:
            query = select(self.model)

            # Apply filters
            if filters:
                filter_conditions = []
                for field_name, value in filters.items():
                    if hasattr(self.model, field_name):
                        field = getattr(self.model, field_name)
                        if isinstance(value, list):
                            filter_conditions.append(field.in_(value))
                        else:
                            filter_conditions.append(field == value)

                if filter_conditions:
                    query = query.where(and_(*filter_conditions))

            # Apply ordering
            if order_by and hasattr(self.model, order_by):
                order_field = getattr(self.model, order_by)
                if desc:
                    query = query.order_by(order_field.desc())
                else:
                    query = query.order_by(order_field)

            # Apply pagination
            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)

            # Add eager loading if specified
            if eager_load:
                for relationship in eager_load:
                    query = query.options(selectinload(getattr(self.model, relationship)))

            result = await session.execute(query)
            return list(result.scalars().all())

        except Exception as e:
            logger.error(f"Error listing {self.model_name}: {e}")
            raise DatabaseError(f"Failed to list {self.model_name}: {str(e)}")

    async def update(
        self,
        session: AsyncSession,
        id: Any,
        obj_in: UpdateSchemaType,
        **kwargs
    ) -> Optional[T]:
        """
        Update a record by ID.

        Args:
            session: Database session
            id: Record ID
            obj_in: Update data (Pydantic model or dict)
            **kwargs: Additional fields to update

        Returns:
            Updated model instance or None if not found

        Raises:
            ValidationError: If data is invalid
            DatabaseError: If database operation fails
        """
        try:
            # Get existing record
            db_obj = await self.get_by_id(session, id)
            if not db_obj:
                return None

            # Convert Pydantic model to dict if necessary
            if hasattr(obj_in, "dict"):
                update_data = obj_in.dict(exclude_unset=True)
            elif isinstance(obj_in, dict):
                update_data = obj_in
            else:
                update_data = obj_in.__dict__

            # Add any additional kwargs
            update_data.update(kwargs)

            # Update fields
            for field, value in update_data.items():
                if hasattr(db_obj, field):
                    setattr(db_obj, field, value)

            # Update timestamp if model has updated_at field
            if hasattr(db_obj, 'updated_at'):
                from datetime import datetime
                db_obj.updated_at = datetime.utcnow()

            await session.flush()
            await session.refresh(db_obj)

            logger.debug(f"Updated {self.model_name} with id: {id}")
            return db_obj

        except IntegrityError as e:
            logger.error(f"Integrity error updating {self.model_name}: {e}")
            raise ValidationError(f"Duplicate or invalid data: {str(e)}")
        except Exception as e:
            logger.error(f"Error updating {self.model_name}: {e}")
            raise DatabaseError(f"Failed to update {self.model_name}: {str(e)}")

    async def delete(self, session: AsyncSession, id: Any) -> bool:
        """
        Delete a record by ID.

        Args:
            session: Database session
            id: Record ID

        Returns:
            True if deleted, False if not found

        Raises:
            DatabaseError: If database operation fails
        """
        try:
            # Check if record exists
            db_obj = await self.get_by_id(session, id)
            if not db_obj:
                return False

            await session.delete(db_obj)
            await session.flush()

            logger.debug(f"Deleted {self.model_name} with id: {id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting {self.model_name}: {e}")
            raise DatabaseError(f"Failed to delete {self.model_name}: {str(e)}")

    async def count(
        self,
        session: AsyncSession,
        filters: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Count records with optional filtering.

        Args:
            session: Database session
            filters: Dictionary of field_name: value filters

        Returns:
            Number of matching records
        """
        try:
            query = select(func.count(self.model.id))

            # Apply filters
            if filters:
                filter_conditions = []
                for field_name, value in filters.items():
                    if hasattr(self.model, field_name):
                        field = getattr(self.model, field_name)
                        if isinstance(value, list):
                            filter_conditions.append(field.in_(value))
                        else:
                            filter_conditions.append(field == value)

                if filter_conditions:
                    query = query.where(and_(*filter_conditions))

            result = await session.execute(query)
            return result.scalar() or 0

        except Exception as e:
            logger.error(f"Error counting {self.model_name}: {e}")
            raise DatabaseError(f"Failed to count {self.model_name}: {str(e)}")

    async def exists(self, session: AsyncSession, id: Any) -> bool:
        """
        Check if record exists by ID.

        Args:
            session: Database session
            id: Record ID

        Returns:
            True if exists, False otherwise
        """
        try:
            query = select(self.model.id).where(self.model.id == id)
            result = await session.execute(query)
            return result.scalar_one_or_none() is not None

        except Exception as e:
            logger.error(f"Error checking existence of {self.model_name}: {e}")
            raise DatabaseError(f"Failed to check {self.model_name} existence: {str(e)}")

    async def bulk_create(
        self,
        session: AsyncSession,
        objects: List[CreateSchemaType]
    ) -> List[T]:
        """
        Create multiple records efficiently.

        Args:
            session: Database session
            objects: List of creation data

        Returns:
            List of created model instances
        """
        try:
            db_objects = []

            for obj_in in objects:
                # Convert to dict
                if hasattr(obj_in, "dict"):
                    create_data = obj_in.dict(exclude_unset=True)
                elif isinstance(obj_in, dict):
                    create_data = obj_in
                else:
                    create_data = obj_in.__dict__

                # Generate UUID if model has id field and none provided
                if hasattr(self.model, 'id') and 'id' not in create_data:
                    create_data['id'] = str(uuid4())

                db_objects.append(self.model(**create_data))

            # Bulk insert
            session.add_all(db_objects)
            await session.flush()

            # Refresh all objects
            for obj in db_objects:
                await session.refresh(obj)

            logger.debug(f"Bulk created {len(db_objects)} {self.model_name} records")
            return db_objects

        except IntegrityError as e:
            logger.error(f"Integrity error in bulk create {self.model_name}: {e}")
            raise ValidationError(f"Duplicate or invalid data in bulk operation: {str(e)}")
        except Exception as e:
            logger.error(f"Error in bulk create {self.model_name}: {e}")
            raise DatabaseError(f"Failed to bulk create {self.model_name}: {str(e)}")


class AsyncRepositoryMixin:
    """Mixin to add common repository methods to specific repositories."""

    async def find_or_create(
        self,
        session: AsyncSession,
        defaults: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> tuple[T, bool]:
        """
        Find existing record or create new one.

        Returns:
            Tuple of (instance, created) where created is True if new record was created
        """
        # Try to find existing record
        filters = kwargs
        existing = await self.list_with_filters(
            session,
            filters=filters,
            limit=1
        )

        if existing:
            return existing[0], False

        # Create new record
        create_data = kwargs.copy()
        if defaults:
            create_data.update(defaults)

        new_instance = await self.create(session, create_data)
        return new_instance, True
