"""
Configuration management for NeedleAi.

This module provides centralized configuration with environment-specific settings,
secrets management, and comprehensive validation.
"""

import os
from functools import lru_cache
from typing import Optional

from app.core.config.environments import (
    create_environment_config,
    get_environment_settings,
)
from app.core.config.settings import Settings as BaseSettings
from app.core.config.validation import setup_config_validation
from app.utils.logging import get_logger

logger = get_logger("config")

# Re-export for backward compatibility
Settings = BaseSettings


@lru_cache()
def get_settings(environment: Optional[str] = None, validate: bool = True) -> Settings:
    """
    Get cached application settings for the specified environment.

    Args:
        environment: Environment name (development, testing, staging, production)
        validate: Whether to run configuration validation

    Returns:
        Configured Settings instance
    """
    if environment is None:
        environment = os.getenv("ENVIRONMENT", "development")

    logger.info(f"Loading configuration for environment: {environment}")

    try:
        # Get environment-specific settings class
        settings_class = get_environment_settings(environment)

        # Create settings instance
        settings = settings_class()

        # Run validation if requested
        if validate:
            try:
                validation_report = setup_config_validation(settings)

                # Log validation summary
                if validation_report.get("errors"):
                    logger.warning(f"Configuration has {len(validation_report['errors'])} errors")
                if validation_report.get("warnings"):
                    logger.info(f"Configuration has {len(validation_report['warnings'])} warnings")

            except Exception as e:
                logger.error(f"Configuration validation failed: {e}")
                if environment == "production":
                    raise

        logger.info(f"Configuration loaded successfully for {environment}")
        return settings

    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        # Fallback to development settings if possible
        if environment != "development":
            logger.warning("Falling back to development configuration")
            return get_settings("development", validate=False)
        raise


def get_development_settings() -> Settings:
    """Get development settings without caching."""
    return create_environment_config("development")


def get_testing_settings() -> Settings:
    """Get testing settings without caching."""
    return create_environment_config("testing")


def get_production_settings() -> Settings:
    """Get production settings without caching."""
    return create_environment_config("production")


def refresh_settings() -> Settings:
    """Refresh cached settings (mainly for testing)."""
    get_settings.cache_clear()
    return get_settings()


# Legacy compatibility
def validate_settings(settings: Settings) -> bool:
    """Validate settings (legacy compatibility function)."""
    try:
        setup_config_validation(settings)
        return True
    except Exception:
        return False
