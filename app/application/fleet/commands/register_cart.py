"""Command for registering a new golf cart."""

from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from app.domain.fleet.entities import GolfCart
from app.domain.fleet.value_objects import CartNumber, Position, Battery
from app.domain.fleet.repositories import GolfCartRepository
from app.domain.shared.cart_status import CartStatus
from app.domain.shared.exceptions import BusinessRuleViolation


@dataclass
class RegisterCartCommand:
    """Command to register a new golf cart."""
    
    cart_number: str
    initial_lat: float = 0.0
    initial_lng: float = 0.0
    initial_battery: float = 100.0
    initial_status: str = "idle"


class RegisterCartHandler:
    """Handler for RegisterCartCommand."""
    
    def __init__(self, repository: GolfCartRepository):
        self.repository = repository
    
    async def handle(self, command: RegisterCartCommand) -> UUID:
        """Execute the command and return the new cart ID."""
        # Create value objects
        cart_number = CartNumber(command.cart_number)
        
        # Check if cart number already exists
        if await self.repository.cart_number_exists(cart_number):
            raise BusinessRuleViolation(
                f"Cart with number {command.cart_number} already exists."
            )
        
        # Create domain entity
        cart = GolfCart(
            cart_number=cart_number,
            position=Position(command.initial_lat, command.initial_lng),
            battery=Battery(command.initial_battery),
            status=CartStatus(command.initial_status)
        )
        
        # Save to repository
        saved_cart = await self.repository.save(cart)
        
        # Return the cart ID
        return saved_cart.id