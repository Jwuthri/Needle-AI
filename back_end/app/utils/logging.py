"""Logging utilities with Rich formatting support."""

import logging
import sys
from typing import Optional

from rich.console import Console
from rich.logging import RichHandler


# Global console instance for Rich formatting
console = Console()


def setup_logging(
    log_level: str = "INFO",
    use_rich: bool = True,
    logger_name: Optional[str] = None,
) -> logging.Logger:
    """
    Configure application logging with optional Rich formatting.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        use_rich: Whether to use Rich formatting for console output
        logger_name: Name for the logger instance (defaults to 'needleai')

    Returns:
        logging.Logger: Configured logger instance

    Example:
        >>> logger = setup_logging(log_level="DEBUG", use_rich=True)
        >>> logger.info("[bold green]Application started[/bold green]")
        >>> logger.error("[bold red]Error occurred[/bold red]", exc_info=True)
    """
    logger_name = logger_name or "needleai"

    # Create handler based on configuration
    if use_rich:
        handler = RichHandler(
            console=console,
            rich_tracebacks=True,
            tracebacks_show_locals=True,
            markup=True,
            show_time=True,
            show_level=True,
            show_path=True,
        )
        log_format = "%(message)s"
    else:
        handler = logging.StreamHandler(sys.stdout)
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Configure basic logging
    logging.basicConfig(
        level=log_level.upper(),
        format=log_format,
        datefmt="[%X]",
        handlers=[handler],
        force=True,
    )

    # Get or create logger
    logger = logging.getLogger(logger_name)
    logger.setLevel(log_level.upper())

    # Set third-party loggers to WARNING to reduce noise
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("alembic").setLevel(logging.WARNING)

    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get a logger instance with the specified name.

    Args:
        name: Logger name (defaults to 'needleai')

    Returns:
        logging.Logger: Logger instance
    """
    return logging.getLogger(name or "needleai")
