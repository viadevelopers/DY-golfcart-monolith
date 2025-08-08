"""Commands for updating golf cart status."""

from dataclasses import dataclass
from uuid import UUID

from app.domain.fleet.repositories import GolfCartRepository
from app.domain.shared.exceptions import EntityNotFound, BusinessRuleViolation


@dataclass
class StartTripCommand:
    """Command to start a cart trip."""
    cart_id: UUID


@dataclass
class StopTripCommand:
    """Command to stop a cart trip."""
    cart_id: UUID


@dataclass
class StartMaintenanceCommand:
    """Command to start cart maintenance."""
    cart_id: UUID


@dataclass
class CompleteMaintenanceCommand:
    """Command to complete cart maintenance."""
    cart_id: UUID


@dataclass
class ChargeBatteryCommand:
    """Command to charge cart battery."""
    cart_id: UUID
    charge_amount: float


class CartStatusHandlers:
    """Handlers for cart status commands."""
    
    def __init__(self, repository: GolfCartRepository):
        self.repository = repository
    
    async def handle_start_trip(self, command: StartTripCommand) -> None:
        """Handle start trip command."""
        cart = await self.repository.get_by_id(command.cart_id)
        if not cart:
            raise EntityNotFound(f"Cart with ID {command.cart_id} not found.")
        
        cart.start_trip()
        await self.repository.save(cart)
    
    async def handle_stop_trip(self, command: StopTripCommand) -> None:
        """Handle stop trip command."""
        cart = await self.repository.get_by_id(command.cart_id)
        if not cart:
            raise EntityNotFound(f"Cart with ID {command.cart_id} not found.")
        
        cart.stop_trip()
        await self.repository.save(cart)
    
    async def handle_start_maintenance(self, command: StartMaintenanceCommand) -> None:
        """Handle start maintenance command."""
        cart = await self.repository.get_by_id(command.cart_id)
        if not cart:
            raise EntityNotFound(f"Cart with ID {command.cart_id} not found.")
        
        cart.start_maintenance()
        await self.repository.save(cart)
    
    async def handle_complete_maintenance(self, command: CompleteMaintenanceCommand) -> None:
        """Handle complete maintenance command."""
        cart = await self.repository.get_by_id(command.cart_id)
        if not cart:
            raise EntityNotFound(f"Cart with ID {command.cart_id} not found.")
        
        cart.complete_maintenance()
        await self.repository.save(cart)
    
    async def handle_charge_battery(self, command: ChargeBatteryCommand) -> None:
        """Handle charge battery command."""
        cart = await self.repository.get_by_id(command.cart_id)
        if not cart:
            raise EntityNotFound(f"Cart with ID {command.cart_id} not found.")
        
        if command.charge_amount <= 0:
            raise BusinessRuleViolation("Charge amount must be positive.")
        
        cart.charge_battery(command.charge_amount)
        await self.repository.save(cart)