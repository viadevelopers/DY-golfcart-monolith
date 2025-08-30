"""
Golf course schemas.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID


class GolfCourseBase(BaseModel):
    """Base golf course schema."""
    name: str = Field(..., min_length=1, max_length=100)
    code: str = Field(..., min_length=1, max_length=20)
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    hole_count: int = Field(default=18, ge=1, le=36)
    timezone: str = "UTC"
    opening_time: Optional[str] = None  # HH:MM
    closing_time: Optional[str] = None  # HH:MM
    cart_speed_limit: float = Field(default=20.0, ge=0, le=50)
    auto_return_enabled: bool = False
    geofence_alerts_enabled: bool = True


class CreateGolfCourse(GolfCourseBase):
    """Create golf course request."""
    pass


class UpdateGolfCourse(BaseModel):
    """Update golf course request."""
    name: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    status: Optional[str] = None
    opening_time: Optional[str] = None
    closing_time: Optional[str] = None
    cart_speed_limit: Optional[float] = None
    auto_return_enabled: Optional[bool] = None
    geofence_alerts_enabled: Optional[bool] = None


class GolfCourse(GolfCourseBase):
    """Golf course response."""
    id: UUID
    status: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class GolfCourseDetail(GolfCourse):
    """Detailed golf course response."""
    cart_count: int = 0
    active_carts: int = 0
    user_count: int = 0
    map_count: int = 0
    route_count: int = 0
    geofence_count: int = 0
    metadata_json: Optional[Dict[str, Any]] = None


class HoleBase(BaseModel):
    """Base hole schema."""
    hole_number: int = Field(..., ge=1, le=36)
    par: int = Field(..., ge=3, le=6)
    distance_red: Optional[int] = None
    distance_white: Optional[int] = None
    distance_blue: Optional[int] = None
    distance_black: Optional[int] = None


class CreateHole(HoleBase):
    """Create hole request."""
    tee_position: Optional[Dict[str, float]] = None  # {"lat": 0.0, "lng": 0.0}
    green_position: Optional[Dict[str, float]] = None
    pin_position: Optional[Dict[str, float]] = None


class Hole(HoleBase):
    """Hole response."""
    id: UUID
    golf_course_id: UUID
    created_at: datetime
    
    class Config:
        from_attributes = True


class RouteBase(BaseModel):
    """Base route schema."""
    name: str = Field(..., min_length=1, max_length=100)
    route_type: str  # HOLE_TO_HOLE, RETURN_TO_BASE, CHARGING, CUSTOM
    distance_meters: Optional[float] = None
    estimated_time_seconds: Optional[int] = None
    from_hole: Optional[int] = None
    to_hole: Optional[int] = None
    speed_limit: Optional[float] = None
    is_active: bool = True
    is_preferred: bool = False


class CreateRoute(RouteBase):
    """Create route request."""
    path: List[List[float]]  # [[lng, lat], [lng, lat], ...]
    waypoints: Optional[List[Dict[str, Any]]] = None


class Route(RouteBase):
    """Route response."""
    id: UUID
    golf_course_id: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class GeofenceBase(BaseModel):
    """Base geofence schema."""
    name: str = Field(..., min_length=1, max_length=100)
    fence_type: str  # RESTRICTED, SLOW_ZONE, NO_ENTRY, HAZARD, PARKING
    speed_limit: Optional[float] = None
    alert_on_entry: bool = False
    alert_on_exit: bool = False
    auto_stop: bool = False
    is_active: bool = True
    severity: str = "WARNING"  # INFO, WARNING, CRITICAL


class CreateGeofence(GeofenceBase):
    """Create geofence request."""
    geometry: List[List[List[List[float]]]]  # [[[[lng, lat], [lng, lat], ...]]]
    schedule: Optional[List[Dict[str, Any]]] = None


class Geofence(GeofenceBase):
    """Geofence response."""
    id: UUID
    golf_course_id: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class MapBase(BaseModel):
    """Base map schema."""
    name: str = Field(..., min_length=1, max_length=100)
    version: str = Field(..., min_length=1, max_length=20)
    min_zoom: int = 10
    max_zoom: int = 19
    default_zoom: int = 15
    is_active: bool = True


class CreateMap(MapBase):
    """Create map request (multipart form data will be handled separately)."""
    pass


class GolfCourseMap(MapBase):
    """Map response."""
    id: UUID
    golf_course_id: UUID
    tile_url: Optional[str] = None
    static_image_url: Optional[str] = None
    uploaded_at: datetime
    
    class Config:
        from_attributes = True