"""
Unit of Work pattern implementation for transaction management.

This pattern ensures that all operations within a business transaction
are committed or rolled back as a single unit.
"""

from typing import Optional, Type, TypeVar, Generic
from contextlib import asynccontextmanager
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.domain.fleet.repositories import GolfCartRepository
from app.infrastructure.persistence.repositories.sqlalchemy_cart_repository import (
    SQLAlchemyCartRepository
)

T = TypeVar('T')


class UnitOfWork:
    """
    Unit of Work pattern implementation.
    
    Manages database transactions and repository instances.
    Ensures all operations within a context are atomic.
    """
    
    def __init__(self, session_factory=None):
        """
        Initialize Unit of Work.
        
        Args:
            session_factory: Optional custom session factory.
                           Defaults to SessionLocal from database module.
        """
        self.session_factory = session_factory or SessionLocal
        self._session: Optional[Session] = None
        self._golf_cart_repository: Optional[GolfCartRepository] = None
    
    @property
    def session(self) -> Session:
        """Get the current session."""
        if not self._session:
            raise RuntimeError("Unit of Work not started. Use 'async with' context manager.")
        return self._session
    
    @property
    def golf_cart_repository(self) -> GolfCartRepository:
        """
        Get the golf cart repository instance.
        
        Lazy initialization ensures repository uses the current session.
        """
        if not self._golf_cart_repository:
            self._golf_cart_repository = SQLAlchemyCartRepository(self.session)
        return self._golf_cart_repository
    
    async def __aenter__(self):
        """
        Enter the Unit of Work context.
        
        Creates a new database session.
        """
        self._session = self.session_factory()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Exit the Unit of Work context.
        
        Commits on success, rolls back on exception.
        """
        if exc_type:
            await self.rollback()
        else:
            await self.commit()
        
        # Always close the session
        self._session.close()
        self._session = None
        self._golf_cart_repository = None
    
    async def commit(self):
        """Commit the current transaction."""
        if self._session:
            self._session.commit()
    
    async def rollback(self):
        """Rollback the current transaction."""
        if self._session:
            self._session.rollback()
    
    async def flush(self):
        """
        Flush pending changes to database without committing.
        
        Useful for getting generated IDs before commit.
        """
        if self._session:
            self._session.flush()


class AsyncUnitOfWork(UnitOfWork):
    """
    Async-friendly Unit of Work with context manager support.
    
    This version provides better async/await integration.
    """
    
    @asynccontextmanager
    async def transaction(self):
        """
        Create a transaction context.
        
        Usage:
            async with uow.transaction():
                # Your transactional code here
                await uow.golf_cart_repository.save(cart)
        """
        await self.__aenter__()
        try:
            yield self
        except Exception:
            await self.__aexit__(Exception, None, None)
            raise
        else:
            await self.__aexit__(None, None, None)


def get_unit_of_work() -> UnitOfWork:
    """
    Factory function for Unit of Work.
    
    Used for dependency injection in FastAPI.
    """
    return UnitOfWork()


async def get_async_unit_of_work() -> AsyncUnitOfWork:
    """
    Factory function for Async Unit of Work.
    
    Used for dependency injection in FastAPI with async support.
    """
    return AsyncUnitOfWork()