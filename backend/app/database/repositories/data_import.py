"""
DataImport repository for managing user data uploads.
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database.models.data_import import DataImport, ImportStatusEnum, ImportTypeEnum
from app.utils.logging import get_logger

logger = get_logger("data_import_repository")


class DataImportRepository:
    """Repository for DataImport model operations."""

    @staticmethod
    async def create(
        db: AsyncSession,
        company_id: str,
        user_id: str,
        file_path: str,
        original_filename: str,
        import_type: ImportTypeEnum
    ) -> DataImport:
        """Create a new data import."""
        data_import = DataImport(
            company_id=company_id,
            user_id=user_id,
            file_path=file_path,
            original_filename=original_filename,
            import_type=import_type
        )
        db.add(data_import)
        await db.flush()
        await db.refresh(data_import)
        logger.info(f"Created data import: {data_import.id}")
        return data_import

    @staticmethod
    async def get_by_id(db: AsyncSession, import_id: str) -> Optional[DataImport]:
        """Get data import by ID."""
        result = await db.execute(select(DataImport).filter(DataImport.id == import_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def list_user_imports(
        db: AsyncSession,
        user_id: str,
        status: Optional[ImportStatusEnum] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[DataImport]:
        """List user's data imports."""
        query = select(DataImport).filter(DataImport.user_id == user_id)

        if status:
            query = query.filter(DataImport.status == status)

        query = query.order_by(desc(DataImport.created_at)).limit(limit).offset(offset)
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def list_company_imports(
        db: AsyncSession,
        company_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[DataImport]:
        """List imports for a company."""
        result = await db.execute(
            select(DataImport)
            .filter(DataImport.company_id == company_id)
            .order_by(desc(DataImport.created_at))
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    @staticmethod
    async def update_status(
        db: AsyncSession,
        import_id: str,
        status: ImportStatusEnum,
        error_message: Optional[str] = None
    ) -> Optional[DataImport]:
        """Update import status."""
        data_import = await DataImportRepository.get_by_id(db, import_id)
        if not data_import:
            return None

        data_import.status = status
        if error_message:
            data_import.error_message = error_message

        if status == ImportStatusEnum.PROCESSING and not data_import.started_at:
            data_import.started_at = datetime.utcnow()
        elif status in [ImportStatusEnum.COMPLETED, ImportStatusEnum.FAILED]:
            data_import.completed_at = datetime.utcnow()

        await db.flush()
        await db.refresh(data_import)
        return data_import

    @staticmethod
    async def update_progress(
        db: AsyncSession,
        import_id: str,
        rows_imported: int,
        rows_failed: int = 0
    ) -> Optional[DataImport]:
        """Update import progress."""
        data_import = await DataImportRepository.get_by_id(db, import_id)
        if not data_import:
            return None

        data_import.rows_imported = rows_imported
        data_import.rows_failed = rows_failed

        await db.flush()
        await db.refresh(data_import)
        return data_import

    @staticmethod
    async def set_celery_task_id(
        db: AsyncSession,
        import_id: str,
        celery_task_id: str
    ) -> Optional[DataImport]:
        """Set Celery task ID."""
        data_import = await DataImportRepository.get_by_id(db, import_id)
        if not data_import:
            return None

        data_import.celery_task_id = celery_task_id
        await db.flush()
        await db.refresh(data_import)
        return data_import

