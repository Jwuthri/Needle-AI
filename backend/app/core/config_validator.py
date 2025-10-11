"""
Configuration validation utilities for NeedleAi.
"""

import os
import re
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import urlparse

from app.config import Settings
from app.utils.logging import get_logger

logger = get_logger("config_validator")


class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""


class ConfigValidator:
    """Configuration validator for application settings."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def validate_all(self) -> bool:
        """Validate all configuration settings."""
        self.errors.clear()
        self.warnings.clear()

        self._validate_security_settings()
        self._validate_database_settings()
        self._validate_redis_settings()
        self._validate_llm_settings()
        self._validate_environment_settings()
        self._validate_file_paths()
        self._validate_network_settings()

        # Log results
        if self.errors:
            for error in self.errors:
                logger.error(f"Configuration error: {error}")

        if self.warnings:
            for warning in self.warnings:
                logger.warning(f"Configuration warning: {warning}")

        return len(self.errors) == 0

    def _validate_security_settings(self):
        """Validate security-related settings."""
        # Secret key validation
        if not self.settings.secret_key:
            self.errors.append("SECRET_KEY is required")
        elif len(self.settings.secret_key) < 32:
            self.errors.append("SECRET_KEY must be at least 32 characters long")
        elif self.settings.secret_key == "your-secret-key-change-in-production":
            if self.settings.environment == "production":
                self.errors.append("Default SECRET_KEY cannot be used in production")
            else:
                self.warnings.append("Using default SECRET_KEY - change for production")

        # Token expiration validation
        if self.settings.access_token_expire_minutes <= 0:
            self.errors.append("ACCESS_TOKEN_EXPIRE_MINUTES must be positive")
        elif self.settings.access_token_expire_minutes > 1440 and self.settings.environment == "production":
            self.warnings.append("Token expiration is longer than 24 hours in production")

        # Password policy validation
        if self.settings.min_password_length < 8:
            self.warnings.append("Minimum password length is less than 8 characters")

        # CORS validation for production
        if self.settings.environment == "production":
            if "*" in self.settings.cors_origins:
                self.errors.append("CORS origins cannot contain '*' in production")

            # Check for localhost/127.0.0.1 in production CORS
            for origin in self.settings.cors_origins:
                if "localhost" in origin or "127.0.0.1" in origin:
                    self.warnings.append(f"CORS origin '{origin}' contains localhost in production")

    def _validate_database_settings(self):
        """Validate database configuration."""
        if not self.settings.database_url:
            self.warnings.append("No database URL configured")
            return

        try:
            parsed = urlparse(self.settings.database_url)

            # Validate database scheme
            if parsed.scheme not in ["postgresql", "sqlite", "mysql"]:
                self.warnings.append(f"Unknown database scheme: {parsed.scheme}")

            # SQLite specific checks
            if parsed.scheme == "sqlite":
                # Check if directory exists for SQLite
                db_path = parsed.path.lstrip("/")
                if db_path and db_path != ":memory:":
                    db_dir = Path(db_path).parent
                    if not db_dir.exists():
                        self.warnings.append(f"SQLite database directory does not exist: {db_dir}")

            # PostgreSQL specific checks
            elif parsed.scheme == "postgresql":
                if not parsed.hostname:
                    self.errors.append("PostgreSQL hostname is missing")
                if not parsed.port:
                    self.warnings.append("PostgreSQL port not specified, using default")
                if not parsed.username:
                    self.errors.append("PostgreSQL username is missing")

        except Exception as e:
            self.errors.append(f"Invalid database URL: {e}")

    def _validate_redis_settings(self):
        """Validate Redis configuration."""
        if not self.settings.redis_url:
            self.errors.append("Redis URL is required")
            return

        try:
            parsed = urlparse(self.settings.redis_url)

            if parsed.scheme != "redis":
                self.errors.append(f"Invalid Redis scheme: {parsed.scheme}")

            if not parsed.hostname:
                self.errors.append("Redis hostname is missing")

            if parsed.port and (parsed.port < 1 or parsed.port > 65535):
                self.errors.append(f"Invalid Redis port: {parsed.port}")

        except Exception as e:
            self.errors.append(f"Invalid Redis URL: {e}")

        # Validate Redis connection limits
        if self.settings.redis_max_connections <= 0:
            self.errors.append("Redis max connections must be positive")
        elif self.settings.redis_max_connections > 1000:
            self.warnings.append("Redis max connections is very high (>1000)")

    def _validate_llm_settings(self):
        """Validate LLM provider settings."""
        # OpenRouter API key validation
        if self.settings.llm_provider == "openrouter":
            if not self.settings.openrouter_api_key:
                self.errors.append("OpenRouter API key is required when using OpenRouter provider")
            elif self.settings.openrouter_api_key == "your-openrouter-api-key-here":
                self.errors.append("Default OpenRouter API key must be replaced")

        # Model validation
        if not self.settings.default_model:
            self.errors.append("Default model is required")

        # Token and temperature validation
        if self.settings.max_tokens <= 0:
            self.errors.append("Max tokens must be positive")
        elif self.settings.max_tokens > 100000:
            self.warnings.append("Max tokens is very high (>100000)")

        if not (0.0 <= self.settings.temperature <= 2.0):
            self.errors.append("Temperature must be between 0.0 and 2.0")

    def _validate_environment_settings(self):
        """Validate environment-specific settings."""
        valid_environments = ["development", "testing", "staging", "production"]

        if self.settings.environment not in valid_environments:
            self.errors.append(f"Environment must be one of {valid_environments}")

        # Production-specific validations
        if self.settings.environment == "production":
            if self.settings.debug:
                self.warnings.append("Debug mode should be disabled in production")

            if self.settings.reload:
                self.warnings.append("Auto-reload should be disabled in production")

            if self.settings.workers <= 1:
                self.warnings.append("Consider using multiple workers in production")

            if self.settings.log_level == "DEBUG":
                self.warnings.append("Debug logging should be avoided in production")

        # Development-specific validations
        elif self.settings.environment == "development":
            if not self.settings.reload:
                self.warnings.append("Auto-reload is recommended for development")

    def _validate_file_paths(self):
        """Validate file paths and directories."""
        # Vector database path validation
        if hasattr(self.settings, 'chromadb_path'):
            if self.settings.chromadb_path:
                path = Path(self.settings.chromadb_path)
                if not path.parent.exists():
                    self.warnings.append(f"ChromaDB directory does not exist: {path.parent}")

    def _validate_network_settings(self):
        """Validate network-related settings."""
        # Port validation
        if not (1 <= self.settings.port <= 65535):
            self.errors.append(f"Invalid port number: {self.settings.port}")

        # Host validation
        if self.settings.host not in ["0.0.0.0", "127.0.0.1", "localhost"]:
            # Basic IP validation
            ip_pattern = re.compile(r'^(\d{1,3}\.){3}\d{1,3}$')
            if not ip_pattern.match(self.settings.host):
                self.warnings.append(f"Unusual host setting: {self.settings.host}")

        # Rate limiting validation
        if self.settings.rate_limit_requests <= 0:
            self.errors.append("Rate limit requests must be positive")

        if self.settings.rate_limit_window <= 0:
            self.errors.append("Rate limit window must be positive")

    def get_validation_report(self) -> Dict[str, Any]:
        """Get detailed validation report."""
        return {
            "valid": len(self.errors) == 0,
            "errors": self.errors,
            "warnings": self.warnings,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "environment": self.settings.environment,
            "critical_errors": [
                error for error in self.errors
                if any(keyword in error.lower() for keyword in ["secret", "api_key", "password"])
            ]
        }


def validate_configuration(settings: Settings) -> Dict[str, Any]:
    """
    Validate configuration and return report.

    Args:
        settings: Application settings to validate

    Returns:
        Validation report dictionary

    Raises:
        ConfigValidationError: If critical validation errors are found
    """
    validator = ConfigValidator(settings)
    is_valid = validator.validate_all()
    report = validator.get_validation_report()

    if not is_valid:
        critical_errors = report["critical_errors"]
        if critical_errors:
            raise ConfigValidationError(
                f"Critical configuration errors found: {'; '.join(critical_errors)}"
            )

    return report


def check_required_environment_vars() -> List[str]:
    """
    Check if required environment variables are set.

    Returns:
        List of missing environment variables
    """
    required_vars = [
        "SECRET_KEY",
        "DATABASE_URL",
        "REDIS_URL",
    ]

    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)

    return missing_vars


def setup_config_validation(settings: Settings) -> None:
    """
    Set up configuration validation on application startup.

    Args:
        settings: Application settings

    Raises:
        ConfigValidationError: If validation fails
    """
    logger.info("Validating application configuration...")

    # Check for missing environment variables
    missing_vars = check_required_environment_vars()
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        if settings.environment == "production":
            raise ConfigValidationError(f"Missing required environment variables: {missing_vars}")

    # Validate configuration
    try:
        report = validate_configuration(settings)

        logger.info(f"Configuration validation completed:")
        logger.info(f"  - Errors: {report['error_count']}")
        logger.info(f"  - Warnings: {report['warning_count']}")
        logger.info(f"  - Environment: {report['environment']}")

        if report["warnings"]:
            logger.info("Configuration warnings (please review):")
            for warning in report["warnings"][:5]:  # Show first 5 warnings
                logger.warning(f"  - {warning}")

    except ConfigValidationError as e:
        logger.error(f"Configuration validation failed: {e}")
        if settings.environment in ["production", "staging"]:
            raise
        else:
            logger.warning("Continuing with invalid configuration in development mode")
