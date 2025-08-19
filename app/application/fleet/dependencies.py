"""Dependency injection for Fleet domain."""

from functools import lru_cache

from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.redis import get_redis_connection
from app.infrastructure.event_bus import EventBus, EventDispatcher
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
from app.application.event_handlers.logging_handler import log_event_handler
from app.application.event_handlers.notification_handler import notification_handler
from app.application.event_handlers.auditing_handler import auditing_handler


@lru_cache()
def get_event_bus():
    """Get a singleton instance of the EventBus."""
    redis_conn = get_redis_connection()
    return EventBus(redis_conn)


@lru_cache()
def get_event_dispatcher():
    """Get a singleton instance of the EventDispatcher."""
    event_bus = get_event_bus()
    dispatcher = EventDispatcher(event_bus)

    # Register handlers
    # A more advanced system might use decorators or discovery
    # to find and register handlers automatically.
    dispatcher.register("CartRegistered", log_event_handler)
    dispatcher.register("CartStarted", log_event_handler)
    dispatcher.register("CartStopped", log_event_handler)
    dispatcher.register("PositionUpdated", log_event_handler)
    dispatcher.register("BatteryLow", log_event_handler)
    dispatcher.register("BatteryCritical", log_event_handler)
    dispatcher.register("CartStatusChanged", log_event_handler)
    dispatcher.register("MaintenanceRequired", log_event_handler)

    # Register notification handlers for specific events
    dispatcher.register("CartStatusChanged", notification_handler)
    dispatcher.register("BatteryCritical", notification_handler)

    # Register the auditing handler for all events
    all_events = [
        "CartRegistered", "CartStarted", "CartStopped", "PositionUpdated",
        "BatteryLow", "BatteryCritical", "CartStatusChanged", "MaintenanceRequired"
    ]
    for event_name in all_events:
        dispatcher.register(event_name, auditing_handler)

    return dispatcher


def get_golf_cart_repository(
    db: Session = Depends(get_db),
    event_bus: EventBus = Depends(get_event_bus)
):
    """
    Factory function for GolfCartRepository.
    
    This is where we decide which concrete implementation to use.
    Could easily switch to MongoDB, Redis, etc. without changing
    the application or presentation layers.
    """
    return SQLAlchemyCartRepository(db, event_bus)


def get_golf_cart_application_service(
    db: Session = Depends(get_db),
    event_bus: EventBus = Depends(get_event_bus)
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
