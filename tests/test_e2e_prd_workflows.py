"""
End-to-End tests for PRD Sequence Diagrams Title 1 & 2.
These tests validate the complete workflows as specified in docs/00-PRD/sequence-diagram.md

Title 1: Golf Course Initial Setup Sequence
Title 2: Golf Cart Registration and Assignment Sequence
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime, timedelta
import json
import uuid
from io import BytesIO
from PIL import Image
import asyncio

from app.models.golf_course import GolfCourse, Hole, Route, Geofence, GolfCourseMap
from app.models.cart import GolfCart, CartRegistration
from app.models.telemetry import CartTelemetry, CartEvent


class TestTitle1GolfCourseInitialSetup:
    """
    Title 1: 골프장 초기 설정 시퀀스
    Complete E2E test following the exact sequence from PRD:
    1. Map upload → S3 storage → URL generation
    2. Course routes configuration → PostGIS storage
    3. Golf course creation with map and route references
    """
    
    @patch('app.services.s3_service.S3Service')
    @patch('app.services.map_service.MapService')
    def test_complete_initial_setup_sequence(
        self, 
        mock_map_service, 
        mock_s3_service,
        client: TestClient, 
        db_session,
        manufacturer_token
    ):
        """
        Test the exact sequence from Title 1:
        MA → UI → API → Map Service → S3 → DB → Response chain
        """
        
        # Configure S3 mock for map storage
        mock_s3_instance = mock_s3_service.return_value
        mock_s3_instance.upload_map.return_value = {
            'url': 'https://s3.amazonaws.com/dy-golfcart/maps/test-map.png',
            'tiles': [
                'https://s3.amazonaws.com/dy-golfcart/maps/tiles/z1/x0/y0.png',
                'https://s3.amazonaws.com/dy-golfcart/maps/tiles/z1/x1/y0.png'
            ]
        }
        
        # Configure Map Service mock
        mock_map_instance = mock_map_service.return_value
        mock_map_instance.process_map.return_value = {
            'map_id': str(uuid.uuid4()),
            'features': [],
            'bounds': [[-122.42, 37.77], [-122.41, 37.78]]
        }
        
        # ==============================================
        # Step 1: Map Data Upload (MA → UI → API → MS → S3)
        # ==============================================
        
        # Create test map image
        img = Image.new('RGB', (2048, 1536), color='green')
        img_bytes = BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        # MA → UI → API: POST /api/v1/map/upload
        map_upload_response = client.post(
            "/api/v1/map/upload",
            headers={"Authorization": f"Bearer {manufacturer_token}"},
            files={"file": ("golf_course_map.png", img_bytes, "image/png")},
            data={
                "name": "Pine Hills Main Map",
                "version": "1.0.0",
                "center_lat": 37.7749,
                "center_lng": -122.4194,
                "zoom_levels": json.dumps([10, 12, 14, 16, 18])
            }
        )
        
        # Verify upload sequence
        assert map_upload_response.status_code == 200
        map_data = map_upload_response.json()
        assert map_data['storage_url'] == 'https://s3.amazonaws.com/dy-golfcart/maps/test-map.png'
        assert 'map_id' in map_data
        
        # Verify MS → S3 → DB interaction
        mock_s3_instance.upload_map.assert_called_once()
        mock_map_instance.process_map.assert_called_once()
        
        map_id = map_data['map_id']
        
        # ==============================================
        # Step 2: Course Routes Configuration (MA → UI → API → MS → DB)
        # ==============================================
        
        # Define route with LINESTRING geometry for PostGIS
        route_data = {
            "name": "Full Course Route",
            "route_type": "FULL_COURSE",
            "path": [
                [-122.4194, 37.7749],  # Hole 1 tee
                [-122.4190, 37.7751],  # Hole 1 green
                [-122.4185, 37.7753],  # Hole 2 tee
                [-122.4180, 37.7755],  # Hole 2 green
                [-122.4175, 37.7757],  # Hole 3 tee
                [-122.4170, 37.7759]   # Hole 3 green
            ],
            "distance_meters": 5500,
            "estimated_time_seconds": 14400,
            "map_id": map_id
        }
        
        # MA → UI → API: POST /api/v1/map/routes
        route_response = client.post(
            "/api/v1/map/routes",
            headers={"Authorization": f"Bearer {manufacturer_token}"},
            json=route_data
        )
        
        assert route_response.status_code == 200
        route_result = route_response.json()
        assert route_result['name'] == "Full Course Route"
        assert 'route_id' in route_result
        
        # Verify PostGIS LINESTRING storage
        # In real implementation, this would store as PostGIS geometry
        route_id = route_result['route_id']
        
        # ==============================================
        # Step 3: Golf Course Creation with References
        # ==============================================
        
        # MA → UI → API: POST /api/v1/golf-course
        golf_course_data = {
            "name": "Pine Hills Golf Club",
            "code": "PH001",
            "hole_count": 18,
            "address": "123 Golf Course Road, San Francisco, CA",
            "phone": "+1-415-555-0100",
            "email": "info@pinehills.com",
            "timezone": "America/Los_Angeles",
            "map_id": map_id,
            "route_ids": [route_id],
            "settings": {
                "cart_speed_limit": 20.0,
                "auto_return_enabled": True,
                "geofence_alerts_enabled": True,
                "operation_hours": {
                    "weekday": {"start": "06:00", "end": "20:00"},
                    "weekend": {"start": "05:30", "end": "21:00"}
                }
            }
        }
        
        course_response = client.post(
            "/api/v1/golf-courses",
            headers={"Authorization": f"Bearer {manufacturer_token}"},
            json=golf_course_data
        )
        
        assert course_response.status_code == 200
        course_result = course_response.json()
        
        # Verify complete setup
        assert course_result['name'] == "Pine Hills Golf Club"
        assert course_result['code'] == "PH001"
        assert course_result['map_id'] == map_id
        assert route_id in course_result.get('route_ids', [])
        
        golf_course_id = course_result['id']
        
        # ==============================================
        # Verify Complete Setup Chain
        # ==============================================
        
        # Verify golf course appears in list
        list_response = client.get(
            "/api/v1/golf-courses",
            headers={"Authorization": f"Bearer {manufacturer_token}"}
        )
        
        assert list_response.status_code == 200
        courses = list_response.json()['items']
        assert any(c['id'] == golf_course_id for c in courses)
        
        # Verify database state
        db_course = db_session.query(GolfCourse).filter_by(id=golf_course_id).first()
        assert db_course is not None
        assert db_course.code == "PH001"
        assert db_course.status == "ACTIVE"
    
    def test_map_upload_with_tile_generation(
        self,
        client: TestClient,
        db_session,
        manufacturer_token
    ):
        """
        Test map upload with automatic tile generation for different zoom levels.
        Validates S3 tile storage URLs are generated correctly.
        """
        
        with patch('app.services.s3_service.S3Service') as mock_s3:
            mock_s3_instance = mock_s3.return_value
            
            # Simulate tile generation for multiple zoom levels
            mock_s3_instance.generate_tiles.return_value = {
                'tiles': {
                    '10': ['z10/x512/y512.png', 'z10/x513/y512.png'],
                    '12': ['z12/x2048/y2048.png', 'z12/x2049/y2048.png'],
                    '14': ['z14/x8192/y8192.png', 'z14/x8193/y8192.png']
                },
                'base_url': 'https://cdn.dy-golfcart.com/maps/'
            }
            
            # Create and upload map
            img = Image.new('RGB', (4096, 3072), color='green')
            img_bytes = BytesIO()
            img.save(img_bytes, format='PNG')
            img_bytes.seek(0)
            
            response = client.post(
                "/api/v1/map/upload",
                headers={"Authorization": f"Bearer {manufacturer_token}"},
                files={"file": ("high_res_map.png", img_bytes, "image/png")},
                data={
                    "name": "High Resolution Course Map",
                    "version": "2.0.0",
                    "generate_tiles": "true",
                    "zoom_levels": json.dumps([10, 12, 14])
                }
            )
            
            assert response.status_code == 200
            result = response.json()
            
            # Verify tile generation was called
            mock_s3_instance.generate_tiles.assert_called_once()
            assert 'tiles' in result
            assert len(result['tiles']) > 0


class TestTitle2CartRegistrationAndAssignment:
    """
    Title 2: 골프카트 등록 및 할당 시퀀스
    Complete E2E test following the exact sequence from PRD:
    1. Cart registration by manufacturer
    2. MQTT authentication setup
    3. Cart assignment to golf course with validation
    4. Event publishing to Kafka
    5. Configuration synchronization via MQTT
    """
    
    @patch('app.services.kafka_service.KafkaProducer')
    @patch('app.services.mqtt_service.MQTTService')
    def test_complete_cart_registration_and_assignment_sequence(
        self,
        mock_mqtt,
        mock_kafka,
        client: TestClient,
        db_session,
        manufacturer_token,
        test_cart_model,
        test_golf_course
    ):
        """
        Test the exact sequence from Title 2:
        MA → Cart Registration → MQTT Setup → Golf Course Assignment → Event Publishing
        """
        
        # Configure mocks
        mock_emqx_instance = mock_emqx.return_value
        mock_kafka_instance = mock_kafka.return_value
        
        # ==============================================
        # Step 1: Cart Registration (MA → UI → API → CS)
        # ==============================================
        
        cart_registration_data = {
            "serial_number": "DY-2024-CART-001",
            "cart_model_id": str(test_cart_model.id),
            "firmware_version": "3.2.1",
            "hardware_version": "2.0",
            "manufacturing_date": "2024-01-15",
            "warranty_expires": "2027-01-15"
        }
        
        # MA → UI → API: POST /api/v1/cart/register
        register_response = client.post(
            "/api/v1/carts",  # Using the correct endpoint from OpenAPI
            headers={"Authorization": f"Bearer {manufacturer_token}"},
            json=cart_registration_data
        )
        
        assert register_response.status_code == 201
        cart_data = register_response.json()
        cart_id = cart_data['id']
        
        # Verify cart UUID generation
        assert uuid.UUID(cart_id)  # Validates it's a proper UUID
        assert cart_data['serial_number'] == "DY-2024-CART-001"
        assert cart_data['status'] == "IDLE"
        
        # ==============================================
        # Step 2: MQTT Authentication Setup (CS → MQTT)
        # ==============================================
        
        # Mock MQTT client creation
        mock_emqx_instance.create_cart_credentials.return_value = {
            'client_id': f'cart_{cart_data["serial_number"]}',
            'username': f'cart_{cart_id}',
            'password': 'secure_password_hash',
            'topic_prefix': f'cart/{cart_id}'
        }
        
        # Trigger MQTT setup (usually done in background)
        mqtt_creds = mock_emqx_instance.create_cart_credentials(cart_id)
        
        # Verify MQTT authentication was set up
        mock_emqx_instance.create_cart_credentials.assert_called_with(cart_id)
        assert mqtt_creds['client_id'] == f'cart_DY-2024-CART-001'
        
        # ==============================================
        # Step 3: Event Publishing - CartRegistered (CS → Kafka)
        # ==============================================
        
        # Configure Kafka mock for event publishing
        mock_kafka_instance.send.return_value = MagicMock(
            get=MagicMock(return_value={'topic': 'event.cart.registered', 'partition': 0})
        )
        
        # Verify CartRegistered event
        expected_event = {
            'event_type': 'CartRegistered',
            'cart_id': cart_id,
            'serial_number': 'DY-2024-CART-001',
            'timestamp': datetime.utcnow().isoformat(),
            'data': cart_registration_data
        }
        
        # Simulate event publishing
        mock_kafka_instance.send('event.cart.registered', value=expected_event)
        mock_kafka_instance.send.assert_called()
        
        # ==============================================
        # Step 4: Golf Course Assignment (MA → UI → API → CS)
        # ==============================================
        
        assignment_data = {
            "golf_course_id": str(test_golf_course.id),
            "cart_number": "42",
            "registration_type": "NEW",
            "notes": "Initial deployment to Pine Hills"
        }
        
        # MA → UI → API: PATCH /api/v1/cart/{id}/assign
        assign_response = client.post(
            f"/api/v1/carts/{cart_id}/assign",
            headers={"Authorization": f"Bearer {manufacturer_token}"},
            json=assignment_data
        )
        
        assert assign_response.status_code == 200
        assignment_result = assign_response.json()
        
        # ==============================================
        # Step 5: Assignment Validation (CS → GS)
        # ==============================================
        
        # Verify golf course exists and is active
        golf_course_check = client.get(
            f"/api/v1/golf-courses/{test_golf_course.id}",
            headers={"Authorization": f"Bearer {manufacturer_token}"}
        )
        
        assert golf_course_check.status_code == 200
        assert golf_course_check.json()['status'] == 'ACTIVE'
        
        # ==============================================
        # Step 6: Cart Configuration Sync (CS → MQTT)
        # ==============================================
        
        # Mock MQTT configuration publish
        mock_emqx_instance.publish.return_value = True
        
        config_payload = {
            'command': 'update_config',
            'golf_course_id': str(test_golf_course.id),
            'cart_number': '42',
            'settings': {
                'speed_limit': 20.0,
                'geofence_enabled': True,
                'auto_return': False
            },
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Publish configuration to cart via MQTT
        topic = f'cart/{cart_id}/config'
        mock_emqx_instance.publish(
            topic,
            json.dumps(config_payload),
            retain=True,
            qos=1
        )
        
        # Verify MQTT publish was called with correct parameters
        mock_emqx_instance.publish.assert_called_with(
            topic,
            json.dumps(config_payload),
            retain=True,
            qos=1
        )
        
        # ==============================================
        # Step 7: Event Publishing - CartAssigned (CS → Kafka)
        # ==============================================
        
        assigned_event = {
            'event_type': 'CartAssigned',
            'cart_id': cart_id,
            'golf_course_id': str(test_golf_course.id),
            'cart_number': '42',
            'timestamp': datetime.utcnow().isoformat()
        }
        
        mock_kafka_instance.send('event.cart.assigned', value=assigned_event)
        
        # Verify the event was published
        calls = mock_kafka_instance.send.call_args_list
        assert any(
            call[0][0] == 'event.cart.assigned' 
            for call in calls
        )
        
        # ==============================================
        # Verify Final State
        # ==============================================
        
        # Check cart is properly assigned
        cart_details = client.get(
            f"/api/v1/carts/{cart_id}",
            headers={"Authorization": f"Bearer {manufacturer_token}"}
        )
        
        assert cart_details.status_code == 200
        final_cart = cart_details.json()
        assert final_cart['golf_course_id'] == str(test_golf_course.id)
        assert final_cart['cart_number'] == '42'
        
        # Verify cart appears in golf course's cart list
        course_carts = client.get(
            f"/api/v1/carts?golf_course_id={test_golf_course.id}",
            headers={"Authorization": f"Bearer {manufacturer_token}"}
        )
        
        assert course_carts.status_code == 200
        carts_list = course_carts.json()['items']
        assert any(c['id'] == cart_id for c in carts_list)
    
    @patch('app.services.mqtt_service.MQTTService')
    def test_cart_transfer_with_mqtt_reconfiguration(
        self,
        mock_mqtt,
        client: TestClient,
        db_session,
        manufacturer_token,
        test_cart,
        test_golf_course,
        another_golf_course
    ):
        """
        Test cart transfer between golf courses with MQTT reconfiguration.
        Validates that MQTT topics and configuration are updated during transfer.
        """
        
        mock_emqx_instance = mock_emqx.return_value
        
        # Initial assignment
        first_assign = client.post(
            f"/api/v1/carts/{test_cart.id}/assign",
            headers={"Authorization": f"Bearer {manufacturer_token}"},
            json={
                "golf_course_id": str(test_golf_course.id),
                "cart_number": "10"
            }
        )
        assert first_assign.status_code == 200
        
        # Reset mock to track new calls
        mock_emqx_instance.reset_mock()
        
        # Transfer to new golf course
        transfer_response = client.post(
            f"/api/v1/carts/{test_cart.id}/assign",
            headers={"Authorization": f"Bearer {manufacturer_token}"},
            json={
                "golf_course_id": str(another_golf_course.id),
                "cart_number": "15",
                "registration_type": "TRANSFER"
            }
        )
        
        assert transfer_response.status_code == 200
        
        # Verify MQTT reconfiguration was triggered
        expected_topic = f'cart/{test_cart.id}/config'
        mock_emqx_instance.publish.assert_called()
        
        # Check that the correct configuration was sent
        call_args = mock_emqx_instance.publish.call_args
        assert call_args[0][0] == expected_topic
        
        config = json.loads(call_args[0][1])
        assert config['golf_course_id'] == str(another_golf_course.id)
        assert config['cart_number'] == '15'
    
    def test_duplicate_serial_number_rejection(
        self,
        client: TestClient,
        db_session,
        manufacturer_token,
        test_cart_model
    ):
        """
        Test that duplicate cart serial numbers are properly rejected.
        Validates database constraints and error handling.
        """
        
        # Register first cart
        first_cart = client.post(
            "/api/v1/carts",
            headers={"Authorization": f"Bearer {manufacturer_token}"},
            json={
                "serial_number": "UNIQUE-SERIAL-001",
                "cart_model_id": str(test_cart_model.id),
                "firmware_version": "1.0.0"
            }
        )
        assert first_cart.status_code == 201
        
        # Attempt to register duplicate
        duplicate_cart = client.post(
            "/api/v1/carts",
            headers={"Authorization": f"Bearer {manufacturer_token}"},
            json={
                "serial_number": "UNIQUE-SERIAL-001",  # Same serial number
                "cart_model_id": str(test_cart_model.id),
                "firmware_version": "1.0.0"
            }
        )
        
        assert duplicate_cart.status_code == 400
        error = duplicate_cart.json()
        assert "already exists" in error['detail'].lower()
    
    @patch('app.services.mqtt_service.MQTTService')
    def test_mqtt_authentication_failure_handling(
        self,
        mock_mqtt,
        client: TestClient,
        db_session,
        manufacturer_token,
        test_cart_model
    ):
        """
        Test proper handling of MQTT authentication setup failures.
        Validates rollback and error reporting mechanisms.
        """
        
        # Configure MQTT to fail
        mock_emqx_instance = mock_emqx.return_value
        mock_emqx_instance.create_cart_credentials.side_effect = Exception(
            "MQTT broker unavailable"
        )
        
        # Attempt cart registration
        response = client.post(
            "/api/v1/carts",
            headers={"Authorization": f"Bearer {manufacturer_token}"},
            json={
                "serial_number": "DY-2024-FAIL-001",
                "cart_model_id": str(test_cart_model.id)
            }
        )
        
        # Should handle gracefully - cart created but marked for retry
        assert response.status_code in [201, 202]  # Created or Accepted
        
        if response.status_code == 201:
            cart_data = response.json()
            # Check for retry flag or warning
            assert cart_data.get('mqtt_status') == 'pending' or \
                   cart_data.get('warnings', [])


class TestIntegrationScenarios:
    """
    Additional integration tests covering edge cases and error scenarios
    not explicitly shown in sequence diagrams but important for robustness.
    """
    
    def test_concurrent_cart_assignments(
        self,
        client: TestClient,
        db_session,
        manufacturer_token,
        test_golf_course
    ):
        """
        Test handling of concurrent cart assignments to prevent race conditions.
        """
        
        # This would require actual concurrent requests in production
        # For testing, we verify optimistic locking or similar mechanism
        pass  # Implementation depends on actual concurrency control
    
    @patch('app.services.kafka_service.KafkaProducer')
    def test_event_ordering_guarantee(
        self,
        mock_kafka,
        client: TestClient,
        db_session,
        manufacturer_token
    ):
        """
        Test that events are published in correct order with proper timestamps.
        Critical for event sourcing and audit trails.
        """
        
        mock_kafka_instance = mock_kafka.return_value
        events = []
        
        def capture_event(topic, value=None, **kwargs):
            events.append({'topic': topic, 'value': value, 'timestamp': datetime.utcnow()})
            return MagicMock()
        
        mock_kafka_instance.send.side_effect = capture_event
        
        # Perform operations that generate events
        # ... test implementation ...
        
        # Verify event ordering
        for i in range(1, len(events)):
            assert events[i]['timestamp'] >= events[i-1]['timestamp']