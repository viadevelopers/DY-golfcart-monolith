"""
Telemetry data schemas for API request/response models.
"""
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum


class EventSeverity(str, Enum):
    """Event severity levels."""
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class EventCategory(str, Enum):
    """Event categories."""
    OPERATIONAL = "OPERATIONAL"
    MAINTENANCE = "MAINTENANCE"
    SAFETY = "SAFETY"
    SYSTEM = "SYSTEM"


class EngineStatus(str, Enum):
    """Engine status options."""
    ON = "ON"
    OFF = "OFF"
    ERROR = "ERROR"
    IDLE = "IDLE"
    UNKNOWN = "UNKNOWN"


class BatteryHealthStatus(str, Enum):
    """Battery health assessment levels."""
    EXCELLENT = "Excellent"
    GOOD = "Good"
    FAIR = "Fair"
    POOR = "Poor"
    UNKNOWN = "Unknown"


# Base schemas
class TelemetryBase(BaseModel):
    """Base telemetry data."""
    model_config = ConfigDict(from_attributes=True)
    
    latitude: float = Field(..., ge=-90, le=90, description="Latitude coordinate")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude coordinate")
    altitude: Optional[float] = Field(None, description="Altitude in meters")
    heading: Optional[float] = Field(None, ge=0, le=359.99, description="Heading in degrees")
    speed: Optional[float] = Field(None, ge=0, description="Speed in km/h")
    acceleration: Optional[float] = Field(None, description="Acceleration in m/s²")
    
    battery_level: Optional[int] = Field(None, ge=0, le=100, description="Battery level percentage")
    battery_voltage: Optional[float] = Field(None, ge=0, description="Battery voltage")
    battery_current: Optional[float] = Field(None, description="Battery current in amps")
    battery_temperature: Optional[float] = Field(None, description="Battery temperature in Celsius")
    charging_status: Optional[bool] = Field(None, description="Whether cart is charging")
    
    engine_status: Optional[EngineStatus] = Field(None, description="Engine status")
    brake_status: Optional[bool] = Field(None, description="Brake status")
    emergency_stop: Optional[bool] = Field(None, description="Emergency stop status")
    
    external_temperature: Optional[float] = Field(None, description="External temperature in Celsius")
    gps_satellites: Optional[int] = Field(None, ge=0, description="Number of GPS satellites")
    gps_hdop: Optional[float] = Field(None, ge=0, description="GPS horizontal dilution of precision")
    
    cpu_usage: Optional[float] = Field(None, ge=0, le=100, description="CPU usage percentage")
    memory_usage: Optional[float] = Field(None, ge=0, le=100, description="Memory usage percentage")
    disk_usage: Optional[float] = Field(None, ge=0, le=100, description="Disk usage percentage")
    
    sensor_data: Optional[Dict[str, Any]] = Field(None, description="Additional sensor data")
    ip_address: Optional[str] = Field(None, description="Cart IP address")


class TelemetryCreate(TelemetryBase):
    """Schema for creating telemetry data."""
    pass


class TelemetryData(TelemetryBase):
    """Schema for telemetry data response."""
    id: int
    cart_id: UUID
    timestamp: datetime
    created_at: datetime


class TelemetryHistory(BaseModel):
    """Schema for historical telemetry data."""
    model_config = ConfigDict(from_attributes=True)
    
    timestamp: datetime
    position: Optional[List[float]] = Field(None, description="[latitude, longitude] coordinates")
    battery_level: Optional[int]
    speed: Optional[float]
    heading: Optional[float]
    engine_status: Optional[EngineStatus]
    charging_status: Optional[bool]
    
    # Optional detailed metrics
    altitude: Optional[float] = None
    acceleration: Optional[float] = None
    battery_voltage: Optional[float] = None
    battery_current: Optional[float] = None
    battery_temperature: Optional[float] = None
    brake_status: Optional[bool] = None
    emergency_stop: Optional[bool] = None
    external_temperature: Optional[float] = None
    gps_satellites: Optional[int] = None
    gps_hdop: Optional[float] = None
    cpu_usage: Optional[float] = None
    memory_usage: Optional[float] = None
    disk_usage: Optional[float] = None


# Event schemas
class CartEventBase(BaseModel):
    """Base cart event data."""
    model_config = ConfigDict(from_attributes=True)
    
    event_type: str = Field(..., description="Event type identifier")
    event_category: EventCategory = Field(..., description="Event category")
    severity: EventSeverity = Field(..., description="Event severity level")
    title: str = Field(..., max_length=200, description="Event title")
    description: Optional[str] = Field(None, description="Event description")
    event_data: Dict[str, Any] = Field(default_factory=dict, description="Event-specific data")
    position: Optional[List[float]] = Field(None, description="[latitude, longitude] where event occurred")
    duration_seconds: Optional[int] = Field(None, description="Event duration if applicable")


class CartEventCreate(CartEventBase):
    """Schema for creating cart events."""
    cart_id: UUID


class CartEvent(CartEventBase):
    """Schema for cart event response."""
    id: UUID
    cart_id: UUID
    timestamp: datetime
    acknowledged: bool = False
    acknowledged_by: Optional[UUID] = None
    acknowledged_at: Optional[datetime] = None
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    auto_actions: Optional[List[str]] = None
    
    # Related entities
    related_geofence_id: Optional[UUID] = None
    related_route_id: Optional[UUID] = None
    related_assignment_id: Optional[UUID] = None
    
    created_at: datetime
    updated_at: datetime


class AcknowledgeEvent(BaseModel):
    """Schema for acknowledging an event."""
    resolution_notes: Optional[str] = Field(None, description="Notes about the acknowledgment")


class ResolveEvent(BaseModel):
    """Schema for resolving an event."""
    resolution_notes: str = Field(..., description="Resolution notes")


# Analytics schemas
class BatteryAnalytics(BaseModel):
    """Battery performance analytics."""
    average_level: float = Field(..., description="Average battery level")
    minimum_level: int = Field(..., description="Minimum battery level recorded")
    maximum_level: int = Field(..., description="Maximum battery level recorded")


class SpeedAnalytics(BaseModel):
    """Speed performance analytics."""
    average_speed_kmh: float = Field(..., description="Average speed in km/h")
    maximum_speed_kmh: float = Field(..., description="Maximum speed in km/h")


class SystemPerformance(BaseModel):
    """System performance metrics."""
    average_cpu_usage: float = Field(..., description="Average CPU usage percentage")
    average_memory_usage: float = Field(..., description="Average memory usage percentage")
    average_disk_usage: float = Field(..., description="Average disk usage percentage")


class PerformanceAnalytics(BaseModel):
    """Comprehensive performance analytics."""
    cart_id: UUID
    analysis_period_days: int
    data_points: int
    uptime_hours: float
    
    battery_analytics: BatteryAnalytics
    speed_analytics: SpeedAnalytics
    system_performance: SystemPerformance
    
    distance_traveled_km: float
    event_summary: Dict[str, int] = Field(..., description="Event counts by severity")
    total_events: int


class FleetMetrics(BaseModel):
    """Fleet-wide metrics."""
    average_battery_level: float
    average_speed_kmh: float
    total_data_points: int


class TopIssue(BaseModel):
    """Top fleet issue."""
    event_type: str
    count: int
    description: str


class FleetAnalytics(BaseModel):
    """Fleet-wide analytics."""
    golf_course_id: UUID
    analysis_period_days: int
    total_carts: int
    active_carts: int
    utilization_rate: float
    fleet_metrics: FleetMetrics
    top_issues: List[TopIssue]


class BatteryTrendAnalysis(BaseModel):
    """Battery trend analysis for predictive maintenance."""
    cart_id: UUID
    analysis_period_hours: int
    current_battery_level: int
    is_charging: bool
    average_discharge_rate_percent_per_hour: float
    discharge_periods_analyzed: int
    charge_periods_analyzed: int
    predicted_hours_to_critical: Optional[float]
    battery_health_status: BatteryHealthStatus


class CartStatusSummary(BaseModel):
    """Current cart status summary."""
    cart_id: UUID
    serial_number: str
    cart_number: Optional[str]
    status: str
    is_online: bool
    last_ping: datetime
    
    position: Optional[Dict[str, Optional[float]]] = Field(
        None, 
        description="Current position with latitude/longitude"
    )
    
    telemetry: Dict[str, Any] = Field(
        ...,
        description="Latest telemetry data"
    )
    
    active_events: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Recent unresolved events"
    )


class DashboardMetrics(BaseModel):
    """Golf course dashboard metrics."""
    golf_course_id: UUID
    total_carts: int
    online_carts: int
    active_events: int
    carts: List[CartStatusSummary]


# Query parameters
class TelemetryHistoryQuery(BaseModel):
    """Query parameters for telemetry history."""
    start_time: datetime = Field(..., description="Start time for data range")
    end_time: datetime = Field(..., description="End time for data range")
    metrics: Optional[List[str]] = Field(None, description="Specific metrics to include")


class AnalyticsQuery(BaseModel):
    """Query parameters for analytics."""
    days: int = Field(7, ge=1, le=365, description="Number of days to analyze")


class BatteryTrendQuery(BaseModel):
    """Query parameters for battery trend analysis."""
    hours: int = Field(24, ge=1, le=168, description="Number of hours to analyze")


# Processing responses
class TelemetryProcessingResult(BaseModel):
    """Result of telemetry processing."""
    status: str = Field(..., description="Processing status (success/error)")
    telemetry_id: Optional[str] = Field(None, description="Created telemetry record ID")
    events_generated: int = Field(0, description="Number of events generated")
    events: List[Dict[str, Any]] = Field(default_factory=list, description="Generated events")
    message: Optional[str] = Field(None, description="Processing message or error")


class ProcessorMetrics(BaseModel):
    """Real-time processor metrics."""
    processed_messages: int
    failed_messages: int
    success_rate: float
    messages_per_second: float
    buffered_messages: int
    active_global_subscribers: int
    active_cart_subscribers: int
    uptime_seconds: float
    processing_active: bool