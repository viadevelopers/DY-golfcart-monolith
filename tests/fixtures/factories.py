"""Test factories for creating domain objects."""

import factory
from factory import fuzzy
from datetime import datetime, timedelta
from uuid import uuid4

from app.domain.fleet.entities import GolfCart
from app.domain.fleet.value_objects import CartNumber, Position, Battery, Velocity
from app.domain.shared.cart_status import CartStatus


class CartNumberFactory(factory.Factory):
    """Factory for creating CartNumber value objects."""
    
    class Meta:
        model = CartNumber
    
    value = factory.Sequence(lambda n: f"CART{n:03d}")


class PositionFactory(factory.Factory):
    """Factory for creating Position value objects."""
    
    class Meta:
        model = Position
    
    latitude = fuzzy.FuzzyFloat(37.0, 38.0)  # San Francisco area
    longitude = fuzzy.FuzzyFloat(-123.0, -122.0)


class BatteryFactory(factory.Factory):
    """Factory for creating Battery value objects."""
    
    class Meta:
        model = Battery
    
    level = fuzzy.FuzzyFloat(20.0, 100.0)


class VelocityFactory(factory.Factory):
    """Factory for creating Velocity value objects."""
    
    class Meta:
        model = Velocity
    
    speed = fuzzy.FuzzyFloat(0.0, 25.0)


class GolfCartFactory(factory.Factory):
    """Factory for creating GolfCart entities."""
    
    class Meta:
        model = GolfCart
    
    cart_number = factory.SubFactory(CartNumberFactory)
    entity_id = factory.LazyFunction(uuid4)
    position = factory.SubFactory(PositionFactory)
    battery = factory.SubFactory(BatteryFactory)
    status = fuzzy.FuzzyChoice([
        CartStatus.IDLE,
        CartStatus.RUNNING,
        CartStatus.CHARGING
    ])
    last_maintenance = fuzzy.FuzzyDateTime(
        datetime.now() - timedelta(days=30),
        datetime.now()
    )


class IdleCartFactory(GolfCartFactory):
    """Factory for creating idle golf carts."""
    
    status = CartStatus.IDLE
    battery = factory.LazyFunction(lambda: Battery(80.0))


class RunningCartFactory(GolfCartFactory):
    """Factory for creating running golf carts."""
    
    status = CartStatus.RUNNING
    battery = factory.LazyFunction(lambda: Battery(60.0))


class ChargingCartFactory(GolfCartFactory):
    """Factory for creating charging golf carts."""
    
    status = CartStatus.CHARGING
    battery = factory.LazyFunction(lambda: Battery(30.0))


class LowBatteryCartFactory(GolfCartFactory):
    """Factory for creating low battery golf carts."""
    
    status = CartStatus.IDLE
    battery = factory.LazyFunction(lambda: Battery(15.0))


class MaintenanceRequiredCartFactory(GolfCartFactory):
    """Factory for creating carts that need maintenance."""
    
    status = CartStatus.IDLE
    last_maintenance = factory.LazyFunction(
        lambda: datetime.now() - timedelta(days=45)
    )