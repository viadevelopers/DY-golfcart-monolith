"""
Pydantic schemas for Map data validation and serialization.

Supports independent map lifecycle as per Title 1 sequence diagram.
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime


class MapBase(BaseModel):
    """Base schema for map data."""
    name: str = Field(..., min_length=1, max_length=255, description="Map name")
    version: str = Field(..., min_length=1, max_length=50, description="Map version")


class MapUploadRequest(MapBase):
    """Request schema for map upload."""
    center_lat: Optional[float] = Field(None, ge=-90, le=90, description="Map center latitude")
    center_lng: Optional[float] = Field(None, ge=-180, le=180, description="Map center longitude")
    zoom_levels: Optional[List[int]] = Field(None, description="Supported zoom levels")
    golf_course_id: Optional[UUID] = Field(None, description="Optional golf course association")


class MapResponse(MapBase):
    """Basic map response schema."""
    id: UUID = Field(..., description="Map unique identifier")
    storage_url: str = Field(..., description="S3 storage URL")
    status: str = Field(..., description="Map status (processing, active, failed, archived)")
    file_type: Optional[str] = Field(None, description="File type (geojson, kml, image)")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    model_config = ConfigDict(from_attributes=True)


class MapDetailResponse(MapResponse):
    """Detailed map response with all fields."""
    file_size: Optional[int] = Field(None, description="File size in bytes")
    original_filename: Optional[str] = Field(None, description="Original uploaded filename")
    bounds: Optional[List[List[float]]] = Field(None, description="Map bounds [[min_lng, min_lat], [max_lng, max_lat]]")
    center_point: Optional[List[float]] = Field(None, description="Map center [lng, lat]")
    zoom_levels: Optional[List[int]] = Field(None, description="Supported zoom levels")
    min_zoom: int = Field(10, description="Minimum zoom level")
    max_zoom: int = Field(19, description="Maximum zoom level")
    default_zoom: int = Field(15, description="Default zoom level")
    tiles: Optional[Dict[str, Any]] = Field(None, description="Tile URLs by zoom level")
    features: Optional[Dict[str, Any]] = Field(None, description="Extracted geographic features")
    metadata_json: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    processing_errors: Optional[Dict[str, Any]] = Field(None, description="Processing error details")
    processing_completed_at: Optional[datetime] = Field(None, description="Processing completion timestamp")
    golf_course_id: Optional[UUID] = Field(None, description="Associated golf course ID")
    uploaded_by: Optional[UUID] = Field(None, description="Uploader user ID")


class MapListResponse(BaseModel):
    """Response schema for map listing."""
    items: List[MapResponse] = Field(..., description="List of maps")
    total: int = Field(..., description="Total number of items")
    skip: int = Field(0, description="Number of items skipped")
    limit: int = Field(100, description="Maximum items returned")
    status: str = Field("success", description="Response status")


class MapUploadResponse(BaseModel):
    """Response schema for successful map upload."""
    map_id: str = Field(..., description="Newly created map ID")
    storage_url: str = Field(..., description="S3 storage URL")
    tiles: Optional[List[str]] = Field(None, description="Generated tile URLs")
    bounds: Optional[List[List[float]]] = Field(None, description="Calculated map bounds")
    features_count: Optional[int] = Field(None, description="Number of extracted features")
    status: str = Field(..., description="Upload status")
    message: str = Field(..., description="Status message")


class MapStatusUpdateRequest(BaseModel):
    """Request schema for map status update."""
    status: str = Field(..., pattern="^(active|archived|processing|failed)$", description="New status")


class MapStatusUpdateResponse(BaseModel):
    """Response schema for map status update."""
    map_id: str = Field(..., description="Map ID")
    status: str = Field(..., description="New status")
    message: str = Field(..., description="Status message")


class MapArchiveResponse(BaseModel):
    """Response schema for map archival."""
    map_id: str = Field(..., description="Archived map ID")
    status: str = Field("archived", description="Archive status")
    message: str = Field(..., description="Archive message")


class RouteCreateRequest(BaseModel):
    """Request schema for route creation."""
    name: str = Field(..., min_length=1, max_length=100, description="Route name")
    route_type: str = Field(..., pattern="^(FULL_COURSE|HOLE_TO_HOLE|RETURN_TO_BASE|CHARGING_STATION|CUSTOM)$", description="Route type")
    path: List[List[float]] = Field(..., min_length=2, description="Route path as [[lng, lat], ...]")
    map_id: str = Field(..., description="Reference map ID")
    distance_meters: Optional[float] = Field(None, ge=0, description="Route distance in meters")
    estimated_time_seconds: Optional[int] = Field(None, ge=0, description="Estimated time in seconds")


class RouteResponse(BaseModel):
    """Response schema for route data."""
    route_id: str = Field(..., description="Route ID")
    name: str = Field(..., description="Route name")
    route_type: str = Field(..., description="Route type")
    distance_meters: float = Field(..., description="Route distance in meters")
    estimated_time_seconds: int = Field(..., description="Estimated travel time in seconds")
    coordinates_count: int = Field(..., description="Number of coordinates in path")
    storage_url: Optional[str] = Field(None, description="S3 storage URL")
    s3_endpoint: Optional[str] = Field(None, description="S3 endpoint")
    status: str = Field(..., description="Route status")


class RouteListResponse(BaseModel):
    """Response schema for route listing."""
    items: List[Dict[str, Any]] = Field(..., description="List of routes")
    total: int = Field(..., description="Total number of routes")
    status: str = Field("success", description="Response status")