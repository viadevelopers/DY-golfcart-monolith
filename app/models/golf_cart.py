from sqlalchemy import Column, String, Float, DateTime, Enum as SQLEnum
from sqlalchemy.sql import func
from app.models.custom_types import UUID
import uuid
from app.database import Base
from app.domain.shared.cart_status import CartStatus

class GolfCart(Base):
    __tablename__ = "golf_carts"
    
    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    cart_number = Column(String, unique=True, nullable=False, index=True)
    position_lat = Column(Float, nullable=False, default=0.0)
    position_lng = Column(Float, nullable=False, default=0.0)
    velocity = Column(Float, nullable=False, default=0.0)  # km/h
    status = Column(SQLEnum(CartStatus), nullable=False, default=CartStatus.IDLE)
    battery_level = Column(Float, nullable=True, default=100.0)  # percentage
    last_maintenance = Column(DateTime, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "cart_number": self.cart_number,
            "position": {
                "lat": self.position_lat,
                "lng": self.position_lng
            },
            "velocity": self.velocity,
            "status": self.status.value if self.status else None,
            "battery_level": self.battery_level,
            "last_maintenance": self.last_maintenance.isoformat() if self.last_maintenance else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
