"""
Independent Map model for DY-GOLFCART Management System.

Maps have independent lifecycle from golf courses as per Title 1 sequence diagram.
Supports geospatial features with PostGIS integration.
"""
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from uuid import uuid4
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, Float, JSON, Text
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from geoalchemy2 import Geometry

from app.core.database import Base


class Map(Base):
    """
    Independent map entity with S3 storage and PostGIS support.
    
    Maps follow independent lifecycle:
    - Can exist without golf course association
    - Store geospatial bounds and features
    - Support tile generation and versioning
    """
    
    __tablename__ = "maps"
    
    # Primary identifiers
    id: Mapped[uuid4] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # Storage information
    storage_url: Mapped[str] = mapped_column(String(500), nullable=False)  # S3 URL for original file
    file_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # geojson, kml, png, jpg, tiff
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Size in bytes
    original_filename: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Geospatial data (PostGIS)
    bounds: Mapped[Optional[Any]] = mapped_column(Geometry("POLYGON", srid=4326), nullable=True)  # Map boundary
    center_point: Mapped[Optional[Any]] = mapped_column(Geometry("POINT", srid=4326), nullable=True)  # Map center
    
    # Map configuration
    zoom_levels: Mapped[Optional[List[int]]] = mapped_column(ARRAY(Integer), nullable=True)  # Supported zoom levels
    min_zoom: Mapped[int] = mapped_column(Integer, default=10)
    max_zoom: Mapped[int] = mapped_column(Integer, default=19)
    default_zoom: Mapped[int] = mapped_column(Integer, default=15)
    
    # Processed data
    tiles: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)  # Array of tile URLs
    features: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)  # Extracted geographic features
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)  # Additional flexible metadata
    
    # Status and processing
    status: Mapped[str] = mapped_column(String(50), default="processing", index=True)  # processing, active, failed, archived
    processing_errors: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)  # Error details if processing failed
    processing_completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Optional golf course association
    golf_course_id: Mapped[Optional[uuid4]] = mapped_column(UUID(as_uuid=True), ForeignKey("golf_courses.id"), nullable=True, index=True)
    
    # Audit fields
    uploaded_by: Mapped[Optional[uuid4]] = mapped_column(UUID(as_uuid=True), ForeignKey("manufacturer_users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    golf_course: Mapped[Optional["GolfCourse"]] = relationship("GolfCourse", backref="independent_maps")
    uploaded_by_user: Mapped[Optional["ManufacturerUser"]] = relationship("ManufacturerUser", backref="uploaded_independent_maps")
    routes: Mapped[List["Route"]] = relationship("Route", backref="map", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Map {self.name} v{self.version} ({self.status})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert map to dictionary for API responses."""
        return {
            'id': str(self.id),
            'name': self.name,
            'version': self.version,
            'storage_url': self.storage_url,
            'file_type': self.file_type,
            'file_size': self.file_size,
            'status': self.status,
            'zoom_levels': self.zoom_levels,
            'tiles': self.tiles,
            'features': self.features,
            'metadata': self.metadata_json,
            'golf_course_id': str(self.golf_course_id) if self.golf_course_id else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def get_bounds_array(self) -> Optional[List[List[float]]]:
        """Get bounds as coordinate array [[min_lng, min_lat], [max_lng, max_lat]]."""
        if not self.bounds:
            return None
        # Convert PostGIS geometry to coordinate array
        # This would use ST_AsGeoJSON or similar in actual query
        # Placeholder implementation - actual would extract from geometry
        return []
    
    def get_center_coords(self) -> Optional[List[float]]:
        """Get center point as [lng, lat] array."""
        if not self.center_point:
            return None
        # Convert PostGIS point to coordinates
        # This would use ST_X and ST_Y functions in actual query
        # Placeholder implementation - actual would extract from geometry
        return []
    
    @classmethod
    def create_from_upload(
        cls,
        name: str,
        version: str,
        storage_url: str,
        file_type: Optional[str] = None,
        file_size: Optional[int] = None,
        original_filename: Optional[str] = None,
        **kwargs
    ) -> "Map":
        """Factory method to create a Map from upload data."""
        return cls(
            name=name,
            version=version,
            storage_url=storage_url,
            file_type=file_type,
            file_size=file_size,
            original_filename=original_filename,
            status="processing",
            **kwargs
        )
    
    def mark_as_active(self) -> None:
        """Mark map as successfully processed and active."""
        self.status = "active"
        self.processing_completed_at = datetime.now(timezone.utc)
        self.processing_errors = None
    
    def mark_as_failed(self, error_details: Dict[str, Any]) -> None:
        """Mark map as failed with error details."""
        self.status = "failed"
        self.processing_errors = error_details
        self.processing_completed_at = datetime.now(timezone.utc)
    
    def archive(self) -> None:
        """Archive the map (soft delete)."""
        self.status = "archived"
        self.updated_at = datetime.now(timezone.utc)