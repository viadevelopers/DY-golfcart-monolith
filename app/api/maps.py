"""
Map management API endpoints.
Independent map lifecycle as per Title 1 sequence diagram.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query, Body
from sqlalchemy.orm import Session
import json

from app.core.database import get_db
from app.core.security import AuthContext, require_manufacturer, get_current_user
from app.services.map_service import map_service
from app.services.s3_service import s3_service
from app.models.map import Map

router = APIRouter()


@router.post("/upload", status_code=status.HTTP_200_OK)
async def upload_map(
    file: UploadFile = File(..., description="Map file (GeoJSON, KML, or image)"),
    name: str = Form(..., description="Map name"),
    version: str = Form(..., description="Map version"),
    center_lat: Optional[float] = Form(None, description="Map center latitude"),
    center_lng: Optional[float] = Form(None, description="Map center longitude"),
    zoom_levels: Optional[List[int]] = Form(None, description="Initial zoom level"),
    current_user: AuthContext = Depends(require_manufacturer)
):
    """
    Upload map file (Title 1 sequence: MA → UI → API → MS → S3).
    
    Independent from golf course creation as per sequence diagram.
    Processes map, stores in S3, generates tiles, and saves to map_features.
    """
    try:
        # Read file data
        file_data = await file.read()
        
        # Process map upload (MS → S3 → maps table)
        result = map_service.process_map_upload(
            file_data=file_data,
            filename=file.filename if file.filename else uuid4().hex,
            name=name,
            version=version,
            center_lat=center_lat,
            center_lng=center_lng,
            zoom_levels=zoom_levels,
            uploaded_by_id=str(current_user.user_id) if current_user else None,
            golf_course_id=None  # Can be added later if needed
        )
        
        # Return response matching Title 1 sequence
        return {
            "map_id": result["map_id"],
            "storage_url": result["storage_url"],
            "tiles": result.get("tiles", []),
            "bounds": result.get("bounds", []),
            "status": "success",
            "message": "Map uploaded and processed successfully"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Map upload failed: {str(e)}"
        )


@router.post("/routes", status_code=status.HTTP_200_OK)
async def create_map_route(
    name: str = Form(..., description="Route name"),
    route_type: str = Form(..., description="Route type"),
    path: str = Form(..., description="Route path as JSON array [[lng, lat], ...]"),
    map_id: str = Form(..., description="Reference map ID"),
    distance_meters: Optional[float] = Form(None, description="Route distance in meters"),
    estimated_time_seconds: Optional[int] = Form(None, description="Estimated time in seconds"),
    current_user: AuthContext = Depends(require_manufacturer),
    db: Session = Depends(get_db)
):
    """
    Create route for map (Title 1 sequence: MA → UI → API → MS → DB).
    
    Stores route as PostGIS LINESTRING in routes table.
    Independent from golf course, references map_id.
    """
    try:
        # Parse path coordinates
        try:
            path_coords = json.loads(path)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid path format. Must be JSON array of [lng, lat] coordinates."
            )
        
        # Validate route type
        valid_types = ["FULL_COURSE", "HOLE_TO_HOLE", "RETURN_TO_BASE", "CHARGING_STATION", "CUSTOM"]
        if route_type not in valid_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid route_type. Must be one of: {', '.join(valid_types)}"
            )
        
        # Create route (MS → DB with LINESTRING)
        result = map_service.create_route(
            name=name,
            route_type=route_type,
            path=path_coords,
            map_id=map_id,
            distance_meters=distance_meters,
            estimated_time_seconds=estimated_time_seconds,
            db=db
        )
        
        # Save route to S3 for future serving
        s3_result = s3_service.save_route(
            route_id=result["route_id"],
            route_data={
                "name": name,
                "route_type": route_type,
                "path": path_coords,
                "distance_meters": result["distance_meters"],
                "estimated_time_seconds": result["estimated_time_seconds"]
            }
        )
        
        # Return response matching Title 1 sequence
        return {
            "route_id": result["route_id"],
            "name": result["name"],
            "route_type": result["route_type"],
            "distance_meters": result["distance_meters"],
            "estimated_time_seconds": result["estimated_time_seconds"],
            "storage_url": s3_result["url"],
            "s3_endpoint": s3_result["s3_endpoint"],
            "status": "created"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Route creation failed: {str(e)}"
        )


@router.get("/routes")
async def list_routes(
    map_id: Optional[str] = None,
    route_type: Optional[str] = None,
    current_user: AuthContext = Depends(get_current_user)
):
    """
    List stored routes with their path data and S3 endpoints.
    
    Returns routes as JSON with coordinate paths and storage endpoints.
    """
    try:
        # Get all routes from S3 service
        routes = s3_service.list_routes()
        
        # Filter by map_id if provided
        if map_id:
            # In production, would filter by map_id from database
            pass
        
        # Filter by route_type if provided  
        if route_type:
            routes = [r for r in routes if r.get("type") == route_type]
        
        return {
            "items": routes,
            "total": len(routes),
            "status": "success"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list routes: {str(e)}"
        )


@router.get("/routes/{route_id}")
async def get_route(
    route_id: str,
    current_user: AuthContext = Depends(get_current_user)
):
    """
    Get specific route with full path coordinates and S3 endpoint.
    
    Returns complete route data including coordinate array.
    """
    try:
        route_data = s3_service.get_route(route_id)
        
        if not route_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Route not found"
            )
        
        return route_data
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve route: {str(e)}"
        )


@router.get("/", status_code=status.HTTP_200_OK)
async def list_maps(
    status: Optional[str] = Query(None, description="Filter by status (active, archived, processing, failed)"),
    golf_course_id: Optional[str] = Query(None, description="Filter by golf course ID"),
    file_type: Optional[str] = Query(None, description="Filter by file type (geojson, kml, image)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, le=1000, description="Maximum number of records"),
    current_user: AuthContext = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all maps with filtering and pagination.
    
    Returns maps from database with optional filters.
    """
    try:
        filters = {
            'status': status,
            'golf_course_id': golf_course_id,
            'file_type': file_type
        }
        
        maps = map_service.list_maps(filters, db, skip, limit)
        
        # Convert to dict for response
        return {
            "items": [map_record.to_dict() for map_record in maps],
            "total": len(maps),
            "skip": skip,
            "limit": limit,
            "status": "success"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list maps: {str(e)}"
        )


@router.get("/{map_id}", status_code=status.HTTP_200_OK)
async def get_map(
    map_id: str,
    current_user: AuthContext = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get detailed map information by ID.
    
    Returns complete map data from database.
    """
    try:
        map_data = map_service.get_map_data(map_id, db)
        
        if not map_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Map not found"
            )
        
        return map_data
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve map: {str(e)}"
        )


@router.patch("/{map_id}/status", status_code=status.HTTP_200_OK)
async def update_map_status(
    map_id: str,
    status: str = Body(..., pattern="^(active|archived|processing|failed)$", description="New status"),
    current_user: AuthContext = Depends(require_manufacturer),
    db: Session = Depends(get_db)
):
    """
    Update map status (archive, activate, etc.).
    
    Only manufacturer users can update map status.
    """
    try:
        success = map_service.update_map_status(map_id, status, db)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Map not found or update failed"
            )
        
        return {
            "map_id": map_id,
            "status": status,
            "message": f"Map status updated to {status}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update map status: {str(e)}"
        )


@router.delete("/{map_id}", status_code=status.HTTP_200_OK)
async def archive_map(
    map_id: str,
    current_user: AuthContext = Depends(require_manufacturer),
    db: Session = Depends(get_db)
):
    """
    Archive a map (soft delete).
    
    Sets map status to 'archived'. Only manufacturer users can archive maps.
    """
    try:
        success = map_service.archive_map(map_id, db)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Map not found or archive failed"
            )
        
        return {
            "map_id": map_id,
            "status": "archived",
            "message": "Map successfully archived"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to archive map: {str(e)}"
        )
