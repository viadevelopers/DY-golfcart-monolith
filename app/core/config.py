"""
Configuration settings for DY-GOLFCART MVP system.
Simplified monolith architecture without Kafka.
"""
from typing import Optional
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings for MVP."""
    
    # Application
    APP_NAME: str = "DY-GOLFCART Management System"
    APP_VERSION: str = "1.0.0-MVP"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = True  # MVP mode
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Database (PostgreSQL with PostGIS)
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/golfcart_db"
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10
    DATABASE_ECHO: bool = False
    
    # Redis (for caching and real-time data)
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_TTL: int = 300  # 5 minutes for MVP
    
    # JWT Authentication
    SECRET_KEY: str = "dy-golfcart-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60  # 1 hour for MVP
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # MQTT Configuration (EMQX - Already Deployed)
    MQTT_BROKER_URL: str = "emqx.dev.viasoft.ai"
    MQTT_PORT: int = 8883  # TLS port
    MQTT_WS_PORT: int = 8084  # WebSocket port
    MQTT_USERNAME: Optional[str] = "admin"
    MQTT_PASSWORD: Optional[str] = "public"
    MQTT_CLIENT_ID: str = "dy-golfcart-backend"
    MQTT_KEEPALIVE: int = 60
    MQTT_QOS: int = 1
    MQTT_USE_TLS: bool = True
    MQTT_ENABLED: bool = True
    
    # MQTT Topics Structure
    MQTT_TOPIC_PREFIX: str = "dy/golfcart"
    MQTT_TELEMETRY_TOPIC: str = "{prefix}/cart/{cart_id}/telemetry"
    MQTT_STATUS_TOPIC: str = "{prefix}/cart/{cart_id}/status"
    MQTT_CONFIG_TOPIC: str = "{prefix}/cart/{cart_id}/config"
    MQTT_COMMAND_TOPIC: str = "{prefix}/cart/{cart_id}/command"
    MQTT_EVENT_TOPIC: str = "{prefix}/events/{event_type}"
    
    # S3 Configuration (for map storage) - MVP uses local storage
    USE_S3: bool = False  # Disabled for MVP
    UPLOAD_DIR: str = "./uploads"  # Local storage for MVP
    MAX_UPLOAD_SIZE: int = 100 * 1024 * 1024  # 100MB
    
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
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    
    # CORS Settings
    CORS_ORIGINS: list = ["http://localhost:3000", "http://localhost:8080"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list = ["*"]
    CORS_ALLOW_HEADERS: list = ["*"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()