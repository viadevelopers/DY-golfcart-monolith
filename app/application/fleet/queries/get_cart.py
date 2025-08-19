"""Queries for retrieving golf cart information."""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from uuid import UUID

from app.domain.fleet.repositories import GolfCartRepository
from app.domain.fleet.value_objects import CartNumber
from app.domain.shared.cart_status import CartStatus


@dataclass
class GetCartByIdQuery:
    """Query to get cart by ID."""
    cart_id: UUID


@dataclass
class GetCartByNumberQuery:
    """Query to get cart by cart number."""
    cart_number: str


@dataclass
class GetAllCartsQuery:
    """Query to get all carts with filtering."""
    skip: int = 0
    limit: int = 100
    status: Optional[str] = None


@dataclass
class GetCartsByStatusQuery:
    """Query to get carts by status."""
    status: str


@dataclass
class GetRunningCartsQuery:
    """Query to get all running carts."""
    pass


@dataclass
class GetCartsNeedingMaintenanceQuery:
    """Query to get carts needing maintenance."""
    pass


class CartQueryHandler:
    """Handler for cart queries."""
    
    def __init__(self, repository: GolfCartRepository):
        self.repository = repository
    
    async def get_by_id(self, query: GetCartByIdQuery) -> Optional[Dict[str, Any]]:
        """Get cart by ID."""
        cart = await self.repository.get_by_id(query.cart_id)
        return cart.to_dict() if cart else None
    
    async def get_by_number(self, query: GetCartByNumberQuery) -> Optional[Dict[str, Any]]:
        """Get cart by cart number."""
        cart_number = CartNumber(query.cart_number)
        cart = await self.repository.get_by_cart_number(cart_number)
        return cart.to_dict() if cart else None
    
    async def get_all(self, query: GetAllCartsQuery) -> Dict[str, Any]:
        """Get all carts with pagination."""
        status = CartStatus(query.status) if query.status else None
        
        carts = await self.repository.get_all(
            skip=query.skip,
            limit=query.limit,
            status=status
        )
        total = await self.repository.count(status=status)
        
        return {
            "total": total,
            "carts": [cart.to_dict() for cart in carts]
        }
    
    async def get_by_status(self, query: GetCartsByStatusQuery) -> List[Dict[str, Any]]:
        """Get carts by status."""
        status = CartStatus(query.status)
        carts = await self.repository.get_by_status(status)
        return [cart.to_dict() for cart in carts]
    
    async def get_running(self, query: GetRunningCartsQuery) -> List[Dict[str, Any]]:
        """Get all running carts."""
        carts = await self.repository.get_running_carts()
        return [cart.to_dict() for cart in carts]
    
    async def get_needing_maintenance(self, query: GetCartsNeedingMaintenanceQuery) -> List[Dict[str, Any]]:
        """Get carts needing maintenance."""
        carts = await self.repository.get_carts_needing_maintenance()
        return [cart.to_dict() for cart in carts]