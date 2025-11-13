"""Company endpoints for managing companies."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query

from back_end.app.api.deps import get_company_service, get_current_user
from back_end.app.services.company_service import CompanyService
from back_end.app.models.user import UserResponse
from back_end.app.models.company import (
    CompanyCreate,
    CompanyUpdate,
    CompanyResponse,
)

router = APIRouter(prefix="/companies", tags=["companies"])


@router.post(
    "/",
    response_model=CompanyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create company",
    description="Create a new company.",
)
async def create_company(
    company_data: CompanyCreate,
    company_service: CompanyService = Depends(get_company_service),
    current_user: UserResponse = Depends(get_current_user),
) -> CompanyResponse:
    """
    Create a new company.
    
    Args:
        company_data: Company creation data
        company_service: Company service for business logic
        current_user: Authenticated user from JWT token
        
    Returns:
        Created company response
        
    Raises:
        HTTPException: If company with the same name already exists
    """
    try:
        company = await company_service.create_company(company_data)
        return company
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create company: {str(e)}",
        )


@router.get(
    "/{company_id}",
    response_model=CompanyResponse,
    status_code=status.HTTP_200_OK,
    summary="Get company by ID",
    description="Retrieve a specific company by its ID.",
)
async def get_company(
    company_id: UUID,
    company_service: CompanyService = Depends(get_company_service),
    current_user: UserResponse = Depends(get_current_user),
) -> CompanyResponse:
    """
    Get a specific company by ID.
    
    Args:
        company_id: Company identifier
        company_service: Company service for business logic
        current_user: Authenticated user from JWT token
        
    Returns:
        Company response
        
    Raises:
        HTTPException: If company not found
    """
    try:
        company = await company_service.get_company(company_id)
        if company is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Company {company_id} not found",
            )
        return company
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve company: {str(e)}",
        )


@router.get(
    "/",
    response_model=List[CompanyResponse],
    status_code=status.HTTP_200_OK,
    summary="Get all companies",
    description="Retrieve all companies with pagination and optional search.",
)
async def get_all_companies(
    skip: int = Query(0, ge=0, description="Number of companies to skip"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of companies to return"),
    search: str = Query(None, description="Search companies by name (case-insensitive)"),
    company_service: CompanyService = Depends(get_company_service),
    current_user: UserResponse = Depends(get_current_user),
) -> List[CompanyResponse]:
    """
    Get all companies with pagination and optional search.
    
    If search parameter is provided, returns companies matching the search term.
    Otherwise, returns all companies with pagination.
    
    Args:
        skip: Number of companies to skip for pagination
        limit: Maximum number of companies to return (1-500)
        search: Optional search term for company name
        company_service: Company service for business logic
        current_user: Authenticated user from JWT token
        
    Returns:
        List of company responses
    """
    try:
        if search:
            # Search companies by name
            companies = await company_service.search_companies(
                name_pattern=search,
                limit=limit,
            )
        else:
            # Get all companies with pagination
            companies = await company_service.get_all_companies(
                skip=skip,
                limit=limit,
            )
        return companies
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve companies: {str(e)}",
        )


@router.patch(
    "/{company_id}",
    response_model=CompanyResponse,
    status_code=status.HTTP_200_OK,
    summary="Update company",
    description="Update company information.",
)
async def update_company(
    company_id: UUID,
    company_data: CompanyUpdate,
    company_service: CompanyService = Depends(get_company_service),
    current_user: UserResponse = Depends(get_current_user),
) -> CompanyResponse:
    """
    Update company information.
    
    Args:
        company_id: Company identifier
        company_data: Company update data
        company_service: Company service for business logic
        current_user: Authenticated user from JWT token
        
    Returns:
        Updated company response
        
    Raises:
        HTTPException: If company not found or name conflict
    """
    try:
        updated_company = await company_service.update_company(company_id, company_data)
        if updated_company is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Company {company_id} not found",
            )
        return updated_company
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update company: {str(e)}",
        )


@router.delete(
    "/{company_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete company",
    description="Delete a company and all associated data.",
)
async def delete_company(
    company_id: UUID,
    company_service: CompanyService = Depends(get_company_service),
    current_user: UserResponse = Depends(get_current_user),
) -> None:
    """
    Delete a company and all associated data.
    
    This operation is permanent and cannot be undone.
    
    Args:
        company_id: Company identifier
        company_service: Company service for business logic
        current_user: Authenticated user from JWT token
        
    Raises:
        HTTPException: If company not found
    """
    try:
        result = await company_service.delete_company(company_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Company {company_id} not found",
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete company: {str(e)}",
        )


@router.post(
    "/sync",
    response_model=CompanyResponse,
    status_code=status.HTTP_200_OK,
    summary="Get or create company",
    description="Get existing company by name or create new one.",
)
async def sync_company(
    company_data: CompanyCreate,
    company_service: CompanyService = Depends(get_company_service),
    current_user: UserResponse = Depends(get_current_user),
) -> CompanyResponse:
    """
    Get existing company by name or create new one.
    
    This endpoint is useful for ensuring a company exists without
    failing if it already does.
    
    Args:
        company_data: Company data
        company_service: Company service for business logic
        current_user: Authenticated user from JWT token
        
    Returns:
        Existing or newly created company response
    """
    try:
        company = await company_service.get_or_create_company(company_data)
        return company
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync company: {str(e)}",
        )
