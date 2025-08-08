"""Dependency injection for Fleet domain."""

from functools import lru_cache

from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.infrastructure.persistence.repositories.sqlalchemy_cart_repository import (
    SQLAlchemyCartRepository
)
from app.infrastructure.persistence.unit_of_work import (
    UnitOfWork,
    get_unit_of_work
)
from app.application.fleet.services.golf_cart_application_service import (
    GolfCartApplicationService,
    IGolfCartApplicationService
)


def get_golf_cart_repository(db: Session = Depends(get_db)):
    """
    Factory function for GolfCartRepository.
    
    This is where we decide which concrete implementation to use.
    Could easily switch to MongoDB, Redis, etc. without changing
    the application or presentation layers.
    """
    return SQLAlchemyCartRepository(db)


def get_golf_cart_application_service(
    db: Session = Depends(get_db)
) -> IGolfCartApplicationService:
    """
    Factory function for GolfCartApplicationService.
    
    This creates the application service with all its dependencies injected.
    The presentation layer will only depend on this function.
    """
    repository = get_golf_cart_repository(db)
    return GolfCartApplicationService(repository)


# Optional: Create a cached version if you want singleton behavior within a request
@lru_cache()
def get_cached_golf_cart_service() -> type[IGolfCartApplicationService]:
    """
    Returns the service class for dependency injection.
    Can be useful for testing or when you need consistent service instances.
    """
    return GolfCartApplicationService


# New: Unit of Work based dependency injection
async def get_golf_cart_service_with_uow() -> IGolfCartApplicationService:
    """
    Factory function for GolfCartApplicationService using Unit of Work pattern.
    
    This provides better transaction management with automatic commit/rollback.
    Each request gets its own Unit of Work instance.
    """
    uow = get_unit_of_work()
    async with uow:
        repository = uow.golf_cart_repository
        return GolfCartApplicationService(repository)
