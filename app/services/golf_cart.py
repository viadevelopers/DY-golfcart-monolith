from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from app.models.golf_cart import GolfCart, CartStatus
from app.schemas.golf_cart import GolfCartCreate, GolfCartUpdate

class GolfCartService:
    def __init__(self, db: Session):
        self.db = db
    
    def create_cart(self, cart_data: GolfCartCreate) -> GolfCart:
        """Register a new golf cart"""
        db_cart = GolfCart(
            cart_number=cart_data.cart_number,
            position_lat=cart_data.position.lat,
            position_lng=cart_data.position.lng,
            velocity=cart_data.velocity,
            status=cart_data.status,
            battery_level=cart_data.battery_level
        )
        self.db.add(db_cart)
        self.db.commit()
        self.db.refresh(db_cart)
        return db_cart
    
    def get_cart_by_id(self, cart_id: UUID) -> Optional[GolfCart]:
        """Get a specific cart by ID"""
        return self.db.query(GolfCart).filter(GolfCart.id == cart_id).first()
    
    def get_cart_by_number(self, cart_number: str) -> Optional[GolfCart]:
        """Get a specific cart by cart number"""
        return self.db.query(GolfCart).filter(GolfCart.cart_number == cart_number).first()
    
    def get_all_carts(
        self, 
        skip: int = 0, 
        limit: int = 100,
        status: Optional[CartStatus] = None
    ) -> List[GolfCart]:
        """Get all carts with optional filtering"""
        query = self.db.query(GolfCart)
        
        if status:
            query = query.filter(GolfCart.status == status)
        
        return query.offset(skip).limit(limit).all()
    
    def get_carts_by_status(self, status: CartStatus) -> List[GolfCart]:
        """Get all carts with a specific status"""
        return self.db.query(GolfCart).filter(GolfCart.status == status).all()
    
    def get_running_carts(self) -> List[GolfCart]:
        """Get all currently running carts"""
        return self.get_carts_by_status(CartStatus.RUNNING)
    
    def get_carts_needing_maintenance(self) -> List[GolfCart]:
        """Get carts that are due for maintenance or fixing"""
        return self.db.query(GolfCart).filter(
            or_(
                GolfCart.status == CartStatus.FIXING,
                GolfCart.battery_level < 20.0
            )
        ).all()
    
    def update_cart(self, cart_id: UUID, cart_update: GolfCartUpdate) -> Optional[GolfCart]:
        """Update cart information"""
        db_cart = self.get_cart_by_id(cart_id)
        if not db_cart:
            return None
        
        update_data = cart_update.dict(exclude_unset=True)
        
        # Handle position update separately
        if "position" in update_data and update_data["position"]:
            db_cart.position_lat = update_data["position"]["lat"]
            db_cart.position_lng = update_data["position"]["lng"]
            del update_data["position"]
        
        # Update other fields
        for field, value in update_data.items():
            setattr(db_cart, field, value)
        
        self.db.commit()
        self.db.refresh(db_cart)
        return db_cart
    
    def update_cart_position(
        self, 
        cart_id: UUID, 
        lat: float, 
        lng: float, 
        velocity: Optional[float] = None
    ) -> Optional[GolfCart]:
        """Update cart position and optionally velocity"""
        db_cart = self.get_cart_by_id(cart_id)
        if not db_cart:
            return None
        
        db_cart.position_lat = lat
        db_cart.position_lng = lng
        
        if velocity is not None:
            db_cart.velocity = velocity
            # Auto-update status based on velocity
            if velocity > 0:
                db_cart.status = CartStatus.RUNNING
            else:
                db_cart.status = CartStatus.IDLE
        
        self.db.commit()
        self.db.refresh(db_cart)
        return db_cart
    
    def delete_cart(self, cart_id: UUID) -> bool:
        """Delete a golf cart"""
        db_cart = self.get_cart_by_id(cart_id)
        if not db_cart:
            return False
        
        self.db.delete(db_cart)
        self.db.commit()
        return True
    
    def get_cart_count(self, status: Optional[CartStatus] = None) -> int:
        """Get total count of carts"""
        query = self.db.query(GolfCart)
        if status:
            query = query.filter(GolfCart.status == status)
        return query.count()