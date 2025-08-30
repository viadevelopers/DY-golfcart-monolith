-- ============================================
-- 1. 골프장 관리 (Golf Course Management)
-- ============================================

-- 골프장 기본 정보
CREATE TABLE golf_courses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    code VARCHAR(20) UNIQUE NOT NULL, -- 골프장 코드
    address TEXT,
    phone VARCHAR(20),
    email VARCHAR(100),
    operating_hours JSONB, -- {"open": "06:00", "close": "18:00"}
    hole_count INT DEFAULT 18,
    status VARCHAR(20) DEFAULT 'ACTIVE', -- ACTIVE, INACTIVE, MAINTENANCE
    metadata JSONB, -- 추가 설정 정보
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    created_by UUID,
    CONSTRAINT chk_status CHECK (status IN ('ACTIVE', 'INACTIVE', 'MAINTENANCE'))
);

-- 골프장별 지도 정보
CREATE TABLE golf_course_maps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    golf_course_id UUID NOT NULL REFERENCES golf_courses(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    version VARCHAR(20) NOT NULL,
    map_data JSONB, -- 지도 메타데이터
    tile_url VARCHAR(500), -- S3 타일 URL 패턴
    bounds GEOMETRY(POLYGON, 4326), -- 지도 경계
    center_point GEOMETRY(POINT, 4326), -- 중심점
    zoom_levels INT[], -- 사용 가능한 줌 레벨
    is_active BOOLEAN DEFAULT true,
    uploaded_at TIMESTAMP DEFAULT NOW(),
    uploaded_by UUID,
    UNIQUE(golf_course_id, version)
);

-- 코스/홀 정보
CREATE TABLE holes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    golf_course_id UUID NOT NULL REFERENCES golf_courses(id) ON DELETE CASCADE,
    hole_number INT NOT NULL,
    par INT NOT NULL,
    distance_meters INT,
    tee_position GEOMETRY(POINT, 4326),
    green_position GEOMETRY(POINT, 4326),
    hole_boundary GEOMETRY(POLYGON, 4326),
    hazards JSONB, -- 해저드 정보
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(golf_course_id, hole_number)
);

-- ============================================
-- 2. 골프카트 관리 (Golf Cart Management)
-- ============================================

-- 카트 모델 정보 (제조사 관리)
CREATE TABLE cart_models (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    manufacturer VARCHAR(50) NOT NULL,
    model_name VARCHAR(50) NOT NULL,
    model_code VARCHAR(30) UNIQUE NOT NULL,
    capacity INT DEFAULT 2, -- 탑승 인원
    max_speed FLOAT DEFAULT 20.0, -- km/h
    battery_capacity INT, -- Ah
    features JSONB, -- 기능 목록
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(manufacturer, model_code)
);

-- 개별 카트 정보
CREATE TABLE golf_carts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    serial_number VARCHAR(50) UNIQUE NOT NULL,
    cart_model_id UUID REFERENCES cart_models(id),
    golf_course_id UUID REFERENCES golf_courses(id),
    cart_number VARCHAR(20), -- 골프장 내 카트 번호
    status VARCHAR(20) DEFAULT 'IDLE', -- IDLE, RUNNING, CHARGING, MAINTENANCE, OFFLINE
    mode VARCHAR(20) DEFAULT 'MANUAL', -- MANUAL, AUTONOMOUS, REMOTE
    firmware_version VARCHAR(20),
    installed_date DATE,
    last_maintenance_date DATE,
    total_distance_km FLOAT DEFAULT 0,
    total_operating_hours INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(golf_course_id, cart_number),
    CONSTRAINT chk_cart_status CHECK (status IN ('IDLE', 'RUNNING', 'CHARGING', 'MAINTENANCE', 'OFFLINE')),
    CONSTRAINT chk_cart_mode CHECK (mode IN ('MANUAL', 'AUTONOMOUS', 'REMOTE'))
);

-- ============================================
-- 3. 경로 및 네비게이션 (Routes & Navigation)
-- ============================================

-- 사전 정의된 경로
CREATE TABLE routes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    golf_course_id UUID NOT NULL REFERENCES golf_courses(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    route_type VARCHAR(30) NOT NULL, -- HOLE_TO_HOLE, RETURN_TO_BASE, CHARGING_STATION
    path GEOMETRY(LINESTRING, 4326) NOT NULL,
    distance_meters FLOAT,
    estimated_time_seconds INT,
    waypoints JSONB, -- 중간 경유지 정보
    restrictions JSONB, -- 속도 제한, 진입 금지 구역 등
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    created_by UUID,
    CONSTRAINT chk_route_type CHECK (route_type IN ('HOLE_TO_HOLE', 'RETURN_TO_BASE', 'CHARGING_STATION', 'CUSTOM'))
);

-- 지오펜스 (제한/위험 구역)
CREATE TABLE geofences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    golf_course_id UUID NOT NULL REFERENCES golf_courses(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    fence_type VARCHAR(30) NOT NULL, -- RESTRICTED, SLOW_ZONE, NO_ENTRY, HAZARD
    geometry GEOMETRY(POLYGON, 4326) NOT NULL,
    speed_limit FLOAT, -- km/h (SLOW_ZONE인 경우)
    alert_level VARCHAR(20), -- INFO, WARNING, CRITICAL
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT chk_fence_type CHECK (fence_type IN ('RESTRICTED', 'SLOW_ZONE', 'NO_ENTRY', 'HAZARD'))
);

-- ============================================
-- 4. 실시간 데이터 (Real-time Data)
-- ============================================

-- 카트 텔레메트리 데이터 (시계열, 파티셔닝 대상)
CREATE TABLE cart_telemetry (
    id BIGSERIAL,
    cart_id UUID NOT NULL REFERENCES golf_carts(id),
    timestamp TIMESTAMP NOT NULL,
    position GEOMETRY(POINT, 4326) NOT NULL,
    heading FLOAT, -- 0-360도
    speed FLOAT, -- km/h
    battery_level INT, -- 0-100%
    battery_voltage FLOAT,
    battery_current FLOAT,
    battery_temperature FLOAT,
    motor_temperature FLOAT,
    total_distance_session FLOAT, -- 이번 세션 주행거리
    altitude FLOAT,
    satellites INT, -- GPS 위성 수
    hdop FLOAT, -- GPS 정확도
    sensor_data JSONB, -- 기타 센서 데이터
    created_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (cart_id, timestamp)
) PARTITION BY RANGE (timestamp);

-- 월별 파티션 생성 예시
CREATE TABLE cart_telemetry_2025_01 PARTITION OF cart_telemetry
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
CREATE TABLE cart_telemetry_2025_02 PARTITION OF cart_telemetry
    FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');

-- 카트 이벤트 로그
CREATE TABLE cart_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cart_id UUID NOT NULL REFERENCES golf_carts(id),
    event_type VARCHAR(50) NOT NULL, -- GEOFENCE_ENTRY, COLLISION_WARNING, EMERGENCY_STOP, etc
    severity VARCHAR(20) NOT NULL, -- INFO, WARNING, ERROR, CRITICAL
    event_data JSONB NOT NULL,
    position GEOMETRY(POINT, 4326),
    timestamp TIMESTAMP NOT NULL,
    resolved BOOLEAN DEFAULT false,
    resolved_at TIMESTAMP,
    resolved_by UUID,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================
-- 5. 명령 및 제어 (Command & Control)
-- ============================================

-- 카트 제어 명령 로그
CREATE TABLE cart_commands (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cart_id UUID NOT NULL REFERENCES golf_carts(id),
    command_type VARCHAR(50) NOT NULL, -- START, STOP, SET_SPEED, RETURN_TO_BASE, etc
    command_data JSONB NOT NULL,
    source VARCHAR(30) NOT NULL, -- SYSTEM, OPERATOR, SCHEDULE, EMERGENCY
    status VARCHAR(20) DEFAULT 'PENDING', -- PENDING, SENT, ACKNOWLEDGED, COMPLETED, FAILED
    sent_at TIMESTAMP,
    acknowledged_at TIMESTAMP,
    completed_at TIMESTAMP,
    response_data JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    created_by UUID,
    CONSTRAINT chk_command_status CHECK (status IN ('PENDING', 'SENT', 'ACKNOWLEDGED', 'COMPLETED', 'FAILED'))
);

-- ============================================
-- 6. 사용자 및 권한 (Users & Permissions)
-- ============================================

-- 사용자 정보
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    role VARCHAR(30) NOT NULL, -- MASTER_ADMIN, GOLF_ADMIN, OPERATOR, VIEWER
    golf_course_id UUID REFERENCES golf_courses(id), -- NULL for MASTER_ADMIN
    password_hash TEXT NOT NULL,
    is_active BOOLEAN DEFAULT true,
    last_login_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT chk_user_role CHECK (role IN ('MASTER_ADMIN', 'GOLF_ADMIN', 'OPERATOR', 'VIEWER'))
);

-- ============================================
-- 7. 예약 및 운영 (Reservation & Operation)
-- ============================================

-- 카트 예약/배정
CREATE TABLE cart_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    golf_course_id UUID NOT NULL REFERENCES golf_courses(id),
    cart_id UUID NOT NULL REFERENCES golf_carts(id),
    reservation_code VARCHAR(20) UNIQUE,
    player_name VARCHAR(100),
    player_phone VARCHAR(20),
    player_count INT DEFAULT 1,
    start_hole INT,
    scheduled_start TIMESTAMP NOT NULL,
    scheduled_end TIMESTAMP,
    actual_start TIMESTAMP,
    actual_end TIMESTAMP,
    status VARCHAR(20) DEFAULT 'RESERVED', -- RESERVED, ACTIVE, COMPLETED, CANCELLED
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    created_by UUID,
    CONSTRAINT chk_assignment_status CHECK (status IN ('RESERVED', 'ACTIVE', 'COMPLETED', 'CANCELLED'))
);

-- ============================================
-- 8. 유지보수 (Maintenance)
-- ============================================

-- 유지보수 기록
CREATE TABLE maintenance_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cart_id UUID NOT NULL REFERENCES golf_carts(id),
    maintenance_type VARCHAR(50) NOT NULL, -- ROUTINE, REPAIR, BATTERY, SOFTWARE_UPDATE
    description TEXT,
    parts_replaced JSONB, -- 교체 부품 목록
    cost DECIMAL(10, 2),
    performed_at TIMESTAMP NOT NULL,
    performed_by VARCHAR(100),
    next_maintenance_date DATE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================
-- 9. 시스템 설정 (System Configuration)
-- ============================================

-- 시스템 파라미터 (키-값 저장소)
CREATE TABLE system_parameters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    golf_course_id UUID REFERENCES golf_courses(id), -- NULL for global settings
    category VARCHAR(50) NOT NULL,
    key VARCHAR(100) NOT NULL,
    value TEXT NOT NULL,
    data_type VARCHAR(20) NOT NULL, -- STRING, NUMBER, BOOLEAN, JSON
    description TEXT,
    is_encrypted BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(golf_course_id, category, key)
);

-- ============================================
-- 인덱스 생성
-- ============================================

-- 텔레메트리 조회 성능
CREATE INDEX idx_cart_telemetry_cart_timestamp ON cart_telemetry(cart_id, timestamp DESC);
CREATE INDEX idx_cart_telemetry_position ON cart_telemetry USING GIST(position);

-- 이벤트 조회
CREATE INDEX idx_cart_events_cart_timestamp ON cart_events(cart_id, timestamp DESC);
CREATE INDEX idx_cart_events_type_severity ON cart_events(event_type, severity);
CREATE INDEX idx_cart_events_position ON cart_events USING GIST(position);

-- 카트 상태 조회
CREATE INDEX idx_golf_carts_course_status ON golf_carts(golf_course_id, status);

-- 명령 조회
CREATE INDEX idx_cart_commands_cart_status ON cart_commands(cart_id, status);
CREATE INDEX idx_cart_commands_created ON cart_commands(created_at DESC);

-- 지오펜스 공간 검색
CREATE INDEX idx_geofences_geometry ON geofences USING GIST(geometry);
CREATE INDEX idx_routes_path ON routes USING GIST(path);

-- 예약 조회
CREATE INDEX idx_assignments_course_date ON cart_assignments(golf_course_id, scheduled_start);
CREATE INDEX idx_assignments_cart_status ON cart_assignments(cart_id, status);

-- ============================================
-- 뷰 생성 (자주 사용되는 조회)
-- ============================================

-- 카트 최신 상태 뷰
CREATE OR REPLACE VIEW v_cart_current_status AS
SELECT 
    c.id,
    c.serial_number,
    c.cart_number,
    c.golf_course_id,
    gc.name as golf_course_name,
    c.status,
    c.mode,
    t.position,
    t.speed,
    t.battery_level,
    t.timestamp as last_update
FROM golf_carts c
LEFT JOIN golf_courses gc ON c.golf_course_id = gc.id
LEFT JOIN LATERAL (
    SELECT * FROM cart_telemetry 
    WHERE cart_id = c.id 
    ORDER BY timestamp DESC 
    LIMIT 1
) t ON true;

-- 골프장별 카트 운영 현황
CREATE OR REPLACE VIEW v_golf_course_cart_summary AS
SELECT 
    gc.id as golf_course_id,
    gc.name as golf_course_name,
    COUNT(c.id) as total_carts,
    COUNT(CASE WHEN c.status = 'RUNNING' THEN 1 END) as running_carts,
    COUNT(CASE WHEN c.status = 'IDLE' THEN 1 END) as idle_carts,
    COUNT(CASE WHEN c.status = 'CHARGING' THEN 1 END) as charging_carts,
    COUNT(CASE WHEN c.status = 'MAINTENANCE' THEN 1 END) as maintenance_carts,
    COUNT(CASE WHEN c.status = 'OFFLINE' THEN 1 END) as offline_carts
FROM golf_courses gc
LEFT JOIN golf_carts c ON gc.id = c.golf_course_id
GROUP BY gc.id, gc.name;
