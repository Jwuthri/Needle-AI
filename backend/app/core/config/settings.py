"""
Application settings with environment-specific configurations.
Updated for Pydantic v2 compatibility.
"""

import re
import secrets
from enum import Enum
from functools import lru_cache
from typing import Dict, List, Optional
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    # Try to load .env from current directory or parent directory
    env_paths = [Path('.env'), Path('../.env'), Path('backend/.env')]
    for env_path in env_paths:
        if env_path.exists():
            load_dotenv(env_path)
            break
except ImportError:
    pass  # python-dotenv not installed


class Environment(str, Enum):
    """Application environment types."""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class LogLevel(str, Enum):
    """Log level options."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Settings(BaseSettings):
    """Application settings with environment-specific validation."""

    # Environment Configuration
    environment: Environment = Environment.DEVELOPMENT
    debug: bool = Field(default=False, description="Enable debug mode")
    testing: bool = Field(default=False, description="Enable testing mode")

    # Application Metadata
    app_name: str = "NeedleAi"
    app_version: str = "0.1.0"
    description: str = "A FastAPI + Next.js AI agent application with OpenRouter and Agno"

    # Server Configuration
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, ge=1024, le=65535, description="Server port")
    reload: bool = Field(default=False, description="Enable auto-reload in development")
    workers: int = Field(default=1, ge=1, le=32, description="Number of worker processes")

    # API Configuration
    api_v1_str: str = "/api/v1"
    cors_origins: List[str] = Field(
        default=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        description="Allowed CORS origins"
    )
    allowed_hosts: List[str] = Field(default=["*"], description="Allowed host headers")
    max_request_size: int = Field(default=16 * 1024 * 1024, description="Max request size in bytes")

    # Database Configuration
    
    database_url: Optional[str] = Field(
        default="postgresql://postgres:postgres@localhost:5432/needleai",
        description="PostgreSQL database URL"
    )
    
    database_pool_size: int = Field(default=20, ge=1, le=100, description="Database pool size")
    database_max_overflow: int = Field(default=30, ge=0, le=100, description="Database max overflow")
    database_pool_timeout: int = Field(default=30, ge=1, le=300, description="Database pool timeout")

    # Valkey Configuration (backward compatible with Redis URLs)
    redis_url: str = Field(default="valkeys://localhost:6379/0", description="Valkey/Redis connection URL")
    redis_password: Optional[str] = Field(default=None, description="Valkey/Redis password")
    redis_max_connections: int = Field(default=100, ge=1, le=1000, description="Valkey max connections")
    redis_socket_timeout: int = Field(default=5, ge=1, le=60, description="Valkey socket timeout")
    redis_health_check_interval: int = Field(default=30, ge=5, le=300, description="Valkey health check interval")

    # WebSocket Configuration (for real-time updates)
    websocket_heartbeat_interval: int = Field(default=30, ge=10, le=300, description="WebSocket heartbeat interval in seconds")
    websocket_max_connections: int = Field(default=1000, ge=1, le=10000, description="Maximum concurrent WebSocket connections")

    # LLM Configuration
    llm_provider: str = Field(default="openai", description="LLM provider")
    openrouter_api_key: Optional[str] = Field(default=None, description="OpenRouter API key")
    default_model: str = Field(default="gpt-5-nano", description="Default LLM model")
    max_tokens: int = Field(default=1000, ge=1, le=32000, description="Maximum tokens per request")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="LLM temperature")
    site_url: Optional[str] = Field(default=None, description="Site URL for OpenRouter referrer tracking")

    # Agent Configuration
    use_agno_agents: bool = Field(default=True, description="Enable Agno agents")
    agent_type: str = Field(default="single", description="Agent architecture type")
    use_agno_memory: bool = Field(default=True, description="Enable agent memory")
    structured_outputs: bool = Field(default=False, description="Enable structured outputs")
    agent_instructions: Optional[str] = Field(default=None, description="Default agent instructions")
    
    # Hybrid Router Configuration
    router_model: str = Field(default="openai/gpt-5-nano", description="Model for query routing")
    router_confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Routing confidence threshold")
    
    # Specialist Models
    product_agent_model: str = Field(default="anthropic/claude-sonnet-4.5", description="Product specialist model")
    research_agent_model: str = Field(default="anthropic/claude-sonnet-4.5", description="Research specialist model")
    analytics_agent_model: str = Field(default="openai/gpt-5", description="Analytics specialist model")
    general_agent_model: str = Field(default="openai/gpt-4o-mini", description="General assistant model")
    
    # MCP API Configurations
    mcp_apis: Dict[str, Dict[str, any]] = Field(
        default_factory=dict,
        description="MCP API configurations for external integrations"
    )
    
    # Performance Configuration
    max_reasoning_steps: int = Field(default=10, ge=1, le=50, description="Max ReAct reasoning steps")
    tool_timeout_seconds: int = Field(default=30, ge=5, le=120, description="Tool execution timeout")
    
    # Security Configuration (Guardrails)
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key for moderation")
    enable_pii_detection: bool = Field(default=True, description="Enable PII detection and redaction")
    enable_injection_detection: bool = Field(default=True, description="Enable prompt injection detection")
    enable_content_moderation: bool = Field(default=True, description="Enable content moderation")
    injection_confidence_threshold: float = Field(default=0.4, ge=0.0, le=1.0, description="Injection detection threshold")

    # Vector Database Configuration
    vector_database: str = Field(default="pinecone", description="Vector database provider")
    memory_type: str = Field(default="vector", description="Memory storage type")
    
    # Pinecone Configuration
    pinecone_api_key: Optional[str] = Field(default=None, description="Pinecone API key")
    pinecone_environment: str = Field(default="gcp-starter", description="Pinecone environment")
    pinecone_index_name: str = Field(default="product-reviews", description="Pinecone index name for reviews")
    
    # Apify Configuration (Web Scraping)
    apify_api_token: Optional[str] = Field(default=None, description="Apify API token")
    apify_reddit_actor_id: str = Field(default="trudax/reddit-scraper", description="Apify Reddit scraper actor ID")
    apify_twitter_actor_id: str = Field(default="apidojo/tweet-scraper", description="Apify Twitter scraper actor ID")
    apify_g2_actor_id: str = Field(default="epctex/g2-scraper", description="Apify G2 scraper actor ID")
    apify_trustpilot_actor_id: str = Field(default="compass/trustpilot-scraper", description="Apify Trustpilot scraper actor ID")
    
    # Stripe Configuration (Payments)
    stripe_secret_key: Optional[str] = Field(default=None, description="Stripe secret key")
    stripe_publishable_key: str = Field(default="", description="Stripe publishable key")
    stripe_webhook_secret: Optional[str] = Field(default=None, description="Stripe webhook secret")
    stripe_currency: str = Field(default="usd", description="Default currency for Stripe")
    
    # Review Scraping Costs (per review in credits)
    reddit_review_cost: float = Field(default=0.01, ge=0.0, description="Cost per Reddit review")
    twitter_review_cost: float = Field(default=0.01, ge=0.0, description="Cost per Twitter review")
    g2_review_cost: float = Field(default=0.02, ge=0.0, description="Cost per G2 review")
    trustpilot_review_cost: float = Field(default=0.015, ge=0.0, description="Cost per Trustpilot review")
    csv_review_cost: float = Field(default=0.0, ge=0.0, description="Cost per CSV imported review")
    
    # Credit Packages (amount in USD: credits)
    credit_packages: Dict[str, int] = Field(
        default={
            "starter": 10,      # $10 = 1000 credits
            "professional": 50,  # $50 = 5000 credits
            "enterprise": 100   # $100 = 10000 credits
        },
        description="Available credit packages"
    )

    # WebSocket Configuration
    websocket_enabled: bool = Field(default="False", description="Enable WebSocket support")
    websocket_heartbeat_interval: int = Field(default=30, ge=5, le=300, description="WebSocket heartbeat interval")
    websocket_max_connections: int = Field(default=1000, ge=1, le=10000, description="Max concurrent WebSocket connections")

    # Security Configuration
    secret_key: str = Field(
        default_factory=lambda: secrets.token_urlsafe(32),
        min_length=32,
        description="Secret key for JWT tokens"
    )
    access_token_expire_minutes: int = Field(
        default=30,
        ge=1,
        le=43200,  # 30 days max
        description="JWT token expiration in minutes"
    )
    refresh_token_expire_days: int = Field(
        default=7,
        ge=1,
        le=30,
        description="Refresh token expiration in days"
    )
    algorithm: str = Field(default="HS256", description="JWT signing algorithm")

    # Password Policy
    min_password_length: int = Field(default=8, ge=8, le=128, description="Minimum password length")
    require_special_chars: bool = Field(default=True, description="Require special characters in passwords")
    require_numbers: bool = Field(default=True, description="Require numbers in passwords")
    require_uppercase: bool = Field(default=True, description="Require uppercase letters in passwords")

    # Clerk Configuration
    clerk_publishable_key: str = Field(default="", description="Clerk publishable key")
    clerk_secret_key: Optional[str] = Field(default=None, description="Clerk secret key")
    clerk_jwt_key: Optional[str] = Field(default=None, description="Clerk JWT verification key")
    clerk_frontend_api_url: Optional[str] = Field(
        default=None, 
        description="Clerk Frontend API URL (e.g., https://your-domain.clerk.accounts.dev)"
    )

    # Rate Limiting
    rate_limit_requests: int = Field(default=100, ge=1, le=10000, description="Requests per time window")
    rate_limit_window: int = Field(default=60, ge=1, le=3600, description="Rate limit window in seconds")
    rate_limit_storage: str = Field(default="redis", pattern="^(memory|redis)$", description="Rate limit storage backend")

    # Session Configuration
    session_expire_seconds: int = Field(default=86400, ge=300, le=2592000, description="Session expiration in seconds")
    max_messages_per_session: int = Field(default=100, ge=1, le=10000, description="Max messages per session")
    session_cleanup_interval: int = Field(default=3600, ge=300, le=86400, description="Session cleanup interval")

    # Cache Configuration
    cache_ttl_seconds: int = Field(default=3600, ge=60, le=86400, description="Default cache TTL")
    cache_max_size: int = Field(default=1000, ge=10, le=100000, description="Max cache entries")
    cache_backend: str = Field(default="redis", pattern="^(memory|redis)$", description="Cache backend")

    # Logging Configuration
    log_level: LogLevel = Field(default=LogLevel.INFO, description="Application log level")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format string"
    )
    log_file: Optional[str] = Field(default=None, description="Log file path")
    log_max_size: int = Field(default=10*1024*1024, ge=1024*1024, description="Max log file size in bytes")
    log_backup_count: int = Field(default=5, ge=1, le=100, description="Number of log backup files")
    structured_logging: bool = Field(default=False, description="Enable structured JSON logging")

    # Monitoring Configuration
    enable_metrics: bool = Field(default=True, description="Enable Prometheus metrics")
    metrics_path: str = Field(default="/metrics", description="Metrics endpoint path")
    enable_health_checks: bool = Field(default=True, description="Enable health check endpoints")
    health_check_timeout: int = Field(default=30, ge=1, le=300, description="Health check timeout")

    # Distributed Tracing Configuration
    enable_tracing: bool = Field(default=False, description="Enable distributed tracing with OpenTelemetry")
    tracing_exporter: str = Field(
        default="console",
        pattern="^(console|jaeger|zipkin|otlp)$",
        description="Tracing exporter type"
    )
    tracing_sample_rate: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Tracing sample rate (0.0 to 1.0)"
    )
    jaeger_endpoint: str = Field(
        default="http://localhost:14268/api/traces",
        description="Jaeger collector endpoint"
    )
    zipkin_endpoint: str = Field(
        default="http://localhost:9411/api/v2/spans",
        description="Zipkin collector endpoint"
    )
    otlp_endpoint: str = Field(
        default="http://localhost:4317",
        description="OTLP gRPC collector endpoint"
    )

    # Celery Configuration (Background Tasks)
    celery_broker_url: str = Field(default="valkeys://localhost:6379/1", description="Celery broker URL (Valkey/Redis)")
    celery_result_backend: str = Field(default="valkeys://localhost:6379/1", description="Celery result backend (Valkey/Redis)")
    
    @field_validator('celery_broker_url', 'celery_result_backend')
    @classmethod
    def ensure_redis_db(cls, v: str) -> str:
        """Ensure Valkey URL has database number."""
        if v:
            # If URL doesn't end with /number, add /0
            if v.startswith(('redis://', 'rediss://', 'valkey://', 'valkeys://')):
                if not re.search(r'/\d+$', v):
                    v = v.rstrip('/') + '/0'
        return v
    
    celery_task_always_eager: bool = Field(default=False, description="Execute tasks synchronously for testing")
    celery_task_routes: Dict[str, Dict[str, str]] = Field(
        default={
            'app.tasks.llm_tasks.*': {'queue': 'llm'},
            'app.tasks.chat_tasks.*': {'queue': 'chat'},
            'app.tasks.general_tasks.*': {'queue': 'general'},
            'app.tasks.scraping_tasks.*': {'queue': 'scraping'},
            'app.tasks.sentiment_tasks.*': {'queue': 'sentiment'},
            'app.tasks.indexing_tasks.*': {'queue': 'indexing'},
        },
        description="Celery task routing configuration"
    )
    celery_worker_prefetch_multiplier: int = Field(default=1, ge=1, le=100, description="Worker prefetch multiplier")
    celery_worker_max_tasks_per_child: int = Field(default=1000, ge=1, description="Max tasks per worker child")
    celery_result_expires: int = Field(default=3600, ge=60, description="Task result expiration time")

    # File Upload Configuration
    max_upload_size: int = Field(default=50*1024*1024, ge=1024, description="Max file upload size in bytes")
    allowed_upload_types: List[str] = Field(
        default=[".txt", ".pdf", ".doc", ".docx", ".json", ".csv", ".xlsx"],
        description="Allowed file upload extensions"
    )
    upload_storage_path: str = Field(default="./data/uploads", description="Upload storage directory")

    # Performance Configuration
    request_timeout: int = Field(default=60, ge=1, le=300, description="Request timeout in seconds")
    keep_alive_timeout: int = Field(default=65, ge=1, le=300, description="Keep-alive timeout")
    max_concurrent_requests: int = Field(default=1000, ge=1, le=10000, description="Max concurrent requests")

    # Feature Flags
    enable_file_uploads: bool = Field(default=True, description="Enable file upload functionality")
    enable_websockets: bool = Field(default=True, description="Enable WebSocket endpoints")
    enable_chat_history: bool = Field(default=True, description="Enable chat history storage")
    enable_user_registration: bool = Field(default=False, description="Enable user self-registration")

    # Development Configuration
    reload_includes: List[str] = Field(default=["*.py"], description="Files to watch for reload")
    reload_excludes: List[str] = Field(default=["*.pyc", "*.log"], description="Files to exclude from reload")

    # Pydantic v2 Validators (updated from v1 @validator to @field_validator)
    @field_validator("environment", mode="before")
    @classmethod
    def validate_environment(cls, v):
        """Validate environment setting."""
        if isinstance(v, str):
            v = v.lower()
        return Environment(v)

    @field_validator("debug", mode="before")
    @classmethod
    def set_debug_mode(cls, v):
        """Set debug mode."""
        return bool(v) if v is not None else True

    @field_validator("reload", mode="before")
    @classmethod
    def set_reload_mode(cls, v):
        """Set reload mode."""
        return bool(v) if v is not None else False

    @field_validator("log_level", mode="before")
    @classmethod
    def set_log_level(cls, v):
        """Set log level."""
        return v or LogLevel.INFO

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from string or list."""
        if v is None or v == "":
            return []
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @field_validator("allowed_hosts", mode="before")
    @classmethod
    def parse_allowed_hosts(cls, v):
        """Parse allowed hosts from string or list."""
        if v is None or v == "":
            return []
        if isinstance(v, str):
            return [host.strip() for host in v.split(",") if host.strip()]
        return v

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v):
        """Validate secret key length."""
        secret_value = str(v)

        if len(secret_value) < 32:
            raise ValueError("Secret key must be at least 32 characters long")
        return v

    @field_validator("access_token_expire_minutes")
    @classmethod
    def validate_token_expiration(cls, v):
        """Validate token expiration."""
        if v > 1440:  # 24 hours max
            raise ValueError("Token expiration cannot exceed 1440 minutes (24 hours)")
        return v

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v):
        """Validate database URL format."""
        if not v:
            return v

        # Basic validation - just check if it's a valid URL format
        if not v.startswith(("postgresql://", "sqlite://", "mysql://", "mongodb://")):
            raise ValueError("Invalid database URL format")

        return v

    def get_secret(self, key: str) -> Optional[str]:
        """Get secret value by key."""
        return getattr(self, key, None)

    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == Environment.DEVELOPMENT

    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == Environment.PRODUCTION

    def is_testing(self) -> bool:
        """Check if running in testing environment."""
        return self.environment == Environment.TESTING or self.testing

    def get_redis_url_with_auth(self, db: Optional[int] = None) -> str:
        """
        Get Valkey/Redis URL with authentication if password is provided.

        Args:
            db: Database number to use (overrides URL default)

        Returns:
            Complete Valkey/Redis URL with authentication
        """
        # Check if we have a password
        password = self.get_secret("redis_password")

        # If redis_url is already set and has password, use it
        if password and "@" in self.redis_url:
            # URL already has auth, use as-is but potentially update db
            base_url = self.redis_url
        elif password:
            # Parse existing URL to add password
            # Extract components from redis_url (e.g., valkeys://localhost:6379/0)
            match = re.match(r'(valkeys?|rediss?)://([^/]+)(/.+)?', self.redis_url)
            if match:
                protocol = match.group(1)
                host_port = match.group(2)
                db_part = match.group(3) or "/0"
                base_url = f"{protocol}://:{password}@{host_port}{db_part}"
            else:
                # Fallback to default format
                base_url = f"valkeys://:{password}@localhost:6379/0"
        else:
            # No password, use existing URL
            base_url = self.redis_url

        # Override database number if specified
        if db is not None:
            base_url = re.sub(r'/\d+$', f'/{db}', base_url)

        return base_url
    
    def parse_database_url(self) -> Dict[str, str]:
        """
        Parse database URL into components.
        
        Returns:
            Dictionary with host, port, user, password, and database name
        """
        if not self.database_url:
            return {
                "user": "postgres",
                "password": "",
                "host": "localhost",
                "port": "5432",
                "database": "needleai"
            }
        
        # Parse PostgreSQL URL: postgresql://user:password@host:port/database
        # or SQLite: sqlite:///path/to/db.sqlite
        if self.database_url.startswith("sqlite"):
            return {
                "user": "",
                "password": "",
                "host": "",
                "port": "",
                "database": self.database_url.split("///")[-1]
            }
        
        # Parse PostgreSQL-style URL
        match = re.match(
            r'(?:postgresql|postgres)://(?:([^:]+):([^@]+)@)?([^:/]+)(?::(\d+))?/(.+)',
            self.database_url
        )
        
        if match:
            user, password, host, port, database = match.groups()
            return {
                "user": user or "postgres",
                "password": password or "",
                "host": host or "localhost",
                "port": port or "5432",
                "database": database or "needleai"
            }
        
        # Fallback defaults
        return {
            "user": "postgres",
            "password": "",
            "host": "localhost",
            "port": "5432",
            "database": "needleai"
        }

    # Pydantic v2 Model Configuration (updated from v1 Config class)
    model_config = SettingsConfigDict(
        case_sensitive=False,
        env_ignore_empty=True,
        extra='ignore',
        env_file=('.env', '../.env'),  # Try both current dir and parent dir
        env_file_encoding='utf-8'
    )


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()
