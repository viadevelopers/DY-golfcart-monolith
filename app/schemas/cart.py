"""
Cart management schemas.
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID


class CartModelBase(BaseModel):
    """Base cart model schema."""
    manufacturer: str = Field(..., min_length=1, max_length=50)
    model_name: str = Field(..., min_length=1, max_length=50)
    model_code: str = Field(..., min_length=1, max_length=30)
    year: Optional[int] = None
    capacity: int = Field(default=2, ge=1, le=10)
    max_speed: float = Field(default=20.0, ge=0, le=50)
    range_km: Optional[float] = None
    charge_time_hours: Optional[float] = None
    features: Optional[Dict[str, Any]] = None


class CreateCartModel(CartModelBase):
    """Create cart model request."""
    pass


class CartModel(CartModelBase):
    """Cart model response."""
    id: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class GolfCartBase(BaseModel):
    """Base golf cart schema."""
    serial_number: str = Field(..., min_length=1, max_length=50)
    cart_model_id: UUID
    cart_number: Optional[str] = None
    firmware_version: Optional[str] = None


class RegisterCart(GolfCartBase):
    """Register cart request."""
    pass


class UpdateCart(BaseModel):
    """Update cart request."""
    cart_number: Optional[str] = None
    status: Optional[str] = None
    mode: Optional[str] = None
    firmware_version: Optional[str] = None
    speed_limit_override: Optional[float] = None


class AssignCart(BaseModel):
    """Assign cart to golf course request."""
    golf_course_id: UUID
    registration_type: str  # NEW, TRANSFER, RETURN, TEMPORARY
    cart_number: Optional[str] = None
    notes: Optional[str] = None


class GolfCart(GolfCartBase):
    """Golf cart response."""
    id: UUID
    golf_course_id: Optional[UUID] = None
    golf_course_name: Optional[str] = None
    status: str
    mode: str
    last_ping: Optional[datetime] = None
    is_online: bool = False
    total_distance_km: float = 0
    total_runtime_hours: float = 0
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class GolfCartDetail(GolfCart):
    """Detailed golf cart response."""
    cart_model: Optional[CartModel] = None
    last_maintenance_date: Optional[datetime] = None
    next_maintenance_date: Optional[datetime] = None
    current_assignment: Optional[Dict[str, Any]] = None
    recent_events: List[Dict[str, Any]] = []


class CartRegistration(BaseModel):
    """Cart registration response."""
    id: UUID
    cart_id: UUID
    golf_course_id: UUID
    registration_type: str
    cart_number: Optional[str] = None
    start_date: datetime
    end_date: Optional[datetime] = None
    notes: Optional[str] = None
    registered_at: datetime
    
    class Config:
        from_attributes = True


class CartTelemetryData(BaseModel):
    """Cart telemetry data."""
    cart_id: UUID
    timestamp: datetime
    position: Dict[str, float]  # {"lat": 0.0, "lng": 0.0}
    heading: Optional[float] = None
    speed: Optional[float] = None
    battery_level: Optional[int] = None
    
    class Config:
        from_attributes = True


class CartStatus(BaseModel):
    """Cart status update."""
    cart_id: UUID
    status: str
    mode: Optional[str] = None
    battery_level: Optional[int] = None
    position: Optional[Dict[str, float]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)