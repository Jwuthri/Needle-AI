"""User dataset endpoints for managing user datasets."""

from typing import List, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query

from back_end.app.api.deps import get_user_dataset_service, get_current_user
from back_end.app.services.user_dataset_service import UserDatasetService
from back_end.app.models.user import UserResponse
from back_end.app.models.user_dataset import (
    UserDatasetCreate,
    UserDatasetUpdate,
    UserDatasetResponse,
)

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.post(
    "/",
    response_model=UserDatasetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create user dataset",
    description="Create a new user dataset.",
)
async def create_dataset(
    dataset_data: UserDatasetCreate,
    dataset_service: UserDatasetService = Depends(get_user_dataset_service),
    current_user: UserResponse = Depends(get_current_user),
) -> UserDatasetResponse:
    """
    Create a new user dataset.
    
    The dataset will be associated with the authenticated user.
    
    Args:
        dataset_data: Dataset creation data
        dataset_service: User dataset service for business logic
        current_user: Authenticated user from JWT token
        
    Returns:
        Created dataset response
        
    Raises:
        HTTPException: If user tries to create dataset for another user
    """
    # Ensure user can only create datasets for themselves
    if dataset_data.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only create datasets for yourself",
        )
    
    try:
        dataset = await dataset_service.create_dataset(dataset_data)
        return dataset
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create dataset: {str(e)}",
        )


@router.get(
    "/{dataset_id}",
    response_model=UserDatasetResponse,
    status_code=status.HTTP_200_OK,
    summary="Get dataset by ID",
    description="Retrieve a specific dataset by its ID.",
)
async def get_dataset(
    dataset_id: UUID,
    dataset_service: UserDatasetService = Depends(get_user_dataset_service),
    current_user: UserResponse = Depends(get_current_user),
) -> UserDatasetResponse:
    """
    Get a specific dataset by ID.
    
    Users can only access their own datasets.
    
    Args:
        dataset_id: Dataset identifier
        dataset_service: User dataset service for business logic
        current_user: Authenticated user from JWT token
        
    Returns:
        Dataset response
        
    Raises:
        HTTPException: If dataset not found or access denied
    """
    try:
        dataset = await dataset_service.get_dataset(dataset_id)
        if dataset is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dataset {dataset_id} not found",
            )
        
        # Verify user owns this dataset
        if dataset.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this dataset",
            )
        
        return dataset
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve dataset: {str(e)}",
        )


@router.get(
    "/",
    response_model=List[UserDatasetResponse],
    status_code=status.HTTP_200_OK,
    summary="Get user's datasets",
    description="Retrieve all datasets for the authenticated user.",
)
async def get_user_datasets(
    skip: int = Query(0, ge=0, description="Number of datasets to skip"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of datasets to return"),
    search: str = Query(None, description="Search datasets by name (case-insensitive)"),
    dataset_service: UserDatasetService = Depends(get_user_dataset_service),
    current_user: UserResponse = Depends(get_current_user),
) -> List[UserDatasetResponse]:
    """
    Get all datasets for the authenticated user.
    
    If search parameter is provided, returns datasets matching the search term.
    Otherwise, returns all datasets with pagination.
    
    Args:
        skip: Number of datasets to skip for pagination
        limit: Maximum number of datasets to return (1-500)
        search: Optional search term for dataset name
        dataset_service: User dataset service for business logic
        current_user: Authenticated user from JWT token
        
    Returns:
        List of dataset responses
    """
    try:
        if search:
            # Search datasets by name
            datasets = await dataset_service.search_user_datasets(
                user_id=current_user.id,
                name_pattern=search,
            )
        else:
            # Get all datasets with pagination
            datasets = await dataset_service.get_user_datasets(
                user_id=current_user.id,
                skip=skip,
                limit=limit,
            )
        return datasets
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve datasets: {str(e)}",
        )


@router.patch(
    "/{dataset_id}",
    response_model=UserDatasetResponse,
    status_code=status.HTTP_200_OK,
    summary="Update dataset",
    description="Update dataset information.",
)
async def update_dataset(
    dataset_id: UUID,
    dataset_data: UserDatasetUpdate,
    dataset_service: UserDatasetService = Depends(get_user_dataset_service),
    current_user: UserResponse = Depends(get_current_user),
) -> UserDatasetResponse:
    """
    Update dataset information.
    
    Users can only update their own datasets.
    
    Args:
        dataset_id: Dataset identifier
        dataset_data: Dataset update data
        dataset_service: User dataset service for business logic
        current_user: Authenticated user from JWT token
        
    Returns:
        Updated dataset response
        
    Raises:
        HTTPException: If dataset not found or access denied
    """
    try:
        # Verify dataset exists and user owns it
        existing_dataset = await dataset_service.get_dataset(dataset_id)
        if existing_dataset is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dataset {dataset_id} not found",
            )
        
        if existing_dataset.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to update this dataset",
            )
        
        # Update dataset
        updated_dataset = await dataset_service.update_dataset(dataset_id, dataset_data)
        if updated_dataset is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dataset {dataset_id} not found",
            )
        return updated_dataset
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update dataset: {str(e)}",
        )


@router.delete(
    "/{dataset_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete dataset",
    description="Delete a dataset and all associated data.",
)
async def delete_dataset(
    dataset_id: UUID,
    dataset_service: UserDatasetService = Depends(get_user_dataset_service),
    current_user: UserResponse = Depends(get_current_user),
) -> None:
    """
    Delete a dataset and all associated data.
    
    This operation is permanent and cannot be undone.
    Users can only delete their own datasets.
    
    Args:
        dataset_id: Dataset identifier
        dataset_service: User dataset service for business logic
        current_user: Authenticated user from JWT token
        
    Raises:
        HTTPException: If dataset not found or access denied
    """
    try:
        # Verify dataset exists and user owns it
        existing_dataset = await dataset_service.get_dataset(dataset_id)
        if existing_dataset is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dataset {dataset_id} not found",
            )
        
        if existing_dataset.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to delete this dataset",
            )
        
        # Delete dataset
        result = await dataset_service.delete_dataset(dataset_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dataset {dataset_id} not found",
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete dataset: {str(e)}",
        )


@router.get(
    "/stats/summary",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Get dataset statistics",
    description="Get statistics about the user's datasets.",
)
async def get_dataset_stats(
    dataset_service: UserDatasetService = Depends(get_user_dataset_service),
    current_user: UserResponse = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get statistics about the user's datasets.
    
    Returns aggregate information like total datasets, total size, etc.
    
    Args:
        dataset_service: User dataset service for business logic
        current_user: Authenticated user from JWT token
        
    Returns:
        Dictionary with dataset statistics
    """
    try:
        stats = await dataset_service.get_dataset_stats(current_user.id)
        return stats
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve dataset statistics: {str(e)}",
        )
