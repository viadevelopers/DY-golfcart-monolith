"""
DY-GOLFCART Management System API
MVP Monolith Architecture
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from contextlib import asynccontextmanager
import logging
import sys

from app.core.config import settings
from app.core.database import init_db, check_db_connection

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifecycle manager.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting DY-GOLFCART Management System...")
    
    # Skip database checks in testing environment
    import os
    is_testing = os.getenv("DATABASE_URL", "").endswith("golfcart_test") or "pytest" in sys.modules
    
    if not is_testing:
        # Check database connection
        if not check_db_connection():
            logger.error("Failed to connect to database")
            raise RuntimeError("Database connection failed")
        
        # Initialize database
        try:
            init_db()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise
    else:
        logger.info("Skipping database initialization (testing mode)")
    
    # Initialize MQTT service
    try:
        from app.services.mqtt_service import initialize_mqtt_service
        await initialize_mqtt_service()
        logger.info("MQTT service initialized successfully")
    except Exception as e:
        logger.warning(f"MQTT service initialization failed: {e}")
        # Don't fail startup if MQTT is unavailable
    
    # TODO: Initialize Redis client
    
    logger.info("Application started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down DY-GOLFCART Management System...")
    # Cleanup MQTT connections
    try:
        from app.services.mqtt_service import shutdown_mqtt_service
        await shutdown_mqtt_service()
        logger.info("MQTT service shutdown complete")
    except Exception as e:
        logger.warning(f"MQTT service shutdown error: {e}")
    
    # TODO: Cleanup Redis connections
    logger.info("Application shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Autonomous Golf Cart Management Platform - MVP API",
    docs_url=f"{settings.API_V1_PREFIX}/docs",
    redoc_url=f"{settings.API_V1_PREFIX}/redoc",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)

# Add compression middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "database": check_db_connection()
    }

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "DY-GOLFCART Management System API",
        "version": settings.APP_VERSION,
        "docs": f"{settings.API_V1_PREFIX}/docs"
    }

# Include routers
from app.api import auth, golf_courses, carts

app.include_router(
    auth.router,
    prefix=f"{settings.API_V1_PREFIX}/auth",
    tags=["Auth"]
)

app.include_router(
    golf_courses.router,
    prefix=f"{settings.API_V1_PREFIX}/golf-courses",
    tags=["Golf Courses"]
)

app.include_router(
    carts.router,
    prefix=f"{settings.API_V1_PREFIX}/carts",
    tags=["Carts"]
)

# TODO: Add more routers as they are implemented
# app.include_router(users.router, prefix=f"{settings.API_V1_PREFIX}/users", tags=["Users"])
# app.include_router(telemetry.router, prefix=f"{settings.API_V1_PREFIX}/telemetry", tags=["Telemetry"])
# app.include_router(operations.router, prefix=f"{settings.API_V1_PREFIX}/operations", tags=["Operations"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
