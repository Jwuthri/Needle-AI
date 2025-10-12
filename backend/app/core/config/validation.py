"""
Configuration validation for NeedleAi.
"""

import re
import socket
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import urlparse

from app.utils.logging import get_logger

from .secrets import get_secret_manager
from .settings import Settings

logger = get_logger("config_validation")


class ConfigValidationError(Exception):
    """Configuration validation error."""

    def __init__(self, message: str, errors: List[Dict[str, Any]]):
        self.message = message
        self.errors = errors
        super().__init__(message)


class ConfigValidator:
    """Comprehensive configuration validator."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.errors: List[Dict[str, Any]] = []
        self.warnings: List[Dict[str, Any]] = []

    def _add_error(self, field: str, message: str, value: Any = None):
        """Add validation error."""
        self.errors.append({
            "field": field,
            "message": message,
            "value": str(value) if value is not None else None,
            "severity": "error"
        })

    def _add_warning(self, field: str, message: str, value: Any = None):
        """Add validation warning."""
        self.warnings.append({
            "field": field,
            "message": message,
            "value": str(value) if value is not None else None,
            "severity": "warning"
        })

    def validate_database_config(self):
        """Validate database configuration."""
        if not self.settings.database_url:
            if self.settings.is_production():
                self._add_error("database_url", "Database URL is required in production")
            else:
                self._add_warning("database_url", "No database URL configured, using in-memory database")
            return

        try:
            parsed = urlparse(self.settings.database_url)

            # Validate scheme
            valid_schemes = ["postgresql", "sqlite", "postgresql+asyncpg", "sqlite+aiosqlite"]
            if parsed.scheme not in valid_schemes:
                self._add_error(
                    "database_url",
                    f"Unsupported database scheme: {parsed.scheme}. Valid schemes: {valid_schemes}",
                    parsed.scheme
                )

            # Production-specific validations
            if self.settings.is_production():
                if parsed.scheme.startswith("sqlite"):
                    self._add_warning("database_url", "SQLite not recommended for production use")

                # Check for SSL in production PostgreSQL
                if parsed.scheme.startswith("postgresql") and "sslmode" not in self.settings.database_url:
                    self._add_warning("database_url", "SSL/TLS should be enabled for production database")

                # Check for default credentials
                if parsed.username in ["postgres", "root", "admin"] and parsed.password in ["postgres", "password", "admin"]:
                    self._add_error("database_url", "Default database credentials detected in production")

            # Validate connection parameters
            if parsed.hostname:
                try:
                    socket.gethostbyname(parsed.hostname)
                except socket.gaierror:
                    self._add_warning("database_url", f"Cannot resolve database hostname: {parsed.hostname}")

        except Exception as e:
            self._add_error("database_url", f"Invalid database URL format: {str(e)}")

    def validate_redis_config(self):
        """Validate Redis configuration."""
        try:
            parsed = urlparse(self.settings.redis_url)

            if parsed.scheme not in ("redis", "rediss"):
                self._add_error("redis_url", f"Invalid Redis scheme: {parsed.scheme}. Must be 'redis://' or 'rediss://'", parsed.scheme)

            # Check connection parameters
            if self.settings.redis_max_connections < 1:
                self._add_error("redis_max_connections", "Redis max connections must be positive")

            if self.settings.redis_socket_timeout < 1:
                self._add_error("redis_socket_timeout", "Redis socket timeout must be positive")

        except Exception as e:
            self._add_error("redis_url", f"Invalid Redis URL format: {str(e)}")

    def validate_security_config(self):
        """Validate security configuration."""
        # Secret key validation
        secret_key = self.settings.get_secret("secret_key") or ""
        if len(secret_key) < 32:
            self._add_error("secret_key", "Secret key must be at least 32 characters long")

        # Check for common weak secret keys
        weak_patterns = [
            r"^test",
            r"^dev",
            r"^default",
            r"^secret",
            r"^password",
            r"1234567890",
            r"abcdefghij"
        ]

        for pattern in weak_patterns:
            if re.search(pattern, secret_key, re.IGNORECASE):
                self._add_warning("secret_key", f"Secret key matches weak pattern: {pattern}")
                break

        # Token expiration validation
        if self.settings.is_production() and self.settings.access_token_expire_minutes > 120:
            self._add_warning("access_token_expire_minutes", "Long token expiration in production (>2 hours)")

        # CORS validation
        if "*" in self.settings.cors_origins:
            if self.settings.is_production():
                self._add_error("cors_origins", "Wildcard CORS origins not allowed in production")
            else:
                self._add_warning("cors_origins", "Wildcard CORS origins detected")

        # Rate limiting validation
        if self.settings.rate_limit_requests <= 0:
            self._add_error("rate_limit_requests", "Rate limit requests must be positive")

        if self.settings.rate_limit_window <= 0:
            self._add_error("rate_limit_window", "Rate limit window must be positive")

    def validate_llm_config(self):
        """Validate LLM configuration."""
        # OpenRouter API key
        if self.settings.llm_provider == "openrouter":
            api_key = self.settings.get_secret("openrouter_api_key")
            if not api_key:
                self._add_error("openrouter_api_key", "OpenRouter API key is required")
            elif not api_key.startswith("sk-or-"):
                self._add_warning("openrouter_api_key", "OpenRouter API key format may be incorrect")

        # Model configuration
        if not self.settings.default_model:
            self._add_error("default_model", "Default model must be specified")

        # Token limits
        if self.settings.max_tokens <= 0:
            self._add_error("max_tokens", "Max tokens must be positive")
        elif self.settings.max_tokens > 32000:
            self._add_warning("max_tokens", "Very high max tokens setting may cause issues")

        # Temperature validation
        if not (0.0 <= self.settings.temperature <= 2.0):
            self._add_error("temperature", "Temperature must be between 0.0 and 2.0")

    def validate_vector_db_config(self):
        """Validate vector database configuration."""
        vector_db = self.settings.vector_database

        if vector_db == "pinecone":
            api_key = self.settings.get_secret("pinecone_api_key")
            if not api_key:
                self._add_error("pinecone_api_key", "Pinecone API key is required")

            if not self.settings.pinecone_index_name:
                self._add_error("pinecone_index_name", "Pinecone index name is required")

        elif vector_db == "weaviate":
            if not self.settings.weaviate_url:
                self._add_error("weaviate_url", "Weaviate URL is required")

        elif vector_db == "qdrant":
            if not self.settings.qdrant_url:
                self._add_error("qdrant_url", "Qdrant URL is required")

        elif vector_db == "chromadb":
            if not self.settings.chromadb_path:
                self._add_error("chromadb_path", "ChromaDB path is required")

    def validate_clerk_config(self):
        """Validate Clerk authentication configuration."""
        if self.settings.clerk_publishable_key:
            if not self.settings.clerk_publishable_key.startswith("pk_"):
                self._add_error("clerk_publishable_key", "Clerk publishable key should start with 'pk_'")

        clerk_secret = self.settings.get_secret("clerk_secret_key")
        if clerk_secret:
            if not clerk_secret.startswith("sk_"):
                self._add_error("clerk_secret_key", "Clerk secret key should start with 'sk_'")

    def validate_file_paths(self):
        """Validate file paths and directories."""
        # Upload storage path
        upload_path = Path(self.settings.upload_storage_path)
        if not upload_path.exists():
            try:
                upload_path.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created upload directory: {upload_path}")
            except OSError as e:
                self._add_error("upload_storage_path", f"Cannot create upload directory: {str(e)}")

        # Log file path
        if self.settings.log_file:
            log_path = Path(self.settings.log_file)
            log_dir = log_path.parent
            if not log_dir.exists():
                try:
                    log_dir.mkdir(parents=True, exist_ok=True)
                    logger.info(f"Created log directory: {log_dir}")
                except OSError as e:
                    self._add_error("log_file", f"Cannot create log directory: {str(e)}")

        # ChromaDB path (if used)
        if self.settings.vector_database == "chromadb":
            chromadb_path = Path(self.settings.chromadb_path)
            if not chromadb_path.exists():
                try:
                    chromadb_path.mkdir(parents=True, exist_ok=True)
                    logger.info(f"Created ChromaDB directory: {chromadb_path}")
                except OSError as e:
                    self._add_error("chromadb_path", f"Cannot create ChromaDB directory: {str(e)}")

    def validate_performance_settings(self):
        """Validate performance-related settings."""
        # Worker count validation
        if self.settings.workers < 1:
            self._add_error("workers", "Worker count must be at least 1")
        elif self.settings.workers > 32:
            self._add_warning("workers", "High worker count may cause resource issues")

        # Database pool settings
        if self.settings.database_pool_size < 1:
            self._add_error("database_pool_size", "Database pool size must be positive")

        if self.settings.database_max_overflow < 0:
            self._add_error("database_max_overflow", "Database max overflow cannot be negative")

        # Timeout settings
        if self.settings.request_timeout <= 0:
            self._add_error("request_timeout", "Request timeout must be positive")

        if self.settings.database_pool_timeout <= 0:
            self._add_error("database_pool_timeout", "Database pool timeout must be positive")

    def validate_secrets_availability(self):
        """Validate that required secrets are available."""
        secret_manager = get_secret_manager()

        required_secrets = []

        # Conditional secret requirements
        if self.settings.llm_provider == "openrouter":
            required_secrets.append("openrouter_api_key")

        if self.settings.vector_database == "pinecone":
            required_secrets.append("pinecone_api_key")

        if self.settings.clerk_publishable_key:
            required_secrets.extend(["clerk_secret_key", "clerk_jwt_key"])

        # Production secrets
        if self.settings.is_production():
            required_secrets.extend([
                "secret_key",
                "database_url"  # Should be in secrets for production
            ])

        # Validate availability
        for secret_key in required_secrets:
            if not secret_manager.get_secret(secret_key):
                self._add_error("secrets", f"Required secret '{secret_key}' is not available")

    def validate_all(self) -> Dict[str, Any]:
        """
        Run all validations.

        Returns:
            Validation report with errors and warnings
        """
        self.errors.clear()
        self.warnings.clear()

        # Run all validation methods
        validation_methods = [
            self.validate_database_config,
            self.validate_redis_config,
            self.validate_security_config,
            self.validate_llm_config,
            self.validate_vector_db_config,
            self.validate_clerk_config,
            self.validate_file_paths,
            self.validate_performance_settings,
            self.validate_secrets_availability,
        ]

        for method in validation_methods:
            try:
                method()
            except Exception as e:
                self._add_error(
                    "validation",
                    f"Error in {method.__name__}: {str(e)}"
                )

        # Create validation report
        report = {
            "environment": self.settings.environment,
            "valid": len(self.errors) == 0,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "errors": self.errors,
            "warnings": self.warnings,
            "summary": self._generate_summary()
        }

        # Log results
        if self.errors:
            logger.error(f"Configuration validation failed with {len(self.errors)} errors")
            for error in self.errors:
                logger.error(f"  {error['field']}: {error['message']}")

        if self.warnings:
            logger.warning(f"Configuration validation completed with {len(self.warnings)} warnings")
            for warning in self.warnings:
                logger.warning(f"  {warning['field']}: {warning['message']}")

        if not self.errors and not self.warnings:
            logger.info("Configuration validation passed without issues")

        return report

    def _generate_summary(self) -> str:
        """Generate validation summary message."""
        if not self.errors and not self.warnings:
            return "Configuration is valid"

        parts = []
        if self.errors:
            parts.append(f"{len(self.errors)} error{'s' if len(self.errors) != 1 else ''}")
        if self.warnings:
            parts.append(f"{len(self.warnings)} warning{'s' if len(self.warnings) != 1 else ''}")

        return f"Configuration validation completed with {' and '.join(parts)}"


def validate_settings(settings: Settings) -> Dict[str, Any]:
    """
    Validate settings configuration.

    Args:
        settings: Settings instance to validate

    Returns:
        Validation report

    Raises:
        ConfigValidationError: If critical errors are found
    """
    validator = ConfigValidator(settings)
    report = validator.validate_all()

    # Raise exception for critical errors in production
    if settings.is_production() and report["errors"]:
        critical_errors = [
            error for error in report["errors"]
            if error["field"] in ["database_url", "secret_key", "openrouter_api_key"]
        ]

        if critical_errors:
            raise ConfigValidationError(
                f"Critical configuration errors in production: {len(critical_errors)} errors found",
                critical_errors
            )

    return report


def setup_config_validation(settings: Settings) -> Dict[str, Any]:
    """
    Setup and run configuration validation.

    Args:
        settings: Settings instance to validate

    Returns:
        Validation report
    """
    logger.info(f"Validating configuration for environment: {settings.environment}")

    try:
        report = validate_settings(settings)

        # Log summary
        logger.info(f"Configuration validation: {report['summary']}")

        return report

    except ConfigValidationError as e:
        logger.error(f"Configuration validation failed: {e.message}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during configuration validation: {str(e)}")
        raise ConfigValidationError("Configuration validation failed with unexpected error", [])
