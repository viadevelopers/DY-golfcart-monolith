"""
Database configuration and session management.
PostgreSQL with PostGIS extension for geospatial data.
"""
from sqlalchemy import create_engine, event, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
from contextlib import contextmanager
from typing import Generator

from app.core.config import settings


# Create database engine
if settings.DEBUG:
    # Use NullPool for development - no pool parameters
    engine = create_engine(
        settings.DATABASE_URL,
        echo=settings.DATABASE_ECHO,
        poolclass=NullPool,
    )
else:
    # Use connection pooling for production
    engine = create_engine(
        settings.DATABASE_URL,
        pool_size=settings.DATABASE_POOL_SIZE,
        max_overflow=settings.DATABASE_MAX_OVERFLOW,
        echo=settings.DATABASE_ECHO,
    )

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency to get database session.
    Usage: db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """
    Context manager for database session.
    Usage: with get_db_context() as db: ...
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db() -> None:
    """
    Initialize database with required extensions and tables.
    Creates tables and PostGIS extension on application startup.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    with engine.begin() as conn:
        # Enable PostGIS extension
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\""))
        
        # Create schema if needed
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS golfcart"))
        
        logger.info("Database extensions initialized")
    
    # Import all models to ensure they are registered with SQLAlchemy
    # This is crucial for table creation
    from app.models import (
        # Users
        ManufacturerUser, GolfCourseUser,
        # Maps (Independent lifecycle - Title 1)
        Map,
        # Golf Course
        GolfCourse, GolfCourseMap, Hole, Route, Geofence,
        # Cart
        CartModel, GolfCart, CartRegistration,
        # Operations
        CartAssignment, MaintenanceLog,
        # Telemetry
        CartTelemetry, CartEvent
    )
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Log created tables
    logger.info(f"Created/verified {len(Base.metadata.sorted_tables)} tables")
    for table in Base.metadata.sorted_tables:
        logger.debug(f"  - Table: {table.name}")
    
    # Verify Map table specifically
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'maps'
            );
        """))
        
        if result.scalar():
            logger.info("✅ Map table verified and ready for use")


def check_db_connection() -> bool:
    """Check if database is accessible."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False