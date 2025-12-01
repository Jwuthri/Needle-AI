"""
Code execution API for running Python analysis code.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import check_rate_limit, get_db
from app.core.security.clerk_auth import ClerkUser, get_current_user
from app.services.code_execution_service import SafeCodeExecutor, validate_code
from app.services.user_dataset_service import UserDatasetService
from app.utils.logging import get_logger
import pandas as pd

logger = get_logger("code_execution_api")

router = APIRouter()


class CodeExecutionRequest(BaseModel):
    """Request to execute Python code."""
    code: str = Field(..., description="Python code to execute")
    dataset_id: str | None = Field(None, description="Optional dataset to pre-load as 'df'")

    class Config:
        json_schema_extra = {
            "example": {
                "code": "df = get_dataset('my_dataset')\nprint(df.head())\nresult = df['rating'].mean()",
                "dataset_id": None
            }
        }


class CodeValidationRequest(BaseModel):
    """Request to validate code without executing."""
    code: str = Field(..., description="Python code to validate")


class CodeExecutionResponse(BaseModel):
    """Response from code execution."""
    success: bool
    output: str
    error: str | None = None
    result: dict | None = None
    execution_time: float
    available_datasets: list[str] = []


class CodeValidationResponse(BaseModel):
    """Response from code validation."""
    valid: bool
    errors: list[str] = []


@router.post("/validate", response_model=CodeValidationResponse)
async def validate_user_code(
    request: CodeValidationRequest,
    current_user: ClerkUser = Depends(get_current_user),
    _rate_limit = Depends(check_rate_limit)
) -> CodeValidationResponse:
    """
    Validate Python code without executing it.
    
    Checks for:
    - Syntax errors
    - Forbidden imports
    - Dangerous function calls
    - Security violations
    """
    errors = validate_code(request.code)
    return CodeValidationResponse(
        valid=len(errors) == 0,
        errors=errors
    )


@router.post("/execute", response_model=CodeExecutionResponse)
async def execute_user_code(
    request: CodeExecutionRequest,
    current_user: ClerkUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _rate_limit = Depends(check_rate_limit)
) -> CodeExecutionResponse:
    """
    Execute Python code in a sandboxed environment.
    
    Available functions:
    - get_dataset(dataset_id) - Load a dataset as pandas DataFrame
    - list_datasets() - List available dataset IDs  
    - dataset_info(dataset_id) - Get schema info about a dataset
    
    Available libraries:
    - pandas (pd), numpy (np), math, statistics
    - datetime, collections, itertools, json, re
    
    Security:
    - No file I/O, network access, or system commands
    - 30 second execution timeout
    - Restricted imports and function calls
    """
    # First validate
    errors = validate_code(request.code)
    if errors:
        return CodeExecutionResponse(
            success=False,
            output="",
            error="Code validation failed:\n" + "\n".join(f"- {e}" for e in errors),
            execution_time=0,
            available_datasets=[]
        )
    
    # Create executor and load user's datasets
    executor = SafeCodeExecutor()
    available_datasets = []
    
    try:
        service = UserDatasetService(db)
        datasets = await service.list_datasets(current_user.id, limit=50, offset=0)
        
        for ds in datasets:
            try:
                data = await service.get_dataset_data(
                    dataset_id=ds.id,
                    user_id=current_user.id,
                    limit=50000,
                    offset=0
                )
                if data and data.get('data'):
                    df = pd.DataFrame(data['data'])
                    executor.add_dataset(ds.id, df)
                    executor.add_dataset(ds.table_name, df)
                    available_datasets.append(ds.id)
                    available_datasets.append(ds.table_name)
            except Exception as e:
                logger.warning(f"Failed to load dataset {ds.id}: {e}")
                continue
                
    except Exception as e:
        logger.error(f"Error loading datasets: {e}")
    
    # Pre-load specific dataset if requested
    code = request.code
    if request.dataset_id and request.dataset_id in executor.datasets:
        code = f"df = get_dataset('{request.dataset_id}')\n" + code
    
    # Execute
    logger.info(f"User {current_user.id} executing code")
    result = executor.execute(code)
    
    return CodeExecutionResponse(
        success=result.success,
        output=result.output,
        error=result.error,
        result=result.result_data if isinstance(result.result_data, dict) else (
            {"value": str(result.result_data)} if result.result_data is not None else None
        ),
        execution_time=result.execution_time,
        available_datasets=list(set(available_datasets))  # Dedupe
    )


@router.get("/help")
async def get_code_execution_help(
    current_user: ClerkUser = Depends(get_current_user)
) -> dict:
    """Get help documentation for code execution."""
    return {
        "description": "Execute Python code for data analysis on your datasets.",
        "available_functions": {
            "get_dataset(dataset_id)": "Load a dataset as pandas DataFrame",
            "list_datasets()": "List available dataset IDs",
            "dataset_info(dataset_id)": "Get schema info about a dataset"
        },
        "available_libraries": [
            "pandas (as pd)",
            "numpy (as np)",
            "math",
            "statistics",
            "datetime",
            "collections",
            "itertools",
            "json",
            "re"
        ],
        "restrictions": [
            "No file I/O operations",
            "No network access",
            "No system commands",
            "30 second execution timeout",
            "Maximum 100KB output"
        ],
        "example": """
# Load a dataset
df = get_dataset("my_dataset_id")

# Basic analysis
print(f"Dataset shape: {df.shape}")
print(f"Columns: {list(df.columns)}")

# Group by analysis
summary = df.groupby('source')['rating'].agg(['mean', 'count'])
print(summary)

# Store result (will be returned in response)
result = summary.to_dict()
"""
    }

