"""
Environment-specific configuration overrides.
"""

from pathlib import Path
from typing import Any, Dict, Optional, Type

from app.utils.logging import get_logger

from .settings import Environment, Settings

logger = get_logger("environments")


class DevelopmentSettings(Settings):
    """Development environment settings."""

    environment: Environment = Environment.DEVELOPMENT
    debug: bool = True
    reload: bool = True
    testing: bool = False

    # Relaxed security for development
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8080",  # Common dev ports
        "http://localhost:5173",  # Vite default
        "http://localhost:4200",  # Angular default
    ]

    # Development database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/needleai"
    
    # Smaller pools for development
    database_pool_size: int = 5
    database_max_overflow: int = 10
    redis_max_connections: int = 20

    # More verbose logging
    log_level: str = "DEBUG"
    structured_logging: bool = True

    # Relaxed rate limiting
    rate_limit_requests: int = 1000

    # Quick token expiration for testing
    access_token_expire_minutes: int = 60

    # Enable all features for testing
    enable_file_uploads: bool = True
    enable_websockets: bool = True
    enable_chat_history: bool = True
    enable_user_registration: bool = True

    # Development-specific settings
    reload_includes: list[str] = ["*.py", "*.html", "*.css", "*.js"]


class TestingSettings(Settings):
    """Testing environment settings."""

    environment: Environment = Environment.TESTING
    debug: bool = True
    testing: bool = True
    reload: bool = False

    # In-memory/fast databases for testing
    database_url: str = "sqlite:///:memory:"
    redis_url: str = "redis://localhost:6379/15"  # Separate DB for tests

    # Small pools for testing
    database_pool_size: int = 1
    database_max_overflow: int = 0
    redis_max_connections: int = 5

    # Disable external services for testing
    # WebSocket test configuration
    websocket_heartbeat_interval: int = 10  # Faster for tests
    websocket_max_connections: int = 100  # Limited for tests

    # Fast operations for testing
    celery_task_always_eager: bool = True
    cache_ttl_seconds: int = 60

    # Minimal logging for tests
    log_level: str = "WARNING"
    structured_logging: bool = False

    # Minimal security for speed
    secret_key: str = "test-secret-key-at-least-32-characters-long"
    access_token_expire_minutes: int = 5

    # Disable rate limiting for tests
    rate_limit_requests: int = 10000

    # Disable some features for testing speed
    enable_metrics: bool = False
    websocket_enabled: bool = False


class StagingSettings(Settings):
    """Staging environment settings."""

    environment: Environment = Environment.STAGING
    debug: bool = False
    reload: bool = False
    testing: bool = False

    # Production-like database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/needleai_staging"
    

    # Production-like pools
    database_pool_size: int = 10
    database_max_overflow: int = 20

    # Moderate logging
    log_level: str = "INFO"
    structured_logging: bool = True

    # Production-like security
    access_token_expire_minutes: int = 30
    rate_limit_requests: int = 200

    # Enable monitoring
    enable_metrics: bool = True
    enable_health_checks: bool = True

    # Staging-specific CORS (more restrictive than dev)
    cors_origins: list[str] = [
        "https://staging.needleai.com",
        "https://needleai-staging.vercel.app",
    ]


class ProductionSettings(Settings):
    """Production environment settings."""

    environment: Environment = Environment.PRODUCTION
    debug: bool = False
    reload: bool = False
    testing: bool = False

    # Production database - must be provided via environment
    
    database_url: Optional[str] = None  # Must be set via env/secrets
    

    # Production pools
    database_pool_size: int = 20
    database_max_overflow: int = 30
    redis_max_connections: int = 100

    # Production logging
    log_level: str = "INFO"
    structured_logging: bool = True
    log_file: Optional[str] = "/var/log/needleai/app.log"

    # Production security
    access_token_expire_minutes: int = 30
    rate_limit_requests: int = 100

    # Production CORS - must be configured
    cors_origins: list[str] = [
        "https://needleai.com",
        "https://www.needleai.com",
    ]
    allowed_hosts: list[str] = [
        "needleai.com",
        "www.needleai.com",
        "api.needleai.com",
    ]

    # Enable all monitoring
    enable_metrics: bool = True
    enable_health_checks: bool = True

    # Production performance
    workers: int = 4  # Scale based on CPU cores
    max_concurrent_requests: int = 2000
    request_timeout: int = 30

    # Production features
    enable_file_uploads: bool = True
    enable_websockets: bool = True
    enable_chat_history: bool = True
    enable_user_registration: bool = False  # Controlled registration


# Environment settings mapping
ENVIRONMENT_SETTINGS: Dict[Environment, Type[Settings]] = {
    Environment.DEVELOPMENT: DevelopmentSettings,
    Environment.TESTING: TestingSettings,
    Environment.STAGING: StagingSettings,
    Environment.PRODUCTION: ProductionSettings,
}


def get_environment_settings(environment: Optional[str] = None) -> Type[Settings]:
    """
    Get settings class for specified environment.

    Args:
        environment: Environment name (development, testing, staging, production)

    Returns:
        Settings class for the environment
    """
    if environment is None:
        # Try to detect from environment variable
        import os
        environment = os.getenv("ENVIRONMENT", "development")

    try:
        env_enum = Environment(environment.lower())
        settings_class = ENVIRONMENT_SETTINGS.get(env_enum, DevelopmentSettings)
        logger.info(f"Using {settings_class.__name__} for environment '{environment}'")
        return settings_class
    except ValueError:
        logger.warning(f"Unknown environment '{environment}', defaulting to development")
        return DevelopmentSettings


def create_environment_config(environment: str, overrides: Optional[Dict[str, Any]] = None) -> Settings:
    """
    Create settings instance for environment with optional overrides.

    Args:
        environment: Environment name
        overrides: Optional field overrides

    Returns:
        Settings instance
    """
    settings_class = get_environment_settings(environment)

    if overrides:
        # Create settings with overrides
        settings = settings_class(**overrides)
        logger.info(f"Created {environment} settings with {len(overrides)} overrides")
    else:
        settings = settings_class()
        logger.info(f"Created {environment} settings with defaults")

    return settings


def validate_environment_settings(settings: Settings) -> Dict[str, Any]:
    """
    Validate settings for the current environment.

    Args:
        settings: Settings instance to validate

    Returns:
        Validation report with errors and warnings
    """
    validation_report = {
        "environment": settings.environment,
        "errors": [],
        "warnings": [],
        "valid": True
    }

    # Production-specific validations
    if settings.environment == Environment.PRODUCTION:
        # Database URL must be provided
        if not settings.database_url:
            validation_report["errors"].append("Database URL is required in production")

        # Secret key must not be default
        secret_key = settings.get_secret("secret_key") or ""
        if "test" in secret_key.lower() or "default" in secret_key.lower():
            validation_report["errors"].append("Production secret key appears to be a default/test value")

        # CORS origins should be specific
        if "*" in settings.cors_origins or "localhost" in str(settings.cors_origins):
            validation_report["warnings"].append("CORS origins should be specific in production")

        # Check SSL/TLS configuration
        if settings.database_url and "sslmode=require" not in settings.database_url:
            validation_report["warnings"].append("Database SSL should be enabled in production")

    # Development-specific validations
    elif settings.environment == Environment.DEVELOPMENT:
        # Warn about production secrets in development
        if settings.database_url and "amazonaws.com" in settings.database_url:
            validation_report["warnings"].append("Using production database in development")

    # General validations
    if len(settings.cors_origins) == 0:
        validation_report["errors"].append("At least one CORS origin must be specified")

    if settings.rate_limit_requests <= 0:
        validation_report["errors"].append("Rate limit must be positive")

    # Set overall validation status
    validation_report["valid"] = len(validation_report["errors"]) == 0

    return validation_report
