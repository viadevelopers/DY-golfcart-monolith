from pydantic import BaseModel, EmailStr, Field, HttpUrl, ConfigDict
from typing import List, Optional, Literal
from datetime import datetime, date
from uuid import UUID
from ..core.enums import Role, UserStatus, GolfCourseStatus, CartStatus, MapType

# ====================
#  Common Schemas
# ====================

class SuccessResponse(BaseModel):
    success: bool = True
    message: Optional[str] = None

class ErrorResponse(BaseModel):
    success: bool = False
    error: dict

class PaginationMeta(BaseModel):
    page: int
    limit: int
    total: int
    totalPages: int

class Location(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)

# ====================
#  User Schemas
# ====================

class UserBase(BaseModel):
    email: EmailStr
    name: str
    role: Literal['ADMIN', 'MANAGER', 'USER']
    status: Literal['ACTIVE', 'INACTIVE', 'BLOCKED']
    phone: Optional[str] = None
    department: Optional[str] = None
    golfCourseId: Optional[str] = None

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

class User(UserBase):
    id: str
    lastLoginAt: Optional[datetime] = None
    createdAt: datetime
    model_config = ConfigDict(from_attributes=True)

class UserListResponse(BaseModel):
    items: List[User]
    pagination: PaginationMeta

# ====================
#  Auth Schemas
# ====================

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    accessToken: str
    refreshToken: str

class LoginResponse(Token):
    user: User

class RefreshTokenRequest(BaseModel):
    refreshToken: str

# ====================
#  Golf Course Schemas
# ====================

class OperatingHours(BaseModel):
    weekday: Optional[str] = Field(None, pattern=r'^\d{2}:\d{2}-\d{2}:\d{2}$')
    weekend: Optional[str] = Field(None, pattern=r'^\d{2}:\d{2}-\d{2}:\d{2}$')
    holiday: Optional[str] = Field(None, pattern=r'^\d{2}:\d{2}-\d{2}:\d{2}$')

class GolfCourseBase(BaseModel):
    name: str
    description: Optional[str] = None
    address: str
    postalCode: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    status: Literal['ACTIVE', 'INACTIVE']
    location: Location
    operatingHours: Optional[OperatingHours] = None

class GolfCourse(GolfCourseBase):
    id: str
    coursesCount: int
    cartsCount: int
    createdAt: datetime
    updatedAt: datetime
    model_config = ConfigDict(from_attributes=True)

class Course(BaseModel):
    id: str
    name: str
    holes: int
    par: int
    length: Optional[float] = None

class Manager(BaseModel):
    id: str
    name: str
    role: Literal['MANAGER', 'ASSISTANT_MANAGER']
    phone: Optional[str] = None

class GolfCourseDetail(GolfCourse):
    description: Optional[str] = None
    detailAddress: Optional[str] = None
    fax: Optional[str] = None
    website: Optional[HttpUrl] = None
    facilities: Optional[List[str]] = []
    courses: Optional[List[Course]] = []
    managers: Optional[List[Manager]] = []

class GolfCourseCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    address: str
    location: Location
    detailAddress: Optional[str] = None
    postalCode: Optional[str] = None
    phone: Optional[str] = None
    fax: Optional[str] = None
    email: Optional[EmailStr] = None
    website: Optional[HttpUrl] = None
    operatingHours: Optional[OperatingHours] = None
    facilities: Optional[List[str]] = []

class GolfCourseUpdateRequest(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    location: Optional[Location] = None
    description: Optional[str] = None
    detailAddress: Optional[str] = None
    postalCode: Optional[str] = None
    phone: Optional[str] = None
    fax: Optional[str] = None
    email: Optional[EmailStr] = None
    website: Optional[HttpUrl] = None
    operatingHours: Optional[OperatingHours] = None
    facilities: Optional[List[str]] = None

class GolfCourseListResponse(BaseModel):
    items: List[GolfCourse]
    pagination: PaginationMeta

# ====================
#  Cart Schemas
# ====================

class CartLocation(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    course: Optional[str] = None
    hole: Optional[int] = None

class CartSpecifications(BaseModel):
    seatingCapacity: Optional[int] = None
    maxSpeed: Optional[float] = None
    weight: Optional[float] = None
    dimensions: Optional[dict] = None

class UsageStats(BaseModel):
    totalDistance: Optional[float] = None
    totalHours: Optional[float] = None
    todayDistance: Optional[float] = None
    todayHours: Optional[float] = None

class Cart(BaseModel):
    id: str
    cartNumber: str
    modelName: str
    golfCourseId: str
    golfCourseName: str
    status: Literal['AVAILABLE', 'IN_USE', 'MAINTENANCE', 'CHARGING']
    manufacturer: Optional[str] = None
    batteryLevel: Optional[int] = Field(None, ge=0, le=100)
    batteryStatus: Optional[Literal['NORMAL', 'LOW', 'CRITICAL']] = None
    isCharging: Optional[bool] = False
    lastMaintenance: Optional[date] = None
    nextMaintenance: Optional[date] = None
    currentLocation: Optional[CartLocation] = None
    usageStats: Optional[UsageStats] = None
    createdAt: datetime
    updatedAt: datetime
    model_config = ConfigDict(from_attributes=True)

class BatteryDetail(BaseModel):
    lastChargeTime: Optional[datetime] = None

class MaintenanceRecord(BaseModel):
    date: date
    type: Literal['REGULAR', 'REPAIR', 'EMERGENCY']
    description: str
    technician: Optional[str] = None
    cost: Optional[float] = None

class MaintenanceInfo(BaseModel):
    lastDate: Optional[date] = None
    nextDate: Optional[date] = None
    history: Optional[List[MaintenanceRecord]] = []

class CartDetail(Cart):
    manufacturingDate: Optional[date] = None
    purchaseDate: Optional[date] = None
    specifications: Optional[CartSpecifications] = None
    battery: Optional[BatteryDetail] = None
    maintenance: Optional[MaintenanceInfo] = None

class CartCreateRequest(BaseModel):
    cartNumber: str
    modelName: str
    golfCourseId: str
    manufacturer: Optional[str] = None
    manufacturingDate: Optional[date] = None
    purchaseDate: Optional[date] = None
    specifications: Optional[CartSpecifications] = None
    battery: Optional[dict] = None

class CartUpdateRequest(CartCreateRequest):
    pass

class CartListResponse(BaseModel):
    items: List[Cart]
    pagination: PaginationMeta

class CartStatusUpdateRequest(BaseModel):
    status: Literal['AVAILABLE', 'IN_USE', 'MAINTENANCE', 'CHARGING']
    note: Optional[str] = None

# ====================
#  Map Schemas
# ====================

class MapBounds(BaseModel):
    north: float
    south: float
    east: float
    west: float
    center: Optional[Location] = None

class MapLayer(BaseModel):
    id: str
    name: str
    type: Literal['polygon', 'line', 'point', 'raster']
    visible: bool
    style: Optional[dict] = None
    features: Optional[int] = None

class UserInfo(BaseModel):
    id: str
    name: str

class Map(BaseModel):
    id: str
    name: str
    golfCourseId: str
    golfCourseName: str
    type: MapType
    description: Optional[str] = None
    version: Optional[str] = None
    imageUrl: Optional[HttpUrl] = None
    thumbnailUrl: Optional[HttpUrl] = None
    metadataUrl: Optional[HttpUrl] = None
    bounds: Optional[MapBounds] = None
    layers: Optional[List[MapLayer]] = []
    fileSize: Optional[int] = None
    resolution: Optional[str] = None
    createdAt: datetime
    updatedAt: datetime
    model_config = ConfigDict(from_attributes=True)

class MapDetail(Map):
    createdBy: Optional[UserInfo] = None
    updatedBy: Optional[UserInfo] = None
    # Other detail fields can be added here

class MapCreateRequest(BaseModel):
    name: str
    golfCourseId: str
    type: MapType
    bounds: MapBounds
    description: Optional[str] = None

class MapUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    version: Optional[str] = None

class MapListResponse(BaseModel):
    items: List[Map]
    pagination: PaginationMeta
