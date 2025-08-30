-- ============================================
-- 1. 사용자 관리 (간소화)
-- ============================================

-- 제조사 관계자
CREATE TABLE manufacturer_users (
id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
email VARCHAR(100) UNIQUE NOT NULL,
name VARCHAR(100) NOT NULL,
phone VARCHAR(20),
department VARCHAR(50),
password_hash TEXT NOT NULL,
is_active BOOLEAN DEFAULT true,
created_at TIMESTAMP DEFAULT NOW(),
updated_at TIMESTAMP DEFAULT NOW()
);

-- 골프장 관계자
CREATE TABLE golf_course_users (
id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
golf_course_id UUID NOT NULL,
email VARCHAR(100) UNIQUE NOT NULL,
name VARCHAR(100) NOT NULL,
phone VARCHAR(20),
position VARCHAR(50),
password_hash TEXT NOT NULL,
is_active BOOLEAN DEFAULT true,
created_at TIMESTAMP DEFAULT NOW(),
updated_at TIMESTAMP DEFAULT NOW()
);

-- ============================================
-- 2. 골프장 관리
-- ============================================

CREATE TABLE golf_courses (
id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
name VARCHAR(100) NOT NULL,
code VARCHAR(20) UNIQUE NOT NULL,
address TEXT,
phone VARCHAR(20),
email VARCHAR(100),
hole_count INT DEFAULT 18,
status VARCHAR(20) DEFAULT 'ACTIVE',
metadata JSONB,
created_by UUID REFERENCES manufacturer_users(id),
created_at TIMESTAMP DEFAULT NOW(),
updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE golf_course_maps (
id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
golf_course_id UUID NOT NULL REFERENCES golf_courses(id),
name VARCHAR(100) NOT NULL,
version VARCHAR(20) NOT NULL,
tile_url VARCHAR(500),
bounds GEOMETRY(POLYGON, 4326),
center_point GEOMETRY(POINT, 4326),
zoom_levels INT[],
is_active BOOLEAN DEFAULT true,
uploaded_by UUID REFERENCES manufacturer_users(id),
uploaded_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE holes (
id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
golf_course_id UUID NOT NULL REFERENCES golf_courses(id),
hole_number INT NOT NULL,
par INT NOT NULL,
distance_meters INT,
tee_position GEOMETRY(POINT, 4326),
green_position GEOMETRY(POINT, 4326),
created_at TIMESTAMP DEFAULT NOW(),
UNIQUE(golf_course_id, hole_number)
);

CREATE TABLE routes (
id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
golf_course_id UUID NOT NULL REFERENCES golf_courses(id),
name VARCHAR(100) NOT NULL,
route_type VARCHAR(30) NOT NULL,
path GEOMETRY(LINESTRING, 4326) NOT NULL,
distance_meters FLOAT,
waypoints JSONB,
is_active BOOLEAN DEFAULT true,
created_by UUID REFERENCES manufacturer_users(id),
created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE geofences (
id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
golf_course_id UUID NOT NULL REFERENCES golf_courses(id),
name VARCHAR(100) NOT NULL,
fence_type VARCHAR(30) NOT NULL,
geometry GEOMETRY(POLYGON, 4326) NOT NULL,
speed_limit FLOAT,
is_active BOOLEAN DEFAULT true,
created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================
-- 3. 카트 관리
-- ============================================

CREATE TABLE cart_models (
id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
manufacturer VARCHAR(50) NOT NULL,
model_name VARCHAR(50) NOT NULL,
model_code VARCHAR(30) UNIQUE NOT NULL,
capacity INT DEFAULT 2,
max_speed FLOAT DEFAULT 20.0,
features JSONB,
created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE golf_carts (
id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
serial_number VARCHAR(50) UNIQUE NOT NULL,
cart_model_id UUID REFERENCES cart_models(id),
golf_course_id UUID REFERENCES golf_courses(id),
cart_number VARCHAR(20),
status VARCHAR(20) DEFAULT 'IDLE',
mode VARCHAR(20) DEFAULT 'MANUAL',
firmware_version VARCHAR(20),
created_at TIMESTAMP DEFAULT NOW(),
updated_at TIMESTAMP DEFAULT NOW(),
UNIQUE(golf_course_id, cart_number)
);

-- 카트 등록 이력 (제조사가 카트를 골프장에 할당)
CREATE TABLE cart_registrations (
id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
cart_id UUID NOT NULL REFERENCES golf_carts(id),
golf_course_id UUID NOT NULL REFERENCES golf_courses(id),
registered_by UUID NOT NULL REFERENCES manufacturer_users(id),
registration_type VARCHAR(30) NOT NULL, -- NEW, TRANSFER, RETURN
cart_number VARCHAR(20),
notes TEXT,
registered_at TIMESTAMP DEFAULT NOW()
);

-- ============================================
-- 4. 실시간 데이터
-- ============================================

CREATE TABLE cart_telemetry (
id BIGSERIAL,
cart_id UUID NOT NULL REFERENCES golf_carts(id),
timestamp TIMESTAMP NOT NULL,
position GEOMETRY(POINT, 4326) NOT NULL,
heading FLOAT,
speed FLOAT,
battery_level INT,
sensor_data JSONB,
created_at TIMESTAMP DEFAULT NOW(),
PRIMARY KEY (cart_id, timestamp)
) PARTITION BY RANGE (timestamp);

CREATE TABLE cart_events (
id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
cart_id UUID NOT NULL REFERENCES golf_carts(id),
event_type VARCHAR(50) NOT NULL,
severity VARCHAR(20) NOT NULL,
event_data JSONB NOT NULL,
position GEOMETRY(POINT, 4326),
timestamp TIMESTAMP NOT NULL,
created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================
-- 5. 운영 관리
-- ============================================

CREATE TABLE cart_assignments (
id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
golf_course_id UUID NOT NULL REFERENCES golf_courses(id),
cart_id UUID NOT NULL REFERENCES golf_carts(id),
reservation_code VARCHAR(20) UNIQUE,
player_name VARCHAR(100),
player_count INT DEFAULT 1,
start_hole INT,
scheduled_start TIMESTAMP NOT NULL,
scheduled_end TIMESTAMP,
status VARCHAR(20) DEFAULT 'RESERVED',
created_by UUID REFERENCES golf_course_users(id),
created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE maintenance_logs (
id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
cart_id UUID NOT NULL REFERENCES golf_carts(id),
maintenance_type VARCHAR(50) NOT NULL,
description TEXT,
performed_at TIMESTAMP NOT NULL,
performed_by VARCHAR(100),
created_by UUID REFERENCES golf_course_users(id),
created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================
-- 인덱스
-- ============================================

CREATE INDEX idx_golf_course_users_course ON golf_course_users(golf_course_id);
CREATE INDEX idx_golf_carts_course ON golf_carts(golf_course_id);
CREATE INDEX idx_cart_telemetry_cart_time ON cart_telemetry(cart_id, timestamp DESC);
CREATE INDEX idx_cart_events_cart_time ON cart_events(cart_id, timestamp DESC);
CREATE INDEX idx_cart_assignments_course_date ON cart_assignments(golf_course_id, scheduled_start);

-- 외래키 제약조건 추가
ALTER TABLE golf_course_users
ADD CONSTRAINT fk_golf_course_users_course
FOREIGN KEY (golf_course_id) REFERENCES golf_courses(id);
