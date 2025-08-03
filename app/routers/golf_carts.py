from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from app.database import get_db
from app.schemas.golf_cart import (
    GolfCartCreate, 
    GolfCartUpdate, 
    GolfCartResponse, 
    GolfCartList,
    CartStatus
)
from app.services.golf_cart import GolfCartService
from app.middleware.auth import get_current_user

router = APIRouter(prefix="/api/golf-carts", tags=["golf-carts"])

@router.post("/", response_model=GolfCartResponse, dependencies=[Depends(get_current_user)])
async def register_golf_cart(
    cart_data: GolfCartCreate,
    db: Session = Depends(get_db)
):
    """Register a new golf cart"""
    service = GolfCartService(db)
    
    # Check if cart number already exists
    existing_cart = service.get_cart_by_number(cart_data.cart_number)
    if existing_cart:
        raise HTTPException(
            status_code=400, 
            detail=f"Cart with number {cart_data.cart_number} already exists"
        )
    
    cart = service.create_cart(cart_data)
    return cart

@router.get("/", response_model=GolfCartList)
async def get_all_carts(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[CartStatus] = None,
    db: Session = Depends(get_db)
):
    """Get all golf carts with optional filtering"""
    service = GolfCartService(db)
    carts = service.get_all_carts(skip=skip, limit=limit, status=status)
    total = service.get_cart_count(status=status)
    
    return GolfCartList(total=total, carts=carts)

@router.get("/{cart_id}", response_model=GolfCartResponse)
async def get_cart_by_id(
    cart_id: UUID,
    db: Session = Depends(get_db)
):
    """Get a specific golf cart by ID"""
    service = GolfCartService(db)
    cart = service.get_cart_by_id(cart_id)
    
    if not cart:
        raise HTTPException(status_code=404, detail="Golf cart not found")
    
    return cart

@router.get("/by-number/{cart_number}", response_model=GolfCartResponse)
async def get_cart_by_number(
    cart_number: str,
    db: Session = Depends(get_db)
):
    """Get a specific golf cart by cart number"""
    service = GolfCartService(db)
    cart = service.get_cart_by_number(cart_number)
    
    if not cart:
        raise HTTPException(status_code=404, detail="Golf cart not found")
    
    return cart

@router.put("/{cart_id}", response_model=GolfCartResponse, dependencies=[Depends(get_current_user)])
async def update_cart(
    cart_id: UUID,
    cart_update: GolfCartUpdate,
    db: Session = Depends(get_db)
):
    """Update golf cart information"""
    service = GolfCartService(db)
    cart = service.update_cart(cart_id, cart_update)
    
    if not cart:
        raise HTTPException(status_code=404, detail="Golf cart not found")
    
    return cart

@router.patch("/{cart_id}/position", response_model=GolfCartResponse, dependencies=[Depends(get_current_user)])
async def update_cart_position(
    cart_id: UUID,
    lat: float = Query(..., description="Latitude"),
    lng: float = Query(..., description="Longitude"),
    velocity: Optional[float] = Query(None, ge=0, description="Velocity in km/h"),
    db: Session = Depends(get_db)
):
    """Update golf cart position and optionally velocity"""
    service = GolfCartService(db)
    cart = service.update_cart_position(cart_id, lat, lng, velocity)
    
    if not cart:
        raise HTTPException(status_code=404, detail="Golf cart not found")
    
    return cart

@router.get("/status/{status}", response_model=List[GolfCartResponse])
async def get_carts_by_status(
    status: CartStatus,
    db: Session = Depends(get_db)
):
    """Get all golf carts with a specific status"""
    service = GolfCartService(db)
    carts = service.get_carts_by_status(status)
    return carts

@router.get("/special/running", response_model=List[GolfCartResponse])
async def get_running_carts(db: Session = Depends(get_db)):
    """Get all currently running golf carts"""
    service = GolfCartService(db)
    carts = service.get_running_carts()
    return carts

@router.get("/special/needs-maintenance", response_model=List[GolfCartResponse])
async def get_carts_needing_maintenance(db: Session = Depends(get_db)):
    """Get golf carts that need maintenance or are fixing"""
    service = GolfCartService(db)
    carts = service.get_carts_needing_maintenance()
    return carts

@router.delete("/{cart_id}", dependencies=[Depends(get_current_user)])
async def delete_cart(
    cart_id: UUID,
    db: Session = Depends(get_db)
):
    """Delete a golf cart"""
    service = GolfCartService(db)
    success = service.delete_cart(cart_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Golf cart not found")
    
    return {"message": "Golf cart deleted successfully"}