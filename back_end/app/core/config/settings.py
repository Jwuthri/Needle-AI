"""Application settings with Pydantic validation."""

from functools import lru_cache
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment-specific validation."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = Field(default="NeedleAi", description="Application name")
    app_version: str = Field(default="0.1.0", description="Application version")
    environment: str = Field(default="development", description="Environment name")
    debug: bool = Field(default=True, description="Debug mode")

    # Server
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")

    # Database
    database_url: str = Field(..., description="PostgreSQL database URL")
    database_name: str = Field(default="needle_ai", description="Database name")

    # Security
    secret_key: str = Field(..., description="Secret key for JWT encoding")
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(
        default=30, description="Access token expiration in minutes"
    )

    # CORS
    cors_origins: List[str] = Field(
        default=["http://localhost:3000"], description="Allowed CORS origins"
    )

    # Clerk Authentication
    clerk_secret_key: str = Field(..., description="Clerk secret key")
    next_public_clerk_publishable_key: str = Field(
        ..., description="Clerk publishable key"
    )

    # LLM API Keys (Optional)
    openai_api_key: Optional[str] = Field(
        default=None, description="OpenAI API key"
    )
    anthropic_api_key: Optional[str] = Field(
        default=None, description="Anthropic API key"
    )

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    use_rich_logging: bool = Field(
        default=True, description="Use Rich for logging"
    )


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached application settings.
    
    Returns:
        Settings: Application settings instance
    """
    return Settings()
