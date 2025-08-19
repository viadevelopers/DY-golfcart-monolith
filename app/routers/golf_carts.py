"""
Golf Cart API routes using proper DDD architecture.

This is the improved version that properly separates concerns:
- Presentation layer (this file) only handles HTTP concerns
- Application service handles business orchestration
- No direct infrastructure dependencies
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from uuid import UUID

from app.schemas.golf_cart import (
    GolfCartCreate, 
    GolfCartUpdate, 
    GolfCartResponse, 
    GolfCartList,
    CartStatus
)
from app.middleware.auth import get_current_user
from app.domain.shared.exceptions import BusinessRuleViolation, EntityNotFound

# Import only the application service interface and factory
from app.application.fleet.dependencies import get_golf_cart_application_service
from app.application.fleet.services.golf_cart_application_service import (
    IGolfCartApplicationService
)

router = APIRouter(prefix="golf-carts", tags=["golf-carts"])


@router.post("/", response_model=GolfCartResponse, dependencies=[Depends(get_current_user)])
async def register_golf_cart(
    cart_data: GolfCartCreate,
    service: IGolfCartApplicationService = Depends(get_golf_cart_application_service)
):
    """
    Register a new golf cart.
    """
    try:
        cart_id = await service.register_cart(
            cart_number=cart_data.cart_number,
            initial_lat=cart_data.position.lat,
            initial_lng=cart_data.position.lng,
            initial_battery=cart_data.battery_level or 100.0,
            initial_status=cart_data.status.value
        )
        
        # Retrieve the created cart
        cart_dict = await service.get_cart_by_id(cart_id)
        
        if not cart_dict:
            raise HTTPException(status_code=500, detail="Failed to retrieve created cart")
        
        return GolfCartResponse(**cart_dict)
        
    except BusinessRuleViolation as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=GolfCartList)
async def get_all_carts(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[CartStatus] = None,
    service: IGolfCartApplicationService = Depends(get_golf_cart_application_service)
):
    """
    Get all golf carts with optional filtering.
    
    Clean separation: HTTP concerns here, business logic in the service.
    """
    result = await service.get_all_carts(
        skip=skip,
        limit=limit,
        status=status.value if status else None
    )
    
    # Transform to response model
    carts = [GolfCartResponse(**cart_dict) for cart_dict in result["carts"]]
    return GolfCartList(total=result["total"], carts=carts)


@router.get("/{cart_id}", response_model=GolfCartResponse)
async def get_cart_by_id(
    cart_id: UUID,
    service: IGolfCartApplicationService = Depends(get_golf_cart_application_service)
):
    """Get a specific golf cart by ID."""
    cart_dict = await service.get_cart_by_id(cart_id)
    
    if not cart_dict:
        raise HTTPException(status_code=404, detail="Golf cart not found")
    
    return GolfCartResponse(**cart_dict)


@router.get("/by-number/{cart_number}", response_model=GolfCartResponse)
async def get_cart_by_number(
    cart_number: str,
    service: IGolfCartApplicationService = Depends(get_golf_cart_application_service)
):
    """Get a specific golf cart by cart number."""
    try:
        cart_dict = await service.get_cart_by_number(cart_number)
        
        if not cart_dict:
            raise HTTPException(status_code=404, detail="Golf cart not found")
        
        return GolfCartResponse(**cart_dict)
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{cart_id}", response_model=GolfCartResponse, dependencies=[Depends(get_current_user)])
async def update_cart(
    cart_id: UUID,
    cart_update: GolfCartUpdate,
    service: IGolfCartApplicationService = Depends(get_golf_cart_application_service)
):
    """
    Update golf cart information.
    
    The application service handles all the complex orchestration logic.
    """
    try:
        # Update position if provided
        if cart_update.position and cart_update.velocity is not None:
            await service.update_cart_position(
                cart_id=cart_id,
                latitude=cart_update.position.lat,
                longitude=cart_update.position.lng,
                velocity=cart_update.velocity
            )
        
        # Update status if provided
        if cart_update.status:
            if cart_update.status == CartStatus.RUNNING:
                await service.start_trip(cart_id)
            elif cart_update.status == CartStatus.IDLE:
                await service.stop_trip(cart_id)
        
        # Retrieve updated cart
        cart_dict = await service.get_cart_by_id(cart_id)
        
        if not cart_dict:
            raise HTTPException(status_code=404, detail="Golf cart not found")
        
        return GolfCartResponse(**cart_dict)
        
    except EntityNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BusinessRuleViolation as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{cart_id}/position", response_model=GolfCartResponse, dependencies=[Depends(get_current_user)])
async def update_cart_position(
    cart_id: UUID,
    lat: float = Query(..., description="Latitude"),
    lng: float = Query(..., description="Longitude"),
    velocity: Optional[float] = Query(None, ge=0, description="Velocity in km/h"),
    service: IGolfCartApplicationService = Depends(get_golf_cart_application_service)
):
    """Update golf cart position."""
    try:
        await service.update_cart_position(
            cart_id=cart_id,
            latitude=lat,
            longitude=lng,
            velocity=velocity or 0.0
        )
        
        # Retrieve updated cart
        cart_dict = await service.get_cart_by_id(cart_id)
        
        if not cart_dict:
            raise HTTPException(status_code=404, detail="Golf cart not found")
        
        return GolfCartResponse(**cart_dict)
        
    except EntityNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BusinessRuleViolation as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{status}", response_model=List[GolfCartResponse])
async def get_carts_by_status(
    status: CartStatus,
    service: IGolfCartApplicationService = Depends(get_golf_cart_application_service)
):
    """Get all golf carts with a specific status."""
    cart_dicts = await service.get_carts_by_status(status.value)
    return [GolfCartResponse(**cart_dict) for cart_dict in cart_dicts]


@router.get("/special/running", response_model=List[GolfCartResponse])
async def get_running_carts(
    service: IGolfCartApplicationService = Depends(get_golf_cart_application_service)
):
    """Get all currently running golf carts."""
    cart_dicts = await service.get_running_carts()
    return [GolfCartResponse(**cart_dict) for cart_dict in cart_dicts]


@router.get("/special/needs-maintenance", response_model=List[GolfCartResponse])
async def get_carts_needing_maintenance(
    service: IGolfCartApplicationService = Depends(get_golf_cart_application_service)
):
    """Get golf carts that need maintenance."""
    cart_dicts = await service.get_carts_needing_maintenance()
    return [GolfCartResponse(**cart_dict) for cart_dict in cart_dicts]


@router.post("/{cart_id}/start-trip", response_model=GolfCartResponse, dependencies=[Depends(get_current_user)])
async def start_trip(
    cart_id: UUID,
    service: IGolfCartApplicationService = Depends(get_golf_cart_application_service)
):
    """Start a trip for a golf cart."""
    try:
        await service.start_trip(cart_id)
        
        # Retrieve updated cart
        cart_dict = await service.get_cart_by_id(cart_id)
        
        if not cart_dict:
            raise HTTPException(status_code=404, detail="Golf cart not found")
        
        return GolfCartResponse(**cart_dict)
        
    except EntityNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BusinessRuleViolation as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{cart_id}/stop-trip", response_model=GolfCartResponse, dependencies=[Depends(get_current_user)])
async def stop_trip(
    cart_id: UUID,
    service: IGolfCartApplicationService = Depends(get_golf_cart_application_service)
):
    """Stop a trip for a golf cart."""
    try:
        await service.stop_trip(cart_id)
        
        # Retrieve updated cart
        cart_dict = await service.get_cart_by_id(cart_id)
        
        if not cart_dict:
            raise HTTPException(status_code=404, detail="Golf cart not found")
        
        return GolfCartResponse(**cart_dict)
        
    except EntityNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BusinessRuleViolation as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{cart_id}", dependencies=[Depends(get_current_user)])
async def delete_cart(
    cart_id: UUID,
    service: IGolfCartApplicationService = Depends(get_golf_cart_application_service)
):
    """Delete a golf cart."""
    try:
        success = await service.delete_cart(cart_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Golf cart not found")
        
        return {"message": "Golf cart deleted successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
