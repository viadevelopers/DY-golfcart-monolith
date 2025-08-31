"""
Configuration settings for DY-GOLFCART MVP system.
Simplified monolith architecture without Kafka.
"""
from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import Field, validator
from functools import lru_cache
import os
from pathlib import Path


def get_env_file() -> str:
    """
    Determine which .env file to load based on environment.
    
    Priority order:
    1. ENV_FILE environment variable (explicit override)
    2. .env.{ENVIRONMENT} if ENVIRONMENT is set
    3. .env.local if running locally (not in Docker)
    4. .env.dev as default for development
    5. .env as final fallback
    """
    # Check for explicit ENV_FILE override
    if env_file := os.getenv("ENV_FILE"):
        if Path(env_file).exists():
            return env_file
    
    # Check ENVIRONMENT variable for environment-specific file
    if environment := os.getenv("ENVIRONMENT"):
        env_specific = f".env.{environment}"
        if Path(env_specific).exists():
            return env_specific
    
    # Check if running in Docker (by checking for common Docker env vars)
    in_docker = os.path.exists("/.dockerenv") or os.getenv("DOCKER_CONTAINER") == "true"
    
    if not in_docker:
        # Running locally - prefer .env.local
        if Path(".env.local").exists():
            return ".env.local"
    
    # Default to .env.dev for development
    if Path(".env.dev").exists():
        return ".env.dev"
    
    # Final fallback to .env
    return ".env"


class Settings(BaseSettings):
    """Application settings with environment-aware configuration."""
    
    # =============================================================================
    # APPLICATION SETTINGS
    # =============================================================================
    APP_NAME: str = "DY-GOLFCART Management System"
    APP_VERSION: str = "1.0.0-MVP"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = Field(default="development", description="Runtime environment")
    DEBUG: bool = Field(default=True, description="Debug mode")
    
    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    @validator('DEBUG')
    def set_debug_mode(cls, v: bool, values: dict) -> bool:
        """Auto-set debug based on environment."""
        env = values.get('ENVIRONMENT', 'development')
        if env == 'production':
            return False
        return v
    
    # =============================================================================
    # DATABASE CONFIGURATION (PostgreSQL with PostGIS)
    # ============================================================================= 
    DATABASE_URL: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/golfcart_db",
        description="Main database connection URL"
    )
    TEST_DATABASE_URL: Optional[str] = Field(
        default=None,
        description="Test database URL for integration tests"
    )
    DATABASE_POOL_SIZE: int = Field(default=5, description="Connection pool size")
    DATABASE_MAX_OVERFLOW: int = Field(default=10, description="Max pool overflow")
    DATABASE_ECHO: bool = Field(default=False, description="Echo SQL queries")
    
    @validator('DATABASE_ECHO')
    def set_db_echo(cls, v: bool, values: dict) -> bool:
        """Enable SQL echo in development."""
        env = values.get('ENVIRONMENT', 'development')
        debug = values.get('DEBUG', True)
        return v or (env == 'development' and debug)
    
    # =============================================================================
    # REDIS CONFIGURATION (Caching and Sessions)
    # =============================================================================
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL"
    )
    REDIS_TTL: int = Field(default=300, description="Default TTL in seconds")
    REDIS_TIMEOUT: int = Field(default=5, description="Connection timeout")
    
    # =============================================================================
    # SECURITY & AUTHENTICATION 
    # =============================================================================
    SECRET_KEY: str = Field(
        default="dy-golfcart-secret-key-change-in-production",
        description="JWT signing secret"
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    @validator('SECRET_KEY')
    def validate_secret_key(cls, v: str, values: dict) -> str:
        """Ensure secret key is changed in production."""
        env = values.get('ENVIRONMENT', 'development')
        if env == 'production' and 'change-in-production' in v:
            raise ValueError('SECRET_KEY must be changed in production')
        return v
    
    # =============================================================================
    # MQTT CONFIGURATION (Real-time Communication)
    # =============================================================================
    MQTT_ENABLED: bool = Field(default=True, description="Enable MQTT client")
    MQTT_BROKER_URL: str = Field(default="emqx.dev.viasoft.ai", description="MQTT broker URL")
    MQTT_PORT: int = Field(default=8883, description="MQTT port (8883 for TLS)")
    MQTT_WS_PORT: int = Field(default=8084, description="WebSocket port")
    MQTT_USERNAME: Optional[str] = Field(default="admin", description="MQTT username")
    MQTT_PASSWORD: Optional[str] = Field(default="public", description="MQTT password")
    MQTT_CLIENT_ID: str = Field(default="dy-golfcart-backend", description="MQTT client ID")
    MQTT_KEEPALIVE: int = 60
    MQTT_QOS: int = 1
    MQTT_USE_TLS: bool = True
    
    # MQTT Topics Structure
    MQTT_TOPIC_PREFIX: str = "dy/golfcart"
    MQTT_TELEMETRY_TOPIC: str = "{prefix}/cart/{cart_id}/telemetry"
    MQTT_STATUS_TOPIC: str = "{prefix}/cart/{cart_id}/status"
    MQTT_CONFIG_TOPIC: str = "{prefix}/cart/{cart_id}/config"
    MQTT_COMMAND_TOPIC: str = "{prefix}/cart/{cart_id}/command"
    MQTT_EVENT_TOPIC: str = "{prefix}/events/{event_type}"
    
    # =============================================================================
    # FILE STORAGE CONFIGURATION
    # =============================================================================
    USE_LOCAL_STORAGE: bool = Field(default=True, description="Use local file storage")
    UPLOAD_DIR: str = Field(default="./uploads", description="Local upload directory")
    MAX_FILE_SIZE: str = Field(default="50MB", description="Maximum file upload size")
    
    # S3 Configuration (optional)
    USE_S3: bool = Field(default=False, description="Use S3 for file storage")
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_S3_BUCKET: Optional[str] = None
    AWS_REGION: str = "us-west-2"
    
    @property
    def max_upload_size_bytes(self) -> int:
        """Convert MAX_FILE_SIZE to bytes."""
        size_str = self.MAX_FILE_SIZE.upper()
        if size_str.endswith('MB'):
            return int(size_str[:-2]) * 1024 * 1024
        elif size_str.endswith('KB'):
            return int(size_str[:-2]) * 1024
        elif size_str.endswith('GB'):
            return int(size_str[:-2]) * 1024 * 1024 * 1024
        return int(size_str)
    
    # WebSocket (for real-time dashboard)
    WS_HEARTBEAT_INTERVAL: int = 30  # seconds
    
    # Telemetry Settings
    TELEMETRY_BATCH_SIZE: int = 100  # Batch insert size
    TELEMETRY_RETENTION_DAYS: int = 30  # Keep 30 days for MVP
    
    # Geofence Settings
    GEOFENCE_CHECK_INTERVAL: int = 5  # seconds
    GEOFENCE_VIOLATION_THRESHOLD: int = 3  # violations before alert
    DEFAULT_SPEED_LIMIT: float = 20.0  # km/h
    
    # System Limits (MVP)
    MAX_CARTS_PER_COURSE: int = 100
    MAX_COURSES_PER_SYSTEM: int = 10
    MAX_TELEMETRY_POINTS_PER_REQUEST: int = 1000
    
    # =============================================================================
    # LOGGING & MONITORING
    # =============================================================================
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    LOG_FORMAT: str = Field(default="json", description="Log format (json/text)")
    
    @validator('LOG_LEVEL')
    def set_log_level(cls, v: str, values: dict) -> str:
        """Auto-set log level based on environment."""
        env = values.get('ENVIRONMENT', 'development')
        debug = values.get('DEBUG', True)
        if env == 'development' and debug:
            return 'DEBUG'
        elif env == 'production':
            return 'WARNING'
        return v.upper()
    
    # =============================================================================
    # CORS SETTINGS
    # =============================================================================
    ALLOWED_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"],
        description="Allowed CORS origins"
    )
    ALLOWED_METHODS: List[str] = Field(
        default=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        description="Allowed HTTP methods"
    )
    ALLOWED_HEADERS: List[str] = Field(
        default=["*"],
        description="Allowed headers"
    )
    CORS_ALLOW_CREDENTIALS: bool = True
    
    @validator('ALLOWED_ORIGINS', pre=True)
    def parse_cors_origins(cls, v) -> List[str]:
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(',') if origin.strip()]
        return v
    
    # =============================================================================
    # FEATURE FLAGS
    # =============================================================================
    FEATURE_AUTONOMOUS_DRIVING: bool = Field(default=True, description="Enable autonomous features")
    FEATURE_ROUTE_OPTIMIZATION: bool = Field(default=True, description="Enable route optimization")
    FEATURE_REAL_TIME_TRACKING: bool = Field(default=True, description="Enable real-time tracking")
    FEATURE_GEOFENCING: bool = Field(default=True, description="Enable geofencing")
    FEATURE_MAINTENANCE_ALERTS: bool = Field(default=True, description="Enable maintenance alerts")
    FEATURE_WEATHER_INTEGRATION: bool = Field(default=False, description="Enable weather integration")
    FEATURE_ADVANCED_ANALYTICS: bool = Field(default=True, description="Enable advanced analytics")
    
    class Config:
        # Dynamically determine which env file to load
        env_file = get_env_file()
        case_sensitive = True
        extra = "ignore"  # Ignore extra environment variables
        
        # Allow environment variables to override file values
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    env_file = get_env_file()
    if os.getenv("DEBUG_CONFIG") == "true":
        print(f"🔧 Loading configuration from: {env_file}")
    return Settings()


# Global settings instance
settings = get_settings()


# Environment-specific helpers
def is_development() -> bool:
    """Check if running in development mode."""
    return settings.ENVIRONMENT == "development"


def is_production() -> bool:
    """Check if running in production mode."""
    return settings.ENVIRONMENT == "production"


def is_testing() -> bool:
    """Check if running in test mode."""
    return settings.ENVIRONMENT == "test" or bool(os.getenv("PYTEST_CURRENT_TEST"))