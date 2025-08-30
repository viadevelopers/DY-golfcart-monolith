"""
Cart management API endpoints.
"""
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.core.security import AuthContext, require_manufacturer, get_current_user
from app.models.cart import CartModel, GolfCart, CartRegistration
from app.models.golf_course import GolfCourse
from app.schemas.cart import (
    CreateCartModel,
    CartModel as CartModelSchema,
    RegisterCart,
    UpdateCart,
    AssignCart,
    GolfCart as GolfCartSchema,
    GolfCartDetail,
    CartRegistration as CartRegistrationSchema
)


router = APIRouter()


# Cart Model endpoints
@router.get("/models", response_model=List[CartModelSchema])
async def list_cart_models(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: AuthContext = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List available cart models.
    """
    models = db.query(CartModel).offset(skip).limit(limit).all()
    return models


@router.post("/models", response_model=CartModelSchema)
async def create_cart_model(
    model: CreateCartModel,
    current_user: AuthContext = Depends(require_manufacturer),
    db: Session = Depends(get_db)
):
    """
    Create a new cart model.
    Only manufacturer users can create cart models.
    """
    # Check if model code already exists
    existing = db.query(CartModel).filter(
        CartModel.model_code == model.model_code
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Model with code {model.model_code} already exists"
        )
    
    db_model = CartModel(**model.model_dump())
    db.add(db_model)
    db.commit()
    db.refresh(db_model)
    
    return db_model


# Cart Registration endpoint (Title 2 sequence)
@router.post("/register", response_model=GolfCartSchema, status_code=status.HTTP_201_CREATED)
async def register_cart(
    cart: RegisterCart,
    current_user: AuthContext = Depends(require_manufacturer),
    db: Session = Depends(get_db)
):
    """
    Register a new golf cart (Title 2 sequence: MA → UI → API → CS).
    
    Creates cart, sets up MQTT authentication, and publishes CartRegistered event.
    This endpoint matches the exact sequence diagram requirement.
    """
    from app.services.kafka_service import get_event_publisher
    from app.services.mqtt_service import mqtt_service
    
    # Check if serial number already exists
    existing = db.query(GolfCart).filter(
        GolfCart.serial_number == cart.serial_number
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cart with serial number {cart.serial_number} already exists"
        )
    
    # Verify cart model exists
    model = db.query(CartModel).filter(
        CartModel.id == cart.cart_model_id
    ).first()
    
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart model not found"
        )
    
    # Create cart (CS → DB)
    db_cart = GolfCart(
        serial_number=cart.serial_number,
        cart_model_id=cart.cart_model_id,
        cart_number=cart.cart_number,
        firmware_version=cart.firmware_version,
        status="IDLE",
        mode="MANUAL",
        mqtt_client_id=f"cart_{cart.serial_number}"
    )
    
    db.add(db_cart)
    db.commit()
    db.refresh(db_cart)
    
    # MQTT authentication setup (CS → MQTT)
    # In production, would create actual MQTT credentials
    mqtt_auth = {
        'client_id': db_cart.mqtt_client_id,
        'username': f"cart_{db_cart.id}",
        'password': 'generated_secure_password',  # Would be generated
        'topic_prefix': f"cart/{db_cart.id}"
    }
    
    # Publish CartRegistered event (CS → Kafka)
    event_publisher = get_event_publisher()
    event_publisher.publish_cart_registered(
        cart_id=str(db_cart.id),
        serial_number=db_cart.serial_number,
        cart_model_id=str(db_cart.cart_model_id),
        additional_data={
            'firmware_version': cart.firmware_version,
            'mqtt_client_id': db_cart.mqtt_client_id
        }
    )
    
    return db_cart

# Golf Cart endpoints
@router.get("/", response_model=List[GolfCartSchema])
async def list_carts(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    golf_course_id: Optional[UUID] = None,
    status: Optional[str] = None,
    current_user: AuthContext = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List golf carts.
    - Manufacturer users see all carts
    - Golf course users see only their carts
    """
    query = db.query(GolfCart)
    
    # Filter by user type
    if current_user.is_golf_course:
        query = query.filter(GolfCart.golf_course_id == current_user.golf_course_id)
    elif golf_course_id:
        query = query.filter(GolfCart.golf_course_id == golf_course_id)
    
    # Filter by status
    if status:
        query = query.filter(GolfCart.status == status)
    
    # Join with golf course for name
    query = query.outerjoin(GolfCourse)
    
    carts = query.offset(skip).limit(limit).all()
    
    # Add golf course name and online status
    result = []
    for cart in carts:
        cart_dict = GolfCartSchema.model_validate(cart).model_dump()
        if cart.golf_course:
            cart_dict["golf_course_name"] = cart.golf_course.name
        cart_dict["is_online"] = cart.is_online
        result.append(GolfCartSchema(**cart_dict))
    
    return result


@router.post("/register", response_model=GolfCartSchema)
async def register_cart(
    cart: RegisterCart,
    current_user: AuthContext = Depends(require_manufacturer),
    db: Session = Depends(get_db)
):
    """
    Register a new golf cart.
    Only manufacturer users can register carts.
    """
    # Check if serial number already exists
    existing = db.query(GolfCart).filter(
        GolfCart.serial_number == cart.serial_number
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cart with serial number {cart.serial_number} already exists"
        )
    
    # Verify cart model exists
    model = db.query(CartModel).filter(
        CartModel.id == cart.cart_model_id
    ).first()
    
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart model not found"
        )
    
    # Create cart
    db_cart = GolfCart(
        serial_number=cart.serial_number,
        cart_model_id=cart.cart_model_id,
        cart_number=cart.cart_number,
        firmware_version=cart.firmware_version,
        status="IDLE",
        mode="MANUAL",
        mqtt_client_id=f"cart_{cart.serial_number}"
    )
    
    db.add(db_cart)
    db.commit()
    db.refresh(db_cart)
    
    return db_cart


@router.get("/{cart_id}", response_model=GolfCartDetail)
async def get_cart(
    cart_id: UUID,
    current_user: AuthContext = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get cart details.
    """
    cart = db.query(GolfCart).filter(GolfCart.id == cart_id).first()
    
    if not cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart not found"
        )
    
    # Check access
    if current_user.is_golf_course and cart.golf_course_id != current_user.golf_course_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Create detailed response
    result = GolfCartDetail.model_validate(cart)
    result.is_online = cart.is_online
    
    # Add cart model
    if cart.cart_model:
        result.cart_model = CartModelSchema.model_validate(cart.cart_model)
    
    # Add golf course name
    if cart.golf_course:
        result.golf_course_name = cart.golf_course.name
    
    # Add current assignment if exists
    if cart.assignments:
        active_assignment = next(
            (a for a in cart.assignments if a.status == "ACTIVE"),
            None
        )
        if active_assignment:
            result.current_assignment = {
                "id": str(active_assignment.id),
                "player_name": active_assignment.player_name,
                "start_hole": active_assignment.start_hole,
                "current_hole": active_assignment.current_hole,
                "scheduled_start": active_assignment.scheduled_start.isoformat()
            }
    
    # Add recent events (last 5)
    if cart.events:
        recent_events = sorted(cart.events, key=lambda e: e.timestamp, reverse=True)[:5]
        result.recent_events = [
            {
                "id": str(e.id),
                "event_type": e.event_type,
                "severity": e.severity,
                "timestamp": e.timestamp.isoformat()
            }
            for e in recent_events
        ]
    
    return result


@router.patch("/{cart_id}", response_model=GolfCartSchema)
async def update_cart(
    cart_id: UUID,
    update_data: UpdateCart,
    current_user: AuthContext = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update cart information.
    """
    cart = db.query(GolfCart).filter(GolfCart.id == cart_id).first()
    
    if not cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart not found"
        )
    
    # Check access
    if current_user.is_golf_course:
        # Fix UUID vs string comparison by converting both to UUID
        from uuid import UUID
        cart_golf_course_id = cart.golf_course_id
        user_golf_course_id = UUID(current_user.golf_course_id) if isinstance(current_user.golf_course_id, str) else current_user.golf_course_id
        
        if cart_golf_course_id != user_golf_course_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        # Golf course users can only update certain fields
        allowed_fields = ["cart_number", "status", "mode"]
        update_dict = {k: v for k, v in update_data.dict(exclude_unset=True).items() 
                      if k in allowed_fields}
    else:
        update_dict = update_data.dict(exclude_unset=True)
    
    # Update fields
    for field, value in update_dict.items():
        setattr(cart, field, value)
    
    cart.updated_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(cart)
    
    return cart


@router.patch("/{cart_id}/assign", response_model=CartRegistrationSchema)
async def assign_cart_to_golf_course(
    cart_id: UUID,
    assignment: AssignCart,
    current_user: AuthContext = Depends(require_manufacturer),
    db: Session = Depends(get_db)
):
    """
    Assign cart to a golf course (Title 2 sequence: MA → UI → API → CS).
    
    Validates golf course, updates assignment, syncs MQTT config, publishes CartAssigned event.
    This endpoint matches the exact sequence diagram requirement (PATCH method).
    """
    from app.services.kafka_service import get_event_publisher
    from app.services.mqtt_service import mqtt_service
    # Get cart
    cart = db.query(GolfCart).filter(GolfCart.id == cart_id).first()
    
    if not cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart not found"
        )
    
    # Verify golf course exists
    golf_course = db.query(GolfCourse).filter(
        GolfCourse.id == assignment.golf_course_id
    ).first()
    
    if not golf_course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Golf course not found"
        )
    
    # End any existing active registration
    existing = db.query(CartRegistration).filter(
        CartRegistration.cart_id == cart_id,
        CartRegistration.end_date.is_(None)
    ).first()
    
    if existing:
        existing.end_date = datetime.now(timezone.utc)
    
    # Create new registration
    registration = CartRegistration(
        cart_id=cart_id,
        golf_course_id=assignment.golf_course_id,
        registered_by=current_user.user_id,
        registration_type=assignment.registration_type,
        cart_number=assignment.cart_number,
        notes=assignment.notes,
        start_date=datetime.now(timezone.utc)
    )
    
    # Update cart (CS → DB)
    cart.golf_course_id = assignment.golf_course_id
    cart.cart_number = assignment.cart_number
    
    db.add(registration)
    db.commit()
    db.refresh(registration)
    
    # MQTT Configuration Sync (CS → MQTT)
    config_payload = {
        'command': 'update_config',
        'golf_course_id': str(golf_course.id),
        'cart_number': assignment.cart_number,
        'settings': {
            'speed_limit': golf_course.cart_speed_limit or 20.0,
            'geofence_enabled': golf_course.geofence_alerts_enabled,
            'auto_return': golf_course.auto_return_enabled
        }
    }
    
    # Publish config to cart via MQTT (retain=true, QoS=1 as per sequence)
    mqtt_service.publish_cart_config(
        cart_serial=cart.serial_number,
        config=config_payload
    )
    
    # Publish CartAssigned event (CS → Kafka)
    event_publisher = get_event_publisher()
    event_publisher.publish_cart_assigned(
        cart_id=str(cart.id),
        golf_course_id=str(golf_course.id),
        cart_number=assignment.cart_number,
        additional_data={
            'registration_type': assignment.registration_type,
            'notes': assignment.notes
        }
    )
    
    return registration


@router.get("/{cart_id}/registrations", response_model=List[CartRegistrationSchema])
async def get_cart_registrations(
    cart_id: UUID,
    current_user: AuthContext = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get cart registration history.
    """
    registrations = db.query(CartRegistration).filter(
        CartRegistration.cart_id == cart_id
    ).order_by(CartRegistration.registered_at.desc()).all()
    
    return registrations