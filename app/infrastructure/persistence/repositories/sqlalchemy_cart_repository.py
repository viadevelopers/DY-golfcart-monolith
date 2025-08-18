"""SQLAlchemy implementation of GolfCartRepository."""

from typing import List, Optional
from uuid import UUID
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.domain.fleet.repositories import GolfCartRepository
from app.domain.fleet.entities import GolfCart
from app.domain.fleet.value_objects import CartNumber, Position, Battery, Velocity
from app.domain.shared.cart_status import CartStatus
from app.models.golf_cart import GolfCart as GolfCartModel
from app.infrastructure.event_bus import EventBus


class SQLAlchemyCartRepository(GolfCartRepository):
    """SQLAlchemy implementation of GolfCartRepository."""

    def __init__(self, db: Session, event_bus: EventBus):
        self.db = db
        self.event_bus = event_bus
    
    async def get_by_id(self, cart_id: UUID) -> Optional[GolfCart]:
        """Get cart by ID."""
        db_cart = self.db.query(GolfCartModel).filter(
            GolfCartModel.id == cart_id
        ).first()
        
        return self._to_domain(db_cart) if db_cart else None
    
    async def get_by_cart_number(self, cart_number: CartNumber) -> Optional[GolfCart]:
        """Get cart by cart number."""
        db_cart = self.db.query(GolfCartModel).filter(
            GolfCartModel.cart_number == str(cart_number)
        ).first()
        
        return self._to_domain(db_cart) if db_cart else None
    
    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        status: Optional[CartStatus] = None
    ) -> List[GolfCart]:
        """Get all carts with optional filtering."""
        query = self.db.query(GolfCartModel)
        
        if status:
            query = query.filter(GolfCartModel.status == status)
        
        db_carts = query.offset(skip).limit(limit).all()
        return [self._to_domain(cart) for cart in db_carts]
    
    async def get_by_status(self, status: CartStatus) -> List[GolfCart]:
        """Get all carts with specific status."""
        db_carts = self.db.query(GolfCartModel).filter(
            GolfCartModel.status == status
        ).all()
        
        return [self._to_domain(cart) for cart in db_carts]
    
    async def get_running_carts(self) -> List[GolfCart]:
        """Get all currently running carts."""
        return await self.get_by_status(CartStatus.RUNNING)
    
    async def get_carts_needing_maintenance(self) -> List[GolfCart]:
        """Get carts that need maintenance."""
        # Get carts that are fixing or have low battery
        db_carts = self.db.query(GolfCartModel).filter(
            or_(
                GolfCartModel.status == CartStatus.FIXING,
                GolfCartModel.battery_level < 20.0,
                GolfCartModel.last_maintenance < datetime.now(timezone.utc) - timedelta(days=30)
            )
        ).all()
        
        return [self._to_domain(cart) for cart in db_carts]
    
    async def save(self, cart: GolfCart) -> GolfCart:
        """Save cart (create or update)."""
        # Check if cart exists
        db_cart = self.db.query(GolfCartModel).filter(
            GolfCartModel.id == cart.id
        ).first()
        
        if db_cart:
            # Update existing
            self._update_model(db_cart, cart)
        else:
            # Create new
            db_cart = self._to_model(cart)
            self.db.add(db_cart)
        
        # Transaction is now managed by the session lifecycle in get_db()
        # self.db.commit()  # Removed - handled by session manager
        self.db.flush()  # Flush to get the ID without committing
        self.db.refresh(db_cart)
        
        # Process domain events
        events = cart.pull_events()
        for event in events:
            await self.event_bus.publish(event)
        
        return self._to_domain(db_cart)
    
    async def delete(self, cart_id: UUID) -> bool:
        """Delete cart by ID."""
        db_cart = self.db.query(GolfCartModel).filter(
            GolfCartModel.id == cart_id
        ).first()
        
        if not db_cart:
            return False
        
        self.db.delete(db_cart)
        # Transaction is now managed by the session lifecycle in get_db()
        # self.db.commit()  # Removed - handled by session manager
        self.db.flush()  # Ensure delete is registered
        return True
    
    async def exists(self, cart_id: UUID) -> bool:
        """Check if cart exists by ID."""
        return self.db.query(GolfCartModel).filter(
            GolfCartModel.id == cart_id
        ).count() > 0
    
    async def cart_number_exists(self, cart_number: CartNumber) -> bool:
        """Check if cart number already exists."""
        return self.db.query(GolfCartModel).filter(
            GolfCartModel.cart_number == str(cart_number)
        ).count() > 0
    
    async def count(self, status: Optional[CartStatus] = None) -> int:
        """Count carts with optional status filter."""
        query = self.db.query(GolfCartModel)
        
        if status:
            query = query.filter(GolfCartModel.status == status)
        
        return query.count()
    
    # Private mapping methods
    
    def _to_domain(self, db_cart: GolfCartModel) -> GolfCart:
        """Convert database model to domain entity."""
        # Create the domain entity
        cart = GolfCart(
            cart_number=CartNumber(db_cart.cart_number),
            entity_id=db_cart.id,
            position=Position(db_cart.position_lat, db_cart.position_lng),
            battery=Battery(db_cart.battery_level or 100.0),
            status=CartStatus(db_cart.status) if db_cart.status else CartStatus.IDLE,
            last_maintenance=db_cart.last_maintenance
        )
        
        # Set additional properties that aren't in the constructor
        cart._velocity = Velocity(db_cart.velocity or 0.0)
        
        # Set timestamps if needed (these are typically handled by Entity base class)
        if hasattr(cart, '_created_at'):
            cart._created_at = db_cart.created_at
        if hasattr(cart, '_updated_at'):
            cart._updated_at = db_cart.updated_at
        
        return cart
    
    def _to_model(self, cart: GolfCart) -> GolfCartModel:
        """Convert domain entity to database model."""
        return GolfCartModel(
            id=cart.id,
            cart_number=str(cart.cart_number),
            position_lat=cart.position.latitude,
            position_lng=cart.position.longitude,
            velocity=cart.velocity.speed,
            status=cart.status,
            battery_level=cart.battery.level,
            last_maintenance=cart.last_maintenance,
            created_at=cart.created_at,
            updated_at=cart.updated_at
        )
    
    def _update_model(self, db_cart: GolfCartModel, cart: GolfCart) -> None:
        """Update database model from domain entity."""
        db_cart.cart_number = str(cart.cart_number)
        db_cart.position_lat = cart.position.latitude
        db_cart.position_lng = cart.position.longitude
        db_cart.velocity = cart.velocity.speed
        db_cart.status = cart.status
        db_cart.battery_level = cart.battery.level
        db_cart.last_maintenance = cart.last_maintenance
        db_cart.updated_at = cart.updated_at
