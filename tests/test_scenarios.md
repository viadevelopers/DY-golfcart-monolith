# DY-GOLFCART Comprehensive Test Scenarios

Based on PRD requirements including sequence diagrams, ERD, and OpenAPI specifications.

## 🎯 Test Coverage Goals

- **Authentication & Authorization**: 100% coverage
- **CRUD Operations**: 100% coverage  
- **Geospatial Operations**: 90% coverage
- **Real-time (MQTT)**: 80% coverage
- **Edge Cases**: 85% coverage

---

## 1️⃣ Authentication & Authorization Tests

### 1.1 Manufacturer Login Flow
```gherkin
Feature: Manufacturer Authentication
  As a manufacturer admin
  I want to login to the system
  So that I can manage golf courses and carts

  Scenario: Successful manufacturer login
    Given I am a registered manufacturer user
    When I POST to /api/v1/auth/manufacturer/login with valid credentials
    Then I should receive JWT tokens
    And the response should include user information
    And my last_login should be updated

  Scenario: Failed manufacturer login - wrong password
    Given I am a registered manufacturer user
    When I POST to /api/v1/auth/manufacturer/login with wrong password
    Then I should receive 401 Unauthorized
    And the response should contain "Incorrect email or password"

  Scenario: Manufacturer accessing golf course endpoints
    Given I am logged in as manufacturer
    When I GET /api/v1/golf-courses
    Then I should see all golf courses in the system
    And I should be able to create new golf courses
```

### 1.2 Golf Course User Login Flow
```gherkin
Feature: Golf Course User Authentication
  As a golf course operator
  I want to login to the system
  So that I can manage my carts and operations

  Scenario: Successful golf course user login
    Given I am a registered golf course user
    When I POST to /api/v1/auth/golf-course/login with valid credentials
    Then I should receive JWT tokens with golf_course_id
    And I should only see data for my golf course

  Scenario: Golf course user accessing other course data
    Given I am logged in as golf course user for "Course A"
    When I GET /api/v1/golf-courses/{course_b_id}
    Then I should receive 403 Forbidden
    And the response should contain "Access denied"
```

### 1.3 Token Refresh Flow
```gherkin
Feature: Token Refresh
  Scenario: Successful token refresh
    Given I have a valid refresh token
    When I POST to /api/v1/auth/refresh
    Then I should receive new access and refresh tokens
    And the old access token should still work until expiry
```

---

## 2️⃣ Golf Course Setup Tests (Sequence Diagram 1)

### 2.1 Complete Golf Course Setup Flow
```gherkin
Feature: Golf Course Initial Setup
  As a manufacturer admin
  I want to setup a new golf course
  So that it's ready for cart operations

  Background:
    Given I am logged in as manufacturer admin
    And I have map files ready for upload

  Scenario: Complete golf course setup workflow
    # Step 1: Create golf course
    When I POST to /api/v1/golf-courses with:
      | name       | code  | hole_count | timezone     |
      | Pine Hills | PH001 | 18         | America/New_York |
    Then the golf course should be created with status "ACTIVE"
    
    # Step 2: Upload map
    When I POST to /api/v1/golf-courses/{id}/maps with multipart data:
      | name         | version | file            |
      | Main Course  | 1.0     | pinehills.png   |
    Then the map should be uploaded and stored
    And the map URL should be accessible
    
    # Step 3: Define holes
    When I POST to /api/v1/golf-courses/{id}/holes for each hole:
      | hole_number | par | distance_white | tee_position           | green_position         |
      | 1           | 4   | 380           | {"lat":37.1, "lng":-122.1} | {"lat":37.2, "lng":-122.2} |
      | 2           | 3   | 165           | {"lat":37.3, "lng":-122.3} | {"lat":37.4, "lng":-122.4} |
    Then all 18 holes should be created
    
    # Step 4: Create routes
    When I POST to /api/v1/golf-courses/{id}/routes with:
      | name           | route_type    | path                                    | distance_meters |
      | Hole 1 to 2    | HOLE_TO_HOLE  | [[lng1,lat1], [lng2,lat2], [lng3,lat3]] | 450            |
      | Return to Base | RETURN_TO_BASE| [[lng4,lat4], [lng5,lat5]]              | 2000           |
    Then routes should be created with LINESTRING geometry
    
    # Step 5: Setup geofences
    When I POST to /api/v1/golf-courses/{id}/geofences with:
      | name          | fence_type | geometry                        | speed_limit | alert_on_entry |
      | Parking Area  | PARKING    | [[[lng,lat],[lng,lat],...]]     | 5.0        | false          |
      | Water Hazard  | HAZARD     | [[[lng,lat],[lng,lat],...]]     | 0          | true           |
    Then geofences should be created with POLYGON geometry
    And geofence alerts should be configured
```

### 2.2 Validation Tests
```gherkin
Feature: Golf Course Setup Validation

  Scenario: Duplicate golf course code
    When I try to create a golf course with existing code "PH001"
    Then I should receive 400 Bad Request
    And the error should be "Golf course with code PH001 already exists"

  Scenario: Invalid hole number
    When I try to create hole number 19 for an 18-hole course
    Then I should receive 400 Bad Request

  Scenario: Invalid geofence polygon
    When I POST geofence with non-closed polygon
    Then the system should auto-close the polygon
    And save it correctly as POLYGON geometry
```

---

## 3️⃣ Cart Registration & Assignment Tests (Sequence Diagram 2)

### 3.1 Cart Lifecycle Management
```gherkin
Feature: Cart Registration and Assignment
  As a manufacturer admin
  I want to register and assign carts to golf courses
  So that courses can operate their cart fleet

  Background:
    Given I am logged in as manufacturer admin
    And cart models exist in the system
    And golf courses exist in the system

  Scenario: Complete cart registration and assignment flow
    # Step 1: Register new cart
    When I POST to /api/v1/carts/register with:
      | serial_number | cart_model_id | firmware_version |
      | DY-2024-001   | {model_uuid}  | 2.1.0           |
    Then the cart should be registered with status "IDLE"
    And mqtt_client_id should be "cart_DY-2024-001"
    
    # Step 2: Assign cart to golf course
    When I POST to /api/v1/carts/{cart_id}/assign with:
      | golf_course_id | registration_type | cart_number | notes                |
      | {course_uuid}  | NEW              | 42          | First cart delivery  |
    Then a registration record should be created
    And the cart.golf_course_id should be updated
    And any previous registration should be ended
    
    # Step 3: Verify MQTT configuration (simulated)
    Then the MQTT topic cart/DY-2024-001/config should be published
    And the cart should appear in golf course's cart list

  Scenario: Transfer cart between golf courses
    Given cart "DY-2024-001" is assigned to "Course A"
    When I POST to /api/v1/carts/{cart_id}/assign with:
      | golf_course_id | registration_type | cart_number |
      | {course_b_id}  | TRANSFER         | 15          |
    Then the previous registration should have end_date set
    And a new registration should be created for "Course B"
    And the cart should no longer appear in "Course A" cart list
```

### 3.2 Cart Status Management
```gherkin
Feature: Cart Status Updates

  Scenario: Update cart status
    Given I am a golf course user
    And cart "42" belongs to my golf course
    When I PATCH /api/v1/carts/{cart_id} with:
      | status  | mode       |
      | RUNNING | AUTONOMOUS |
    Then the cart status should be updated
    And updated_at timestamp should be refreshed

  Scenario: Cart online/offline detection
    Given a cart with last_ping 30 seconds ago
    When I GET /api/v1/carts/{cart_id}
    Then is_online should be true
    
    Given a cart with last_ping 3 minutes ago
    When I GET /api/v1/carts/{cart_id}
    Then is_online should be false
```

---

## 4️⃣ Map/Course Data Synchronization Tests (Sequence Diagram 3)

### 4.1 Cart Boot and Sync Process
```gherkin
Feature: Cart Data Synchronization
  As a golf cart
  I need to sync map and route data on boot
  So that I can navigate the course

  Background:
    Given cart "DY-2024-001" is assigned to "Pine Hills"
    And "Pine Hills" has maps, routes, and geofences configured
    And MQTT broker is running at emqx.dev.viasoft.ai

  Scenario: Cart boot sequence with data sync
    # Step 1: Cart connects to MQTT
    When cart publishes to "dy/golfcart/cart/DY-2024-001/status":
      """
      {
        "status": "booting",
        "golf_course_id": null,
        "timestamp": 1693201540
      }
      """
    
    # Step 2: Backend identifies cart and prepares data
    Then backend should query cart's golf_course_id
    And backend should fetch map data for the course
    And backend should fetch all active routes
    And backend should fetch all active geofences
    
    # Step 3: Backend sends configuration
    When backend publishes to "dy/golfcart/cart/DY-2024-001/config":
      """
      {
        "command": "update_map",
        "map_url": "/uploads/maps/{course_id}/main.png",
        "routes": [...],
        "geofences": [...],
        "speed_limit": 20.0,
        "timestamp": 1693201542
      }
      """
    
    # Step 4: Cart acknowledges
    When cart publishes to "dy/golfcart/cart/DY-2024-001/ack":
      """
      {
        "status": "map_loaded",
        "timestamp": 1693201545
      }
      """
    Then cart status should be updated to "IDLE"
    And last_ping should be updated
```

### 4.2 Real-time Telemetry Flow
```gherkin
Feature: Real-time Telemetry

  Scenario: Cart sending telemetry data
    When cart publishes to "dy/golfcart/cart/DY-2024-001/telemetry":
      """
      {
        "position": {"lat": 37.1234, "lng": -122.5678},
        "heading": 45.0,
        "speed": 15.5,
        "battery_level": 85,
        "timestamp": 1693201600
      }
      """
    Then telemetry should be stored in cart_telemetry table
    And position should be stored as PostGIS POINT geometry
    And cart.last_ping should be updated

  Scenario: Geofence violation detection
    Given cart is inside a SLOW_ZONE geofence with speed_limit 10
    When cart telemetry shows speed: 15.5
    Then a SPEED_VIOLATION event should be created
    And event severity should be "WARNING"
    And backend should publish speed limit command to cart
```

---

## 5️⃣ Dashboard Monitoring Tests (Sequence Diagram 4)

### 5.1 Manufacturer Dashboard
```gherkin
Feature: Manufacturer Master Dashboard
  As a manufacturer admin
  I want to monitor all golf courses and carts
  So that I can ensure system-wide operations

  Scenario: Load master dashboard overview
    Given I am logged in as manufacturer
    When I GET /api/v1/master/overview
    Then I should receive:
      | Data Point           | Description                    |
      | total_golf_courses   | Count of all golf courses      |
      | active_golf_courses  | Courses with status ACTIVE     |
      | total_carts          | Count of all registered carts  |
      | online_carts         | Carts with recent ping         |
      | carts_in_operation   | Carts with status RUNNING      |
      | maintenance_due      | Carts needing maintenance      |
    And response time should be < 500ms

  Scenario: Real-time updates via WebSocket
    Given I have WebSocket connection to /ws
    When a cart status changes from IDLE to RUNNING
    Then I should receive WebSocket message:
      """
      {
        "event": "cart_status_change",
        "cart_id": "...",
        "old_status": "IDLE",
        "new_status": "RUNNING"
      }
      """
```

### 5.2 Golf Course Dashboard
```gherkin
Feature: Golf Course Operator Dashboard

  Scenario: Golf course specific dashboard
    Given I am logged in as golf course user
    When I GET /api/v1/dashboard
    Then I should only see data for my golf course
    And I should see:
      | today_reservations  | Cart assignments for today     |
      | active_carts        | Currently running carts         |
      | available_carts     | Idle carts ready for use        |
      | charging_carts      | Carts currently charging        |
```

---

## 6️⃣ Edge Cases & Error Scenarios

### 6.1 Network & Connectivity
```gherkin
Feature: Network Resilience

  Scenario: MQTT connection loss
    Given cart is sending telemetry
    When MQTT connection is lost for 5 minutes
    Then cart status should change to OFFLINE
    And a CONNECTION_LOST event should be created
    And dashboard should show cart as offline

  Scenario: Telemetry data batching
    Given cart has intermittent connectivity
    When cart reconnects after 10 minutes
    Then batched telemetry data should be processed
    And data should maintain chronological order
```

### 6.2 Data Validation
```gherkin
Feature: Data Integrity

  Scenario: Invalid GPS coordinates
    When telemetry contains position outside valid range:
      | lat  | lng   |
      | 200  | -500  |
    Then data should be rejected
    And error event should be logged

  Scenario: Duplicate cart registration
    When attempting to register cart with existing serial number
    Then operation should fail with 400 Bad Request
```

### 6.3 Performance & Load
```gherkin
Feature: System Performance

  Scenario: High-frequency telemetry
    Given 100 carts sending telemetry every second
    When system processes for 5 minutes
    Then no telemetry data should be lost
    And average processing time should be < 100ms
    And database partitioning should handle the load

  Scenario: Concurrent user access
    Given 50 users accessing dashboards simultaneously
    When all users refresh data
    Then response time should remain < 1 second
    And Redis cache should serve repeated queries
```

---

## 7️⃣ Integration Test Scenarios

### 7.1 Complete Workflow Test
```python
def test_complete_golf_course_setup_workflow():
    """
    Test the entire golf course setup process from creation to cart operation.
    """
    # 1. Login as manufacturer
    auth_response = client.post("/api/v1/auth/manufacturer/login", ...)
    token = auth_response.json()["access_token"]
    
    # 2. Create golf course
    course = client.post("/api/v1/golf-courses", ..., headers={"Authorization": f"Bearer {token}"})
    course_id = course.json()["id"]
    
    # 3. Upload map
    map_response = client.post(f"/api/v1/golf-courses/{course_id}/maps", files={"file": ...})
    
    # 4. Create holes (1-18)
    for hole_num in range(1, 19):
        client.post(f"/api/v1/golf-courses/{course_id}/holes", ...)
    
    # 5. Create routes
    client.post(f"/api/v1/golf-courses/{course_id}/routes", ...)
    
    # 6. Create geofences
    client.post(f"/api/v1/golf-courses/{course_id}/geofences", ...)
    
    # 7. Register cart
    cart = client.post("/api/v1/carts/register", ...)
    cart_id = cart.json()["id"]
    
    # 8. Assign cart to course
    client.post(f"/api/v1/carts/{cart_id}/assign", json={"golf_course_id": course_id, ...})
    
    # 9. Simulate MQTT telemetry
    mqtt_client.publish(f"dy/golfcart/cart/{cart_id}/telemetry", ...)
    
    # 10. Verify cart appears in dashboard
    dashboard = client.get(f"/api/v1/golf-courses/{course_id}")
    assert dashboard.json()["active_carts"] == 1
```

### 7.2 Multi-tenant Access Control Test
```python
def test_multi_tenant_access_control():
    """
    Ensure golf course users can only access their own data.
    """
    # Create two golf courses
    course_a = create_golf_course("Course A")
    course_b = create_golf_course("Course B")
    
    # Create users for each course
    user_a = create_golf_course_user(course_a.id)
    user_b = create_golf_course_user(course_b.id)
    
    # Login as user A
    token_a = login_golf_course_user(user_a)
    
    # Try to access course B data
    response = client.get(
        f"/api/v1/golf-courses/{course_b.id}",
        headers={"Authorization": f"Bearer {token_a}"}
    )
    
    assert response.status_code == 403
    assert "Access denied" in response.json()["detail"]
```

---

## 8️⃣ Performance Benchmarks

### Expected Performance Metrics
| Operation | Target | Max Acceptable |
|-----------|--------|----------------|
| API Response (CRUD) | < 200ms | 500ms |
| Telemetry Processing | < 50ms | 100ms |
| Dashboard Load | < 500ms | 1000ms |
| WebSocket Latency | < 100ms | 300ms |
| Map Upload (10MB) | < 5s | 10s |
| Geofence Check | < 10ms | 50ms |
| Batch Telemetry (100 points) | < 500ms | 1000ms |

### Load Testing Targets
- Concurrent Users: 100
- Carts per Course: 100
- Telemetry Rate: 1 Hz per cart
- Total Courses: 10
- Database Size: 1M telemetry records

---

## 9️⃣ Test Data Setup

### Base Test Fixtures
```python
# tests/fixtures/test_data.py

TEST_MANUFACTURER = {
    "email": "admin@dygolfcart.com",
    "password": "Test123!@#",
    "name": "Test Admin"
}

TEST_GOLF_COURSE = {
    "name": "Pine Hills Golf Club",
    "code": "PH001",
    "hole_count": 18,
    "address": "123 Golf Course Rd",
    "timezone": "America/New_York"
}

TEST_CART_MODEL = {
    "manufacturer": "DY Golf Carts",
    "model_name": "DY-2024",
    "model_code": "DY2024",
    "capacity": 2,
    "max_speed": 20.0
}

TEST_CART = {
    "serial_number": "DY-2024-TEST-001",
    "firmware_version": "2.1.0"
}

TEST_GEOFENCE = {
    "name": "Parking Area",
    "fence_type": "PARKING",
    "geometry": [[[
        [-122.1, 37.1],
        [-122.1, 37.2],
        [-122.2, 37.2],
        [-122.2, 37.1],
        [-122.1, 37.1]  # Closed polygon
    ]]],
    "speed_limit": 5.0
}

TEST_TELEMETRY = {
    "position": {"lat": 37.15, "lng": -122.15},
    "heading": 45.0,
    "speed": 15.5,
    "battery_level": 85,
    "timestamp": "2024-01-15T10:30:00Z"
}
```

---

## 🎯 Test Execution Strategy

### Phase 1: Unit Tests (Week 1)
- [ ] Authentication module tests
- [ ] Model validation tests
- [ ] Geospatial operation tests
- [ ] Business logic tests

### Phase 2: Integration Tests (Week 2)
- [ ] API endpoint tests
- [ ] Database integration tests
- [ ] MQTT integration tests
- [ ] Multi-tenant access tests

### Phase 3: E2E Tests (Week 3)
- [ ] Complete workflow tests
- [ ] Dashboard functionality tests
- [ ] Real-time data flow tests
- [ ] Performance benchmarks

### Phase 4: Load & Stress Tests (Week 4)
- [ ] High-frequency telemetry tests
- [ ] Concurrent user tests
- [ ] Database performance tests
- [ ] Network resilience tests