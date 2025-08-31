"""
Map Repository for clean data access layer.

Implements repository pattern for Map entity with spatial query support.
"""
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from geoalchemy2.elements import WKTElement
from geoalchemy2 import functions as geo_func

from app.models.map import Map


class MapRepository:
    """
    Repository for Map entity operations.
    
    Provides clean data access interface with:
    - CRUD operations
    - Spatial queries
    - Status management
    - Filtering and pagination
    """
    
    def __init__(self, db: Session):
        """Initialize repository with database session."""
        self.db = db
    
    def create(self, map_data: Dict[str, Any]) -> Map:
        """
        Create a new map record.
        
        Args:
            map_data: Dictionary containing map fields
            
        Returns:
            Created Map instance
        """
        map_record = Map(**map_data)
        self.db.add(map_record)
        self.db.commit()
        self.db.refresh(map_record)
        return map_record
    
    def get_by_id(self, map_id: UUID) -> Optional[Map]:
        """
        Retrieve map by ID.
        
        Args:
            map_id: Map UUID
            
        Returns:
            Map instance or None
        """
        return self.db.query(Map).filter(Map.id == map_id).first()
    
    def get_active(self) -> List[Map]:
        """
        Retrieve all active maps.
        
        Returns:
            List of active Map instances
        """
        return self.db.query(Map).filter(Map.status == 'active').all()
    
    def find_by_golf_course(self, golf_course_id: UUID) -> List[Map]:
        """
        Find maps associated with a golf course.
        
        Args:
            golf_course_id: Golf course UUID
            
        Returns:
            List of Map instances
        """
        return self.db.query(Map).filter(
            and_(
                Map.golf_course_id == golf_course_id,
                Map.status != 'archived'
            )
        ).all()
    
    def find_by_bounds(self, min_lng: float, min_lat: float, max_lng: float, max_lat: float) -> List[Map]:
        """
        Find maps that intersect with given bounds.
        
        Args:
            min_lng: Minimum longitude
            min_lat: Minimum latitude
            max_lng: Maximum longitude
            max_lat: Maximum latitude
            
        Returns:
            List of Map instances within bounds
        """
        # Create bounding box polygon
        bbox = WKTElement(
            f'POLYGON(({min_lng} {min_lat}, {max_lng} {min_lat}, '
            f'{max_lng} {max_lat}, {min_lng} {max_lat}, {min_lng} {min_lat}))',
            srid=4326
        )
        
        # Query maps that intersect with the bounding box
        return self.db.query(Map).filter(
            and_(
                Map.bounds.ST_Intersects(bbox),
                Map.status == 'active'
            )
        ).all()
    
    def find_nearest(self, lng: float, lat: float, limit: int = 5) -> List[Map]:
        """
        Find nearest maps to a point.
        
        Args:
            lng: Longitude
            lat: Latitude
            limit: Maximum number of results
            
        Returns:
            List of nearest Map instances
        """
        point = WKTElement(f'POINT({lng} {lat})', srid=4326)
        
        # Query maps ordered by distance from point
        return self.db.query(Map).filter(
            Map.status == 'active'
        ).order_by(
            Map.center_point.ST_Distance(point)
        ).limit(limit).all()
    
    def update(self, map_id: UUID, updates: Dict[str, Any]) -> Optional[Map]:
        """
        Update map fields.
        
        Args:
            map_id: Map UUID
            updates: Dictionary of fields to update
            
        Returns:
            Updated Map instance or None
        """
        map_record = self.get_by_id(map_id)
        if map_record:
            for key, value in updates.items():
                if hasattr(map_record, key):
                    setattr(map_record, key, value)
            map_record.updated_at = datetime.now(timezone.utc)
            self.db.commit()
            self.db.refresh(map_record)
        return map_record
    
    def update_status(self, map_id: UUID, status: str, errors: Optional[Dict[str, Any]] = None) -> bool:
        """
        Update map status with optional error details.
        
        Args:
            map_id: Map UUID
            status: New status (processing, active, failed, archived)
            errors: Optional error details for failed status
            
        Returns:
            True if successful, False otherwise
        """
        map_record = self.get_by_id(map_id)
        if map_record:
            map_record.status = status
            map_record.updated_at = datetime.now(timezone.utc)
            
            if status == 'failed' and errors:
                map_record.processing_errors = errors
                map_record.processing_completed_at = datetime.now(timezone.utc)
            elif status == 'active':
                map_record.processing_completed_at = datetime.now(timezone.utc)
                map_record.processing_errors = None
            
            self.db.commit()
            return True
        return False
    
    def archive(self, map_id: UUID) -> bool:
        """
        Archive a map (soft delete).
        
        Args:
            map_id: Map UUID
            
        Returns:
            True if successful, False otherwise
        """
        return self.update_status(map_id, 'archived')
    
    def delete(self, map_id: UUID) -> bool:
        """
        Permanently delete a map (hard delete).
        
        Args:
            map_id: Map UUID
            
        Returns:
            True if successful, False otherwise
        """
        map_record = self.get_by_id(map_id)
        if map_record:
            self.db.delete(map_record)
            self.db.commit()
            return True
        return False
    
    def search(
        self,
        filters: Dict[str, Any],
        skip: int = 0,
        limit: int = 100,
        order_by: str = 'created_at',
        order_desc: bool = True
    ) -> tuple[List[Map], int]:
        """
        Search maps with filters and pagination.
        
        Args:
            filters: Search criteria
            skip: Number of records to skip
            limit: Maximum number of records
            order_by: Field to order by
            order_desc: Whether to order descending
            
        Returns:
            Tuple of (maps list, total count)
        """
        query = self.db.query(Map)
        
        # Apply filters
        if filters.get('status'):
            query = query.filter(Map.status == filters['status'])
        if filters.get('golf_course_id'):
            query = query.filter(Map.golf_course_id == filters['golf_course_id'])
        if filters.get('file_type'):
            query = query.filter(Map.file_type == filters['file_type'])
        if filters.get('name_contains'):
            query = query.filter(Map.name.contains(filters['name_contains']))
        if filters.get('version'):
            query = query.filter(Map.version == filters['version'])
        if filters.get('uploaded_by'):
            query = query.filter(Map.uploaded_by == filters['uploaded_by'])
        
        # Date range filters
        if filters.get('created_after'):
            query = query.filter(Map.created_at >= filters['created_after'])
        if filters.get('created_before'):
            query = query.filter(Map.created_at <= filters['created_before'])
        
        # Get total count before pagination
        total = query.count()
        
        # Apply ordering
        if hasattr(Map, order_by):
            order_column = getattr(Map, order_by)
            if order_desc:
                query = query.order_by(order_column.desc())
            else:
                query = query.order_by(order_column)
        
        # Apply pagination
        maps = query.offset(skip).limit(limit).all()
        
        return maps, total
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get map statistics.
        
        Returns:
            Dictionary with statistics
        """
        total = self.db.query(func.count(Map.id)).scalar()
        active = self.db.query(func.count(Map.id)).filter(Map.status == 'active').scalar()
        archived = self.db.query(func.count(Map.id)).filter(Map.status == 'archived').scalar()
        failed = self.db.query(func.count(Map.id)).filter(Map.status == 'failed').scalar()
        processing = self.db.query(func.count(Map.id)).filter(Map.status == 'processing').scalar()
        
        # Get file type distribution
        file_types = self.db.query(
            Map.file_type,
            func.count(Map.id)
        ).group_by(Map.file_type).all()
        
        return {
            'total': total,
            'by_status': {
                'active': active,
                'archived': archived,
                'failed': failed,
                'processing': processing
            },
            'by_file_type': {ft: count for ft, count in file_types if ft},
            'with_golf_course': self.db.query(func.count(Map.id)).filter(Map.golf_course_id.isnot(None)).scalar(),
            'independent': self.db.query(func.count(Map.id)).filter(Map.golf_course_id.is_(None)).scalar()
        }
    
    def bulk_update_status(self, map_ids: List[UUID], status: str) -> int:
        """
        Update status for multiple maps.
        
        Args:
            map_ids: List of map UUIDs
            status: New status
            
        Returns:
            Number of updated records
        """
        updated = self.db.query(Map).filter(
            Map.id.in_(map_ids)
        ).update(
            {
                Map.status: status,
                Map.updated_at: datetime.now(timezone.utc)
            },
            synchronize_session=False
        )
        self.db.commit()
        return updated