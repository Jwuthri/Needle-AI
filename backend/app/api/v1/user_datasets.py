"""
User datasets API endpoints for CSV upload and management.
"""

from typing import List, Optional

from app.config import get_settings
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import check_rate_limit, get_db
from app.core.security.clerk_auth import ClerkUser, require_current_user
from app.models.user_dataset import (
    UserDatasetListResponse,
    UserDatasetResponse,
    UserDatasetUploadResponse,
)
from app.services.user_dataset_service import UserDatasetService
from app.utils.logging import get_logger

logger = get_logger("user_datasets_api")

router = APIRouter()


def get_user_dataset_service(db: AsyncSession = Depends(get_db)) -> UserDatasetService:
    """Get user dataset service instance."""
    return UserDatasetService(db)


@router.post("/upload", response_model=UserDatasetUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_csv(
    file: UploadFile = File(..., description="CSV file to upload"),
    table_name: Optional[str] = Form(None, description="Name for the dataset table (optional, will be auto-generated if not provided)"),
    current_user: ClerkUser = Depends(require_current_user),
    db: AsyncSession = Depends(get_db),
    service: UserDatasetService = Depends(get_user_dataset_service),
    _rate_limit = Depends(check_rate_limit)
) -> UserDatasetUploadResponse:
    """
    Upload a CSV file and create a dynamic table with EDA metadata.
    
    The CSV will be parsed, stored in a dynamic table named `__user_{user_id}_{table_name}`,
    and LLM-generated EDA metadata will be created.
    
    If table_name is not provided, an LLM will generate a descriptive name based on the CSV content.
    """
    settings = get_settings()
    
    # Validate file type
    if not file.filename or not file.filename.lower().endswith('.csv'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV files are supported"
        )
    
    # Validate file size
    file_content = await file.read()
    if len(file_content) > settings.max_upload_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds maximum allowed size of {settings.max_upload_size} bytes"
        )
    
    try:
        result = await service.upload_csv(
            user_id=current_user.id,
            file_content=file_content,
            table_name=table_name.strip() if table_name else None,
            filename=file.filename or "unknown.csv"
        )
        
        logger.info(f"Successfully uploaded CSV for user {current_user.id}: {result.get('table_name', 'auto-generated')}")
        
        return UserDatasetUploadResponse(**result)
        
    except ValueError as e:
        logger.error(f"Validation error uploading CSV: {e}")
        error_message = str(e)
        # Provide more specific error for duplicate table names
        if "already exists" in error_message.lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=error_message
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_message
        )
    except Exception as e:
        logger.error(f"Error uploading CSV: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload CSV: {str(e)}"
        )


@router.get("/", response_model=UserDatasetListResponse)
async def list_datasets(
    current_user: ClerkUser = Depends(require_current_user),
    db: AsyncSession = Depends(get_db),
    service: UserDatasetService = Depends(get_user_dataset_service),
    limit: int = 50,
    offset: int = 0,
    _rate_limit = Depends(check_rate_limit)
) -> UserDatasetListResponse:
    """List all datasets for the current user."""
    try:
        datasets = await service.list_datasets(
            user_id=current_user.id,
            limit=limit,
            offset=offset
        )
        
        from app.database.repositories.user_dataset import UserDatasetRepository
        total = await UserDatasetRepository.count_user_datasets(db, current_user.id)
        
        return UserDatasetListResponse(
            datasets=[UserDatasetResponse(**ds) for ds in datasets],
            total=total
        )
        
    except Exception as e:
        logger.error(f"Error listing datasets: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list datasets: {str(e)}"
        )


@router.get("/{dataset_id}", response_model=UserDatasetResponse)
async def get_dataset(
    dataset_id: str,
    current_user: ClerkUser = Depends(require_current_user),
    db: AsyncSession = Depends(get_db),
    service: UserDatasetService = Depends(get_user_dataset_service),
    _rate_limit = Depends(check_rate_limit)
) -> UserDatasetResponse:
    """Get a specific dataset by ID."""
    try:
        dataset = await service.get_dataset(dataset_id, current_user.id)
        
        if not dataset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dataset not found"
            )
        
        return UserDatasetResponse(**dataset)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting dataset: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get dataset: {str(e)}"
        )


@router.get("/{dataset_id}/data")
async def get_dataset_data(
    dataset_id: str,
    current_user: ClerkUser = Depends(require_current_user),
    db: AsyncSession = Depends(get_db),
    service: UserDatasetService = Depends(get_user_dataset_service),
    limit: int = 100,
    offset: int = 0,
    _rate_limit = Depends(check_rate_limit)
):
    """Get data from a dataset's dynamic table."""
    try:
        data = await service.get_dataset_data(
            dataset_id=dataset_id,
            user_id=current_user.id,
            limit=min(limit, 1000),  # Cap at 1000 rows
            offset=offset
        )
        
        if data is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dataset not found"
            )
        
        return data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting dataset data: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get dataset data: {str(e)}"
        )

