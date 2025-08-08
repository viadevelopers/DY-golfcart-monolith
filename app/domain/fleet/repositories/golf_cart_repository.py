"""Repository interface for GolfCart aggregate."""

from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from app.domain.shared.cart_status import CartStatus
from app.domain.fleet.entities import GolfCart
from app.domain.fleet.value_objects import CartNumber


class GolfCartRepository(ABC):
    """Abstract repository interface for GolfCart aggregate."""
    
    @abstractmethod
    async def get_by_id(self, cart_id: UUID) -> Optional[GolfCart]:
        """Get cart by ID."""
        pass
    
    @abstractmethod
    async def get_by_cart_number(self, cart_number: CartNumber) -> Optional[GolfCart]:
        """Get cart by cart number."""
        pass
    
    @abstractmethod
    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        status: Optional[CartStatus] = None
    ) -> List[GolfCart]:
        """Get all carts with optional filtering."""
        pass
    
    @abstractmethod
    async def get_by_status(self, status: CartStatus) -> List[GolfCart]:
        """Get all carts with specific status."""
        pass
    
    @abstractmethod
    async def get_running_carts(self) -> List[GolfCart]:
        """Get all currently running carts."""
        pass
    
    @abstractmethod
    async def get_carts_needing_maintenance(self) -> List[GolfCart]:
        """Get carts that need maintenance."""
        pass
    
    @abstractmethod
    async def save(self, cart: GolfCart) -> GolfCart:
        """Save cart (create or update)."""
        pass
    
    @abstractmethod
    async def delete(self, cart_id: UUID) -> bool:
        """Delete cart by ID."""
        pass
    
    @abstractmethod
    async def exists(self, cart_id: UUID) -> bool:
        """Check if cart exists by ID."""
        pass
    
    @abstractmethod
    async def cart_number_exists(self, cart_number: CartNumber) -> bool:
        """Check if cart number already exists."""
        pass
    
    @abstractmethod
    async def count(self, status: Optional[CartStatus] = None) -> int:
        """Count carts with optional status filter."""
        pass