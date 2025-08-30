"""
Golf course management API endpoints.
"""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import func
from geoalchemy2.shape import from_shape
from shapely.geometry import Point, LineString, Polygon

from app.core.database import get_db
from app.core.security import AuthContext, require_manufacturer, get_current_user
from app.models.golf_course import GolfCourse, GolfCourseMap, Hole, Route, Geofence
from app.models.cart import GolfCart
from app.schemas.golf_course import (
    CreateGolfCourse,
    UpdateGolfCourse,
    GolfCourse as GolfCourseSchema,
    GolfCourseDetail,
    CreateHole,
    Hole as HoleSchema,
    CreateRoute,
    Route as RouteSchema,
    CreateGeofence,
    Geofence as GeofenceSchema,
    GolfCourseMap as MapSchema
)


router = APIRouter()


@router.get("/", response_model=List[GolfCourseSchema])
async def list_golf_courses(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    current_user: AuthContext = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List golf courses.
    - Manufacturer users see all golf courses
    - Golf course users see only their golf course
    """
    query = db.query(GolfCourse)
    
    # Filter by user type
    if current_user.is_golf_course:
        query = query.filter(GolfCourse.id == current_user.golf_course_id)
    
    # Filter by status
    if status:
        query = query.filter(GolfCourse.status == status)
    
    # Apply pagination
    golf_courses = query.offset(skip).limit(limit).all()
    
    return golf_courses


@router.post("/", response_model=GolfCourseSchema)
async def create_golf_course(
    golf_course: CreateGolfCourse,
    current_user: AuthContext = Depends(require_manufacturer),
    db: Session = Depends(get_db)
):
    """
    Create a new golf course.
    Only manufacturer users can create golf courses.
    """
    # Check if code already exists
    existing = db.query(GolfCourse).filter(
        GolfCourse.code == golf_course.code
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Golf course with code {golf_course.code} already exists"
        )
    
    # Create golf course
    db_golf_course = GolfCourse(
        **golf_course.dict(),
        created_by=current_user.user_id,
        status="ACTIVE"
    )
    
    db.add(db_golf_course)
    db.commit()
    db.refresh(db_golf_course)
    
    return db_golf_course


@router.get("/{golf_course_id}", response_model=GolfCourseDetail)
async def get_golf_course(
    golf_course_id: UUID,
    current_user: AuthContext = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get golf course details.
    """
    # Get golf course
    golf_course = db.query(GolfCourse).filter(
        GolfCourse.id == golf_course_id
    ).first()
    
    if not golf_course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Golf course not found"
        )
    
    # Check access
    if current_user.is_golf_course and current_user.golf_course_id != str(golf_course_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Get counts
    cart_count = db.query(func.count(GolfCart.id)).filter(
        GolfCart.golf_course_id == golf_course_id
    ).scalar()
    
    active_carts = db.query(func.count(GolfCart.id)).filter(
        GolfCart.golf_course_id == golf_course_id,
        GolfCart.status == "RUNNING"
    ).scalar()
    
    # Convert to detailed schema
    result = GolfCourseDetail.from_orm(golf_course)
    result.cart_count = cart_count or 0
    result.active_carts = active_carts or 0
    result.user_count = len(golf_course.users)
    result.map_count = len(golf_course.maps)
    result.route_count = len(golf_course.routes)
    result.geofence_count = len(golf_course.geofences)
    
    return result


@router.patch("/{golf_course_id}", response_model=GolfCourseSchema)
async def update_golf_course(
    golf_course_id: UUID,
    update_data: UpdateGolfCourse,
    current_user: AuthContext = Depends(require_manufacturer),
    db: Session = Depends(get_db)
):
    """
    Update golf course information.
    Only manufacturer users can update golf courses.
    """
    golf_course = db.query(GolfCourse).filter(
        GolfCourse.id == golf_course_id
    ).first()
    
    if not golf_course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Golf course not found"
        )
    
    # Update fields
    update_dict = update_data.dict(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(golf_course, field, value)
    
    db.commit()
    db.refresh(golf_course)
    
    return golf_course


# Hole management endpoints
@router.get("/{golf_course_id}/holes", response_model=List[HoleSchema])
async def list_holes(
    golf_course_id: UUID,
    current_user: AuthContext = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all holes for a golf course.
    """
    holes = db.query(Hole).filter(
        Hole.golf_course_id == golf_course_id
    ).order_by(Hole.hole_number).all()
    
    return holes


@router.post("/{golf_course_id}/holes", response_model=HoleSchema)
async def create_hole(
    golf_course_id: UUID,
    hole: CreateHole,
    current_user: AuthContext = Depends(require_manufacturer),
    db: Session = Depends(get_db)
):
    """
    Create a hole for a golf course.
    Only manufacturer users can create holes.
    """
    # Get golf course to validate hole count
    golf_course = db.query(GolfCourse).filter(GolfCourse.id == golf_course_id).first()
    if not golf_course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Golf course not found"
        )
    
    # Validate hole number is within valid range
    if hole.hole_number < 1 or hole.hole_number > golf_course.hole_count:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Hole number must be between 1 and {golf_course.hole_count}"
        )
    
    # Check if hole number already exists
    existing = db.query(Hole).filter(
        Hole.golf_course_id == golf_course_id,
        Hole.hole_number == hole.hole_number
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Hole {hole.hole_number} already exists"
        )
    
    # Create hole
    db_hole = Hole(
        golf_course_id=golf_course_id,
        hole_number=hole.hole_number,
        par=hole.par,
        distance_red=hole.distance_red,
        distance_white=hole.distance_white,
        distance_blue=hole.distance_blue,
        distance_black=hole.distance_black
    )
    
    # Set positions if provided
    if hole.tee_position:
        db_hole.tee_position = from_shape(
            Point(hole.tee_position["lng"], hole.tee_position["lat"]),
            srid=4326
        )
    
    if hole.green_position:
        db_hole.green_position = from_shape(
            Point(hole.green_position["lng"], hole.green_position["lat"]),
            srid=4326
        )
    
    if hole.pin_position:
        db_hole.pin_position = from_shape(
            Point(hole.pin_position["lng"], hole.pin_position["lat"]),
            srid=4326
        )
    
    db.add(db_hole)
    db.commit()
    db.refresh(db_hole)
    
    return db_hole


# Route management endpoints
@router.get("/{golf_course_id}/routes", response_model=List[RouteSchema])
async def list_routes(
    golf_course_id: UUID,
    route_type: Optional[str] = None,
    is_active: Optional[bool] = None,
    current_user: AuthContext = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List routes for a golf course.
    """
    query = db.query(Route).filter(Route.golf_course_id == golf_course_id)
    
    if route_type:
        query = query.filter(Route.route_type == route_type)
    
    if is_active is not None:
        query = query.filter(Route.is_active == is_active)
    
    routes = query.all()
    return routes


@router.post("/{golf_course_id}/routes", response_model=RouteSchema)
async def create_route(
    golf_course_id: UUID,
    route: CreateRoute,
    current_user: AuthContext = Depends(require_manufacturer),
    db: Session = Depends(get_db)
):
    """
    Create a route for a golf course.
    Only manufacturer users can create routes.
    """
    # Validate route path coordinates
    if route.path:
        for coord in route.path:
            if len(coord) != 2:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Each coordinate must have exactly 2 values [lng, lat]"
                )
            lng, lat = coord
            if not (-180 <= lng <= 180):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Longitude {lng} must be between -180 and 180"
                )
            if not (-90 <= lat <= 90):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Latitude {lat} must be between -90 and 90"
                )
    
    # Create route
    db_route = Route(
        golf_course_id=golf_course_id,
        name=route.name,
        route_type=route.route_type,
        distance_meters=route.distance_meters,
        estimated_time_seconds=route.estimated_time_seconds,
        from_hole=route.from_hole,
        to_hole=route.to_hole,
        speed_limit=route.speed_limit,
        is_active=route.is_active,
        is_preferred=route.is_preferred,
        waypoints=route.waypoints,
        created_by=current_user.user_id
    )
    
    # Set path geometry
    if route.path:
        db_route.path = from_shape(
            LineString(route.path),
            srid=4326
        )
    
    db.add(db_route)
    db.commit()
    db.refresh(db_route)
    
    return db_route


# Geofence management endpoints
@router.get("/{golf_course_id}/geofences", response_model=List[GeofenceSchema])
async def list_geofences(
    golf_course_id: UUID,
    fence_type: Optional[str] = None,
    is_active: Optional[bool] = None,
    current_user: AuthContext = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List geofences for a golf course.
    """
    query = db.query(Geofence).filter(Geofence.golf_course_id == golf_course_id)
    
    if fence_type:
        query = query.filter(Geofence.fence_type == fence_type)
    
    if is_active is not None:
        query = query.filter(Geofence.is_active == is_active)
    
    geofences = query.all()
    return geofences


@router.post("/{golf_course_id}/geofences", response_model=GeofenceSchema)
async def create_geofence(
    golf_course_id: UUID,
    geofence: CreateGeofence,
    current_user: AuthContext = Depends(require_manufacturer),
    db: Session = Depends(get_db)
):
    """
    Create a geofence for a golf course.
    Only manufacturer users can create geofences.
    """
    # Validate speed limit
    if geofence.speed_limit is not None and geofence.speed_limit > 50.0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Speed limit {geofence.speed_limit} km/h exceeds maximum allowed limit of 50.0 km/h"
        )
    
    # Create geofence
    db_geofence = Geofence(
        golf_course_id=golf_course_id,
        name=geofence.name,
        fence_type=geofence.fence_type,
        speed_limit=geofence.speed_limit,
        alert_on_entry=geofence.alert_on_entry,
        alert_on_exit=geofence.alert_on_exit,
        auto_stop=geofence.auto_stop,
        is_active=geofence.is_active,
        severity=geofence.severity,
        schedule=geofence.schedule
    )
    
    # Set geometry with validation
    if geofence.geometry:
        try:
            # Extract the coordinate ring from nested structure
            coordinates = geofence.geometry[0][0]  # [[[lng, lat], [lng, lat], ...]]
            
            # Validate coordinates
            if len(coordinates) < 3:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Polygon must have at least 3 coordinates"
                )
            
            # Validate coordinate values
            for coord in coordinates:
                if len(coord) != 2:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail="Each coordinate must have exactly 2 values [lng, lat]"
                    )
                lng, lat = coord
                if not (-180 <= lng <= 180):
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=f"Longitude {lng} must be between -180 and 180"
                    )
                if not (-90 <= lat <= 90):
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=f"Latitude {lat} must be between -90 and 90"
                    )
            
            # Ensure the polygon is closed
            if coordinates[0] != coordinates[-1]:
                coordinates = coordinates + [coordinates[0]]
            
            # Create and validate the polygon
            from shapely.geometry import Polygon
            polygon = Polygon(coordinates)
            
            if not polygon.is_valid:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Invalid polygon geometry: {polygon.is_valid_reason if hasattr(polygon, 'is_valid_reason') else 'Invalid geometry'}"
                )
            
            # Check if polygon has meaningful area
            if polygon.area < 1e-12:  # Very small threshold for coordinate precision
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Polygon area is too small, coordinates may be invalid"
                )
            
            # Set the geometry using GeoAlchemy2
            db_geofence.geometry = from_shape(polygon, srid=4326)
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Failed to process geometry: {str(e)}"
            )
    
    db.add(db_geofence)
    db.commit()
    db.refresh(db_geofence)
    
    return db_geofence


# Map upload endpoint (simplified for MVP - using local storage)
@router.post("/{golf_course_id}/maps", response_model=MapSchema)
async def upload_map(
    golf_course_id: UUID,
    name: str = Form(...),
    version: str = Form(...),
    file: UploadFile = File(...),
    current_user: AuthContext = Depends(require_manufacturer),
    db: Session = Depends(get_db)
):
    """
    Upload a map for a golf course.
    Only manufacturer users can upload maps.
    Note: MVP version uses local file storage.
    """
    import os
    from app.core.config import settings
    
    # Create upload directory if it doesn't exist
    upload_dir = os.path.join(settings.UPLOAD_DIR, "maps", str(golf_course_id))
    os.makedirs(upload_dir, exist_ok=True)
    
    # Save file
    file_path = os.path.join(upload_dir, file.filename)
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    # Create map record
    db_map = GolfCourseMap(
        golf_course_id=golf_course_id,
        name=name,
        version=version,
        static_image_url=f"/uploads/maps/{golf_course_id}/{file.filename}",
        is_active=True,
        uploaded_by=current_user.user_id
    )
    
    db.add(db_map)
    db.commit()
    db.refresh(db_map)
    
    return db_map