from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum
from uuid import UUID

class CartStatus(str, Enum):
    RUNNING = "running"
    IDLE = "idle"
    CHARGING = "charging"
    FIXING = "fixing"
    OUT_OF_SERVICE = "out_of_service"

class Position(BaseModel):
    lat: float = Field(..., description="Latitude coordinate")
    lng: float = Field(..., description="Longitude coordinate")

class GolfCartBase(BaseModel):
    cart_number: str = Field(..., description="Unique cart number/identifier")
    position: Position = Field(default=Position(lat=0.0, lng=0.0))
    velocity: float = Field(default=0.0, ge=0, description="Velocity in km/h")
    status: CartStatus = Field(default=CartStatus.IDLE)
    battery_level: Optional[float] = Field(default=100.0, ge=0, le=100, description="Battery level percentage")

class GolfCartCreate(GolfCartBase):
    pass

class GolfCartUpdate(BaseModel):
    cart_number: Optional[str] = None
    position: Optional[Position] = None
    velocity: Optional[float] = Field(None, ge=0)
    status: Optional[CartStatus] = None
    battery_level: Optional[float] = Field(None, ge=0, le=100)
    last_maintenance: Optional[datetime] = None

class GolfCartResponse(GolfCartBase):
    id: UUID
    last_maintenance: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class GolfCartList(BaseModel):
    total: int
    carts: list[GolfCartResponse]