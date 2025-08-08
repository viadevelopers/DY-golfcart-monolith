"""Golf Cart Application Service - Facade for all fleet operations."""

from typing import Dict, List, Optional, Any
from uuid import UUID
from abc import ABC, abstractmethod

from app.domain.fleet.repositories import GolfCartRepository
from app.domain.shared.exceptions import BusinessRuleViolation, EntityNotFound

# Import commands and handlers
from app.application.fleet.commands.register_cart import (
    RegisterCartCommand, 
    RegisterCartHandler
)
from app.application.fleet.commands.update_position import (
    UpdateCartPositionCommand, 
    UpdateCartPositionHandler
)
from app.application.fleet.commands.update_status import (
    StartTripCommand,
    StopTripCommand,
    CartStatusHandlers
)

# Import queries and handler
from app.application.fleet.queries.get_cart import (
    GetCartByIdQuery,
    GetCartByNumberQuery,
    GetAllCartsQuery,
    GetCartsByStatusQuery,
    GetRunningCartsQuery,
    GetCartsNeedingMaintenanceQuery,
    CartQueryHandler
)


class IGolfCartApplicationService(ABC):
    """Interface for Golf Cart Application Service."""
    
    @abstractmethod
    async def register_cart(
        self, 
        cart_number: str,
        initial_lat: float,
        initial_lng: float,
        initial_battery: float = 100.0,
        initial_status: str = "idle"
    ) -> UUID:
        """Register a new golf cart."""
        pass
    
    @abstractmethod
    async def get_cart_by_id(self, cart_id: UUID) -> Optional[Dict[str, Any]]:
        """Get cart by ID."""
        pass
    
    @abstractmethod
    async def get_cart_by_number(self, cart_number: str) -> Optional[Dict[str, Any]]:
        """Get cart by cart number."""
        pass
    
    @abstractmethod
    async def get_all_carts(
        self,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get all carts with pagination and optional filtering."""
        pass
    
    @abstractmethod
    async def update_cart_position(
        self,
        cart_id: UUID,
        latitude: float,
        longitude: float,
        velocity: float = 0.0
    ) -> None:
        """Update cart position."""
        pass
    
    @abstractmethod
    async def start_trip(self, cart_id: UUID) -> None:
        """Start a trip for a cart."""
        pass
    
    @abstractmethod
    async def stop_trip(self, cart_id: UUID) -> None:
        """Stop a trip for a cart."""
        pass
    
    @abstractmethod
    async def delete_cart(self, cart_id: UUID) -> bool:
        """Delete a cart."""
        pass
    
    @abstractmethod
    async def get_carts_by_status(self, status: str) -> List[Dict[str, Any]]:
        """Get all carts with specific status."""
        pass
    
    @abstractmethod
    async def get_running_carts(self) -> List[Dict[str, Any]]:
        """Get all running carts."""
        pass
    
    @abstractmethod
    async def get_carts_needing_maintenance(self) -> List[Dict[str, Any]]:
        """Get carts needing maintenance."""
        pass


class GolfCartApplicationService(IGolfCartApplicationService):
    """
    Application Service for Golf Cart operations.
    
    This service acts as a facade between the presentation layer and domain/infrastructure layers.
    It orchestrates commands and queries, ensuring proper separation of concerns.
    """
    
    def __init__(self, repository: GolfCartRepository):
        """
        Initialize the application service with repository dependency.
        
        Note: Repository is injected, not created here. This maintains proper
        dependency inversion - the service depends on the abstraction (interface),
        not the concrete implementation.
        """
        self.repository = repository
        
        # Initialize handlers with the injected repository
        self.register_handler = RegisterCartHandler(repository)
        self.position_handler = UpdateCartPositionHandler(repository)
        self.status_handler = CartStatusHandlers(repository)
        self.query_handler = CartQueryHandler(repository)
    
    async def register_cart(
        self, 
        cart_number: str,
        initial_lat: float,
        initial_lng: float,
        initial_battery: float = 100.0,
        initial_status: str = "idle"
    ) -> UUID:
        """Register a new golf cart."""
        command = RegisterCartCommand(
            cart_number=cart_number,
            initial_lat=initial_lat,
            initial_lng=initial_lng,
            initial_battery=initial_battery,
            initial_status=initial_status
        )
        
        try:
            return await self.register_handler.handle(command)
        except BusinessRuleViolation:
            # Re-raise domain exceptions
            raise
        except Exception as e:
            # Log and wrap infrastructure exceptions
            raise Exception(f"Failed to register cart: {str(e)}")
    
    async def get_cart_by_id(self, cart_id: UUID) -> Optional[Dict[str, Any]]:
        """Get cart by ID."""
        query = GetCartByIdQuery(cart_id)
        return await self.query_handler.get_by_id(query)
    
    async def get_cart_by_number(self, cart_number: str) -> Optional[Dict[str, Any]]:
        """Get cart by cart number."""
        query = GetCartByNumberQuery(cart_number)
        return await self.query_handler.get_by_number(query)
    
    async def get_all_carts(
        self,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get all carts with pagination and optional filtering."""
        query = GetAllCartsQuery(skip=skip, limit=limit, status=status)
        return await self.query_handler.get_all(query)
    
    async def update_cart_position(
        self,
        cart_id: UUID,
        latitude: float,
        longitude: float,
        velocity: float = 0.0
    ) -> None:
        """Update cart position."""
        command = UpdateCartPositionCommand(
            cart_id=cart_id,
            latitude=latitude,
            longitude=longitude,
            velocity=velocity
        )
        
        try:
            await self.position_handler.handle(command)
        except (EntityNotFound, BusinessRuleViolation):
            # Re-raise domain exceptions
            raise
        except Exception as e:
            # Log and wrap infrastructure exceptions
            raise Exception(f"Failed to update cart position: {str(e)}")
    
    async def start_trip(self, cart_id: UUID) -> None:
        """Start a trip for a cart."""
        command = StartTripCommand(cart_id)
        
        try:
            await self.status_handler.handle_start_trip(command)
        except (EntityNotFound, BusinessRuleViolation):
            # Re-raise domain exceptions
            raise
        except Exception as e:
            # Log and wrap infrastructure exceptions
            raise Exception(f"Failed to start trip: {str(e)}")
    
    async def stop_trip(self, cart_id: UUID) -> None:
        """Stop a trip for a cart."""
        command = StopTripCommand(cart_id)
        
        try:
            await self.status_handler.handle_stop_trip(command)
        except (EntityNotFound, BusinessRuleViolation):
            # Re-raise domain exceptions
            raise
        except Exception as e:
            # Log and wrap infrastructure exceptions
            raise Exception(f"Failed to stop trip: {str(e)}")
    
    async def delete_cart(self, cart_id: UUID) -> bool:
        """Delete a cart."""
        try:
            return await self.repository.delete(cart_id)
        except Exception as e:
            # Log and wrap infrastructure exceptions
            raise Exception(f"Failed to delete cart: {str(e)}")
    
    async def get_carts_by_status(self, status: str) -> List[Dict[str, Any]]:
        """Get all carts with specific status."""
        query = GetCartsByStatusQuery(status)
        return await self.query_handler.get_by_status(query)
    
    async def get_running_carts(self) -> List[Dict[str, Any]]:
        """Get all running carts."""
        query = GetRunningCartsQuery()
        return await self.query_handler.get_running(query)
    
    async def get_carts_needing_maintenance(self) -> List[Dict[str, Any]]:
        """Get carts needing maintenance."""
        query = GetCartsNeedingMaintenanceQuery()
        return await self.query_handler.get_needing_maintenance(query)