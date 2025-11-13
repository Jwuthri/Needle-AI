"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config.settings import get_settings
from app.database.session import engine
from app.utils.logging import setup_logging


# Get application settings
settings = get_settings()

# Set up logging
logger = setup_logging(
    log_level=settings.log_level,
    use_rich=settings.use_rich_logging,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Lifespan context manager for application startup and shutdown.
    
    Handles:
    - Database connection initialization
    - Resource cleanup on shutdown
    
    Args:
        app: FastAPI application instance
        
    Yields:
        None: Control during application runtime
    """
    # Startup
    logger.info(
        f"[bold green]Starting {settings.app_name} v{settings.app_version}[/bold green]"
    )
    logger.info(f"Environment: [cyan]{settings.environment}[/cyan]")
    logger.info(f"Debug mode: [yellow]{settings.debug}[/yellow]")
    logger.info(f"Database: [blue]{settings.database_name}[/blue]")
    
    # Test database connection
    try:
        async with engine.begin() as conn:
            logger.info("[bold green]✓[/bold green] Database connection established")
    except Exception as e:
        logger.error(f"[bold red]✗[/bold red] Database connection failed: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("[bold yellow]Shutting down application...[/bold yellow]")
    await engine.dispose()
    logger.info("[bold green]✓[/bold green] Database connections closed")
    logger.info("[bold green]Application shutdown complete[/bold green]")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Simplified backend system for chat functionality with LLM integration",
    debug=settings.debug,
    lifespan=lifespan,
)

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    """
    Root endpoint providing basic API information.
    
    Returns:
        dict: API information including name, version, and status
    """
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "environment": settings.environment,
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
