"""
Telemetry API endpoints for cart data and analytics.
"""
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import AuthContext, get_current_user, require_manufacturer
from app.models import CartTelemetry, CartEvent, GolfCart, GolfCourse
from app.services import get_telemetry_service, get_realtime_processor
from app.schemas.telemetry import (
    TelemetryData,
    TelemetryHistory,
    CartEvent as CartEventSchema,
    AcknowledgeEvent,
    ResolveEvent,
    PerformanceAnalytics,
    FleetAnalytics,
    BatteryTrendAnalysis,
    CartStatusSummary,
    DashboardMetrics,
    TelemetryProcessingResult,
    ProcessorMetrics,
    TelemetryCreate
)

router = APIRouter()


# Telemetry data endpoints
@router.get("/cart/{cart_id}/current", response_model=Optional[CartStatusSummary])
async def get_cart_current_status(
    cart_id: UUID,
    current_user: AuthContext = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current status and latest telemetry for a specific cart."""
    # Verify cart exists and user has access
    cart = db.query(GolfCart).filter(GolfCart.id == cart_id).first()
    if not cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart not found"
        )
    
    # Check access permissions based on user type
    if current_user.user_type == "golf_course" and cart.golf_course_id != current_user.golf_course_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this cart"
        )
    
    telemetry_service = get_telemetry_service()
    cart_status = telemetry_service.get_cart_current_status(cart_id)
    
    return cart_status


@router.get("/cart/{cart_id}/history", response_model=List[TelemetryHistory])
async def get_cart_telemetry_history(
    cart_id: UUID,
    start_time: datetime = Query(..., description="Start time for data range"),
    end_time: datetime = Query(..., description="End time for data range"),
    metrics: Optional[List[str]] = Query(None, description="Specific metrics to include"),
    current_user: AuthContext = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get historical telemetry data for a cart."""
    # Verify cart exists and user has access
    cart = db.query(GolfCart).filter(GolfCart.id == cart_id).first()
    if not cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart not found"
        )
    
    # Check access permissions
    if current_user.user_type == "golf_course" and cart.golf_course_id != current_user.golf_course_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this cart"
        )
    
    # Validate time range
    if end_time <= start_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="End time must be after start time"
        )
    
    # Limit time range to prevent excessive queries
    max_days = 30
    if (end_time - start_time).days > max_days:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Time range cannot exceed {max_days} days"
        )
    
    telemetry_service = get_telemetry_service()
    history = telemetry_service.get_telemetry_history(cart_id, start_time, end_time, metrics)
    
    return history


@router.post("/cart/{cart_id}/telemetry", response_model=TelemetryProcessingResult)
async def submit_cart_telemetry(
    cart_id: UUID,
    telemetry_data: TelemetryCreate,
    current_user: AuthContext = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Submit telemetry data for a cart (typically used by cart systems)."""
    # Verify cart exists
    cart = db.query(GolfCart).filter(GolfCart.id == cart_id).first()
    if not cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart not found"
        )
    
    # Only allow cart systems or manufacturers to submit telemetry
    if current_user.user_type not in ["cart_system", "manufacturer"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only cart systems and manufacturers can submit telemetry"
        )
    
    telemetry_service = get_telemetry_service()
    result = await telemetry_service.process_telemetry(str(cart_id), telemetry_data.model_dump())
    
    if result.get('status') == 'error':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get('message', 'Telemetry processing failed')
        )
    
    return TelemetryProcessingResult(**result)


# Event management endpoints
@router.get("/cart/{cart_id}/events", response_model=List[CartEventSchema])
async def get_cart_events(
    cart_id: UUID,
    severity: Optional[str] = Query(None, description="Filter by severity"),
    resolved: Optional[bool] = Query(None, description="Filter by resolution status"),
    limit: int = Query(50, ge=1, le=500, description="Maximum number of events"),
    current_user: AuthContext = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get events for a specific cart."""
    # Verify cart exists and user has access
    cart = db.query(GolfCart).filter(GolfCart.id == cart_id).first()
    if not cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart not found"
        )
    
    # Check access permissions
    if current_user.user_type == "golf_course" and cart.golf_course_id != current_user.golf_course_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this cart"
        )
    
    # Build query
    query = db.query(CartEvent).filter(CartEvent.cart_id == cart_id)
    
    if severity:
        query = query.filter(CartEvent.severity == severity.upper())
    
    if resolved is not None:
        query = query.filter(CartEvent.resolved == resolved)
    
    events = query.order_by(CartEvent.timestamp.desc()).limit(limit).all()
    
    return events


@router.patch("/events/{event_id}/acknowledge", response_model=CartEventSchema)
async def acknowledge_event(
    event_id: UUID,
    acknowledge_data: AcknowledgeEvent,
    current_user: AuthContext = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Acknowledge a cart event."""
    event = db.query(CartEvent).filter(CartEvent.id == event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    # Check access permissions
    if current_user.user_type == "golf_course":
        cart = db.query(GolfCart).filter(GolfCart.id == event.cart_id).first()
        if cart and cart.golf_course_id != current_user.golf_course_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this event"
            )
    
    # Update event
    event.acknowledged = True
    event.acknowledged_by = current_user.user_id
    event.acknowledged_at = datetime.utcnow()
    if acknowledge_data.resolution_notes:
        event.resolution_notes = acknowledge_data.resolution_notes
    
    db.commit()
    db.refresh(event)
    
    return event


@router.patch("/events/{event_id}/resolve", response_model=CartEventSchema)
async def resolve_event(
    event_id: UUID,
    resolve_data: ResolveEvent,
    current_user: AuthContext = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Resolve a cart event."""
    event = db.query(CartEvent).filter(CartEvent.id == event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    # Check access permissions
    if current_user.user_type == "golf_course":
        cart = db.query(GolfCart).filter(GolfCart.id == event.cart_id).first()
        if cart and cart.golf_course_id != current_user.golf_course_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this event"
            )
    
    # Update event
    event.resolved = True
    event.resolved_at = datetime.utcnow()
    event.resolution_notes = resolve_data.resolution_notes
    
    # Also acknowledge if not already acknowledged
    if not event.acknowledged:
        event.acknowledged = True
        event.acknowledged_by = current_user.user_id
        event.acknowledged_at = datetime.utcnow()
    
    db.commit()
    db.refresh(event)
    
    return event


# Analytics endpoints
@router.get("/cart/{cart_id}/analytics", response_model=PerformanceAnalytics)
async def get_cart_analytics(
    cart_id: UUID,
    days: int = Query(7, ge=1, le=365, description="Number of days to analyze"),
    current_user: AuthContext = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get performance analytics for a specific cart."""
    # Verify cart exists and user has access
    cart = db.query(GolfCart).filter(GolfCart.id == cart_id).first()
    if not cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart not found"
        )
    
    # Check access permissions
    if current_user.user_type == "golf_course" and cart.golf_course_id != current_user.golf_course_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this cart"
        )
    
    telemetry_service = get_telemetry_service()
    analytics = telemetry_service.get_performance_analytics(cart_id, days)
    
    if "error" in analytics:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=analytics["error"]
        )
    
    return PerformanceAnalytics(**analytics)


@router.get("/cart/{cart_id}/battery-trend", response_model=BatteryTrendAnalysis)
async def get_battery_trend_analysis(
    cart_id: UUID,
    hours: int = Query(24, ge=1, le=168, description="Number of hours to analyze"),
    current_user: AuthContext = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get battery trend analysis for predictive maintenance."""
    # Verify cart exists and user has access
    cart = db.query(GolfCart).filter(GolfCart.id == cart_id).first()
    if not cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart not found"
        )
    
    # Check access permissions
    if current_user.user_type == "golf_course" and cart.golf_course_id != current_user.golf_course_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this cart"
        )
    
    telemetry_service = get_telemetry_service()
    analysis = telemetry_service.get_battery_trend_analysis(cart_id, hours)
    
    if "error" in analysis:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=analysis["error"]
        )
    
    if analysis.get("insufficient_data"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Insufficient battery data for trend analysis"
        )
    
    return BatteryTrendAnalysis(**analysis)


# Golf course dashboard endpoints
@router.get("/golf-course/{golf_course_id}/dashboard", response_model=DashboardMetrics)
async def get_golf_course_dashboard(
    golf_course_id: UUID,
    current_user: AuthContext = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get dashboard metrics for a golf course."""
    # Verify golf course exists
    golf_course = db.query(GolfCourse).filter(GolfCourse.id == golf_course_id).first()
    if not golf_course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Golf course not found"
        )
    
    # Check access permissions
    if (current_user.user_type == "golf_course" and 
        current_user.golf_course_id != golf_course_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this golf course"
        )
    
    telemetry_service = get_telemetry_service()
    dashboard = telemetry_service.get_golf_course_dashboard(golf_course_id)
    
    if "error" in dashboard:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=dashboard["error"]
        )
    
    return DashboardMetrics(**dashboard)


@router.get("/golf-course/{golf_course_id}/fleet-analytics", response_model=FleetAnalytics)
async def get_fleet_analytics(
    golf_course_id: UUID,
    days: int = Query(7, ge=1, le=365, description="Number of days to analyze"),
    current_user: AuthContext = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get fleet-wide analytics for a golf course."""
    # Verify golf course exists
    golf_course = db.query(GolfCourse).filter(GolfCourse.id == golf_course_id).first()
    if not golf_course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Golf course not found"
        )
    
    # Check access permissions
    if (current_user.user_type == "golf_course" and 
        current_user.golf_course_id != golf_course_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this golf course"
        )
    
    telemetry_service = get_telemetry_service()
    analytics = telemetry_service.get_fleet_analytics(golf_course_id, days)
    
    if "error" in analytics:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=analytics["error"]
        )
    
    return FleetAnalytics(**analytics)


# System monitoring endpoints (manufacturer only)
@router.get("/processor/metrics", response_model=ProcessorMetrics)
async def get_processor_metrics(
    current_user: AuthContext = Depends(require_manufacturer)
):
    """Get real-time telemetry processor metrics (manufacturer only)."""
    processor = get_realtime_processor()
    metrics = processor.get_metrics()
    
    return ProcessorMetrics(**metrics)


@router.post("/processor/reset-metrics")
async def reset_processor_metrics(
    current_user: AuthContext = Depends(require_manufacturer)
):
    """Reset processor metrics (manufacturer only)."""
    processor = get_realtime_processor()
    processor.reset_metrics()
    
    return {"message": "Processor metrics reset successfully"}


# Manufacturer overview endpoints
@router.get("/manufacturer/overview", response_model=List[DashboardMetrics])
async def get_manufacturer_overview(
    current_user: AuthContext = Depends(require_manufacturer),
    db: Session = Depends(get_db)
):
    """Get overview of all golf courses for manufacturer."""
    # Get all golf courses
    golf_courses = db.query(GolfCourse).all()
    
    telemetry_service = get_telemetry_service()
    overviews = []
    
    for golf_course in golf_courses:
        dashboard = telemetry_service.get_golf_course_dashboard(golf_course.id)
        if "error" not in dashboard:
            overviews.append(DashboardMetrics(**dashboard))
    
    return overviews


@router.get("/manufacturer/fleet-summary")
async def get_manufacturer_fleet_summary(
    current_user: AuthContext = Depends(require_manufacturer),
    db: Session = Depends(get_db)
):
    """Get summary of all fleets across all golf courses."""
    # Get total cart counts
    total_carts = db.query(GolfCart).count()
    
    # Get online carts (pinged within 2 minutes)
    online_threshold = datetime.utcnow() - timedelta(minutes=2)
    online_carts = db.query(GolfCart).filter(
        GolfCart.last_ping > online_threshold
    ).count()
    
    # Get recent critical events
    recent_threshold = datetime.utcnow() - timedelta(hours=24)
    critical_events = db.query(CartEvent).filter(
        CartEvent.severity == "CRITICAL",
        CartEvent.timestamp > recent_threshold,
        CartEvent.resolved == False
    ).count()
    
    # Get golf course count
    golf_courses = db.query(GolfCourse).count()
    
    return {
        "total_golf_courses": golf_courses,
        "total_carts": total_carts,
        "online_carts": online_carts,
        "offline_carts": total_carts - online_carts,
        "online_percentage": round((online_carts / total_carts * 100) if total_carts > 0 else 0, 1),
        "critical_events_24h": critical_events,
        "system_health": "Good" if critical_events < 5 else "Needs Attention" if critical_events < 20 else "Critical"
    }