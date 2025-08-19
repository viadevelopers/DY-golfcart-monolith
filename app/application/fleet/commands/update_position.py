"""Command for updating golf cart position."""

from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from app.domain.fleet.repositories import GolfCartRepository
from app.domain.shared.exceptions import EntityNotFound


@dataclass
class UpdateCartPositionCommand:
    """Command to update cart position."""
    
    cart_id: UUID
    latitude: float
    longitude: float
    velocity: float


class UpdateCartPositionHandler:
    """Handler for UpdateCartPositionCommand."""
    
    def __init__(self, repository: GolfCartRepository):
        self.repository = repository
    
    async def handle(self, command: UpdateCartPositionCommand) -> None:
        """Execute the command."""
        # Get the cart
        cart = await self.repository.get_by_id(command.cart_id)
        if not cart:
            raise EntityNotFound(f"Cart with ID {command.cart_id} not found.")
        
        # Update position using domain logic
        cart.update_position(
            command.latitude,
            command.longitude,
            command.velocity
        )
        
        # Save changes
        await self.repository.save(cart)