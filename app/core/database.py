"""
Database configuration and session management.
PostgreSQL with PostGIS extension for geospatial data.
"""
from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
from contextlib import contextmanager
from typing import Generator

from app.core.config import settings


# Create database engine
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    echo=settings.DATABASE_ECHO,
    # Use NullPool for development to avoid connection issues
    poolclass=NullPool if settings.DEBUG else None,
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
    Initialize database with required extensions.
    Creates tables and PostGIS extension.
    """
    with engine.begin() as conn:
        # Enable PostGIS extension
        conn.execute("CREATE EXTENSION IF NOT EXISTS postgis")
        conn.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"")
        
        # Create schema if needed
        conn.execute("CREATE SCHEMA IF NOT EXISTS golfcart")
    
    # Create all tables
    Base.metadata.create_all(bind=engine)


def check_db_connection() -> bool:
    """Check if database is accessible."""
    try:
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        return True
    except Exception:
        return False