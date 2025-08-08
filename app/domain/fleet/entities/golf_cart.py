"""Golf Cart domain entity with rich business logic."""

from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from app.domain.shared import Entity
from app.domain.shared.cart_status import CartStatus
from app.domain.shared.exceptions import BusinessRuleViolation
from app.domain.fleet.value_objects import (
    CartNumber,
    Position,
    Battery,
    Velocity
)
from app.domain.fleet.events import (
    CartRegistered,
    CartStarted,
    CartStopped,
    PositionUpdated,
    BatteryLow,
    BatteryCritical,
    CartStatusChanged,
    MaintenanceRequired
)


class GolfCart(Entity):
    """Golf Cart aggregate root with business logic."""
    
    # Business rules constants
    MIN_BATTERY_TO_START = 20.0
    BATTERY_CONSUMPTION_RATE = 10.0  # % per hour
    MAX_IDLE_TIME_MINUTES = 30
    MAINTENANCE_INTERVAL_DAYS = 30
    
    def __init__(
        self,
        cart_number: CartNumber,
        entity_id: Optional[UUID] = None,
        position: Optional[Position] = None,
        battery: Optional[Battery] = None,
        status: Optional[CartStatus] = None,
        last_maintenance: Optional[datetime] = None
    ):
        super().__init__(entity_id)
        self._cart_number = cart_number
        self._position = position or Position(0.0, 0.0)
        self._battery = battery or Battery(100.0)
        self._velocity = Velocity(0.0)
        self._status = status or CartStatus.IDLE
        self._last_maintenance = last_maintenance
        self._trip_started_at: Optional[datetime] = None
        self._last_position_update: Optional[datetime] = None
        
        # Raise registration event for new carts
        if not entity_id:
            self._raise_event(CartRegistered(self.id, str(cart_number)))
    
    # Properties
    @property
    def cart_number(self) -> CartNumber:
        """Get cart number."""
        return self._cart_number
    
    @property
    def position(self) -> Position:
        """Get current position."""
        return self._position
    
    @property
    def battery(self) -> Battery:
        """Get battery status."""
        return self._battery
    
    @property
    def velocity(self) -> Velocity:
        """Get current velocity."""
        return self._velocity
    
    @property
    def status(self) -> CartStatus:
        """Get current status."""
        return self._status
    
    @property
    def last_maintenance(self) -> Optional[datetime]:
        """Get last maintenance date."""
        return self._last_maintenance
    
    @property
    def is_on_trip(self) -> bool:
        """Check if cart is currently on a trip."""
        return self._status == CartStatus.RUNNING
    
    # Business Operations
    
    def start_trip(self) -> None:
        """Start a new trip."""
        # Business rule: Can only start from idle or charging status
        if not self._status.can_start_trip():
            raise BusinessRuleViolation(
                f"Cannot start trip from {self._status.value} status. "
                "Cart must be IDLE or CHARGING."
            )
        
        # Business rule: Minimum battery level required
        if not self._battery.can_start_trip():
            raise BusinessRuleViolation(
                f"Insufficient battery ({self._battery.level}%). "
                f"Minimum {self.MIN_BATTERY_TO_START}% required to start trip."
            )
        
        # Business rule: Check maintenance status
        if self._needs_maintenance():
            raise BusinessRuleViolation(
                "Cart requires maintenance before starting a new trip."
            )
        
        self._change_status(CartStatus.RUNNING)
        self._trip_started_at = datetime.utcnow()
        self._raise_event(CartStarted(self.id, self._position))
        self.mark_updated()
    
    def stop_trip(self) -> None:
        """Stop the current trip."""
        if self._status != CartStatus.RUNNING:
            raise BusinessRuleViolation(
                f"Cannot stop trip. Cart is not running (status: {self._status.value})."
            )
        
        trip_duration = None
        if self._trip_started_at:
            trip_duration = int((datetime.utcnow() - self._trip_started_at).total_seconds())
        
        self._change_status(CartStatus.IDLE)
        self._velocity = Velocity(0.0)
        self._trip_started_at = None
        self._raise_event(CartStopped(self.id, self._position, trip_duration))
        self.mark_updated()
    
    def update_position(
        self,
        latitude: float,
        longitude: float,
        velocity: float
    ) -> None:
        """Update cart position and velocity."""
        old_position = self._position
        new_position = Position(latitude, longitude)
        new_velocity = Velocity(velocity)
        
        self._position = new_position
        self._velocity = new_velocity
        
        # Auto-manage status based on velocity
        if new_velocity.is_moving() and self._status == CartStatus.IDLE:
            self.start_trip()
        elif new_velocity.is_stopped() and self._status == CartStatus.RUNNING:
            self._check_idle_timeout()
        
        # Consume battery based on movement
        if new_velocity.is_moving():
            self._consume_battery()
        
        self._last_position_update = datetime.utcnow()
        self._raise_event(PositionUpdated(
            self.id, old_position, new_position, velocity
        ))
        self.mark_updated()
    
    def charge_battery(self, amount: float) -> None:
        """Charge the battery."""
        if self._status == CartStatus.RUNNING:
            raise BusinessRuleViolation(
                "Cannot charge battery while cart is running."
            )
        
        old_battery = self._battery
        self._battery = self._battery.charge(amount)
        
        if self._status != CartStatus.CHARGING:
            self._change_status(CartStatus.CHARGING)
        
        # Check if battery is now sufficient
        if old_battery.is_low() and not self._battery.is_low():
            self._raise_event(CartStatusChanged(
                self.id, CartStatus.CHARGING, CartStatus.IDLE
            ))
            self._status = CartStatus.IDLE
        
        self.mark_updated()
    
    def start_maintenance(self) -> None:
        """Put cart into maintenance mode."""
        if self._status == CartStatus.RUNNING:
            self.stop_trip()
        
        self._change_status(CartStatus.FIXING)
        self._raise_event(MaintenanceRequired(
            self.id, "Scheduled maintenance"
        ))
        self.mark_updated()
    
    def complete_maintenance(self) -> None:
        """Complete maintenance and return cart to service."""
        if self._status != CartStatus.FIXING:
            raise BusinessRuleViolation(
                "Cart is not in maintenance mode."
            )
        
        self._last_maintenance = datetime.utcnow()
        self._battery = Battery(100.0)  # Full charge after maintenance
        self._change_status(CartStatus.IDLE)
        self.mark_updated()
    
    def decommission(self) -> None:
        """Take cart out of service permanently."""
        if self._status == CartStatus.RUNNING:
            self.stop_trip()
        
        self._change_status(CartStatus.OUT_OF_SERVICE)
        self.mark_updated()
    
    # Private helper methods
    
    def _change_status(self, new_status: CartStatus) -> None:
        """Change cart status and raise event."""
        if self._status != new_status:
            old_status = self._status
            self._status = new_status
            self._raise_event(CartStatusChanged(
                self.id, old_status, new_status
            ))
    
    def _consume_battery(self) -> None:
        """Consume battery based on usage."""
        # Calculate consumption based on time since last update
        if self._last_position_update:
            hours_elapsed = (datetime.utcnow() - self._last_position_update).total_seconds() / 3600
            consumption = self.BATTERY_CONSUMPTION_RATE * hours_elapsed * (self._velocity.speed / 20.0)
            
            old_battery = self._battery
            self._battery = self._battery.consume(consumption)
            
            # Check battery thresholds
            if not old_battery.is_critical() and self._battery.is_critical():
                self._raise_event(BatteryCritical(self.id, self._battery.level))
            elif not old_battery.is_low() and self._battery.is_low():
                self._raise_event(BatteryLow(self.id, self._battery.level))
    
    def _check_idle_timeout(self) -> None:
        """Check if cart has been idle too long and should stop trip."""
        if self._last_position_update:
            idle_time = datetime.utcnow() - self._last_position_update
            if idle_time > timedelta(minutes=self.MAX_IDLE_TIME_MINUTES):
                self.stop_trip()
    
    def _needs_maintenance(self) -> bool:
        """Check if cart needs maintenance."""
        if not self._last_maintenance:
            return True
        
        days_since_maintenance = (datetime.utcnow() - self._last_maintenance).days
        return days_since_maintenance >= self.MAINTENANCE_INTERVAL_DAYS
    
    # Domain service helpers
    
    def can_accept_reservation(self) -> bool:
        """Check if cart can accept a reservation."""
        return (
            self._status in [CartStatus.IDLE, CartStatus.CHARGING] and
            self._battery.can_start_trip() and
            not self._needs_maintenance()
        )
    
    def estimate_range(self) -> float:
        """Estimate remaining range in kilometers."""
        if not self._battery.can_start_trip():
            return 0.0
        
        # Assume average speed of 15 km/h and current battery level
        hours_remaining = self._battery.estimate_remaining_time(
            self.BATTERY_CONSUMPTION_RATE
        )
        return hours_remaining * 15.0  # km
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "id": str(self.id),
            "cart_number": str(self._cart_number),
            "position": self._position.to_dict(),
            "velocity": self._velocity.speed,
            "battery_level": self._battery.level,
            "status": self._status.value,
            "last_maintenance": self._last_maintenance.isoformat() if self._last_maintenance else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }