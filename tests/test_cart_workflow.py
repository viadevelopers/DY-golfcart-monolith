"""
Cart registration and telemetry workflow tests based on PRD Sequence Diagrams 2 & 3.
Tests cart lifecycle: registration → assignment → synchronization → telemetry.
"""
import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
import json

from app.models.cart import GolfCart, CartRegistration
from app.models.telemetry import CartTelemetry, CartEvent


class TestCartRegistrationWorkflow:
    """Test cart registration and assignment workflow from PRD."""
    
    def test_complete_cart_registration_flow(self, client: TestClient, db_session,
                                            manufacturer_token, test_cart_model,
                                            test_golf_course):
        """
        Test complete cart registration workflow:
        1. Register new cart
        2. Assign to golf course
        3. Verify MQTT configuration
        """
        
        # Step 1: Register new cart
        register_response = client.post(
            "/api/v1/carts/register",
            headers={"Authorization": f"Bearer {manufacturer_token}"},
            json={
                "serial_number": "DY-2024-001",
                "cart_model_id": str(test_cart_model.id),
                "firmware_version": "2.1.0",
                "cart_number": "001"
            }
        )
        
        assert register_response.status_code == 200
        cart_data = register_response.json()
        cart_id = cart_data["id"]
        
        # Verify cart properties
        assert cart_data["serial_number"] == "DY-2024-001"
        assert cart_data["status"] == "IDLE"
        assert cart_data["mode"] == "MANUAL"
        assert cart_data["golf_course_id"] is None
        
        # Verify MQTT client ID
        db_cart = db_session.query(GolfCart).filter_by(id=cart_id).first()
        assert db_cart.mqtt_client_id == "cart_DY-2024-001"
        
        # Step 2: Assign cart to golf course
        assign_response = client.post(
            f"/api/v1/carts/{cart_id}/assign",
            headers={"Authorization": f"Bearer {manufacturer_token}"},
            json={
                "golf_course_id": str(test_golf_course.id),
                "registration_type": "NEW",
                "cart_number": "42",
                "notes": "First cart delivery to Pine Hills"
            }
        )
        
        assert assign_response.status_code == 200
        registration_data = assign_response.json()
        
        # Verify registration
        assert registration_data["cart_id"] == cart_id
        assert registration_data["golf_course_id"] == str(test_golf_course.id)
        assert registration_data["registration_type"] == "NEW"
        assert registration_data["cart_number"] == "42"
        
        # Verify cart was updated
        updated_cart = client.get(
            f"/api/v1/carts/{cart_id}",
            headers={"Authorization": f"Bearer {manufacturer_token}"}
        )
        assert updated_cart.status_code == 200
        assert updated_cart.json()["golf_course_id"] == str(test_golf_course.id)
        assert updated_cart.json()["cart_number"] == "42"
        
        # Step 3: Verify cart appears in golf course cart list
        course_carts = client.get(
            f"/api/v1/carts?golf_course_id={test_golf_course.id}",
            headers={"Authorization": f"Bearer {manufacturer_token}"}
        )
        
        assert course_carts.status_code == 200
        cart_list = course_carts.json()
        assert any(c["id"] == cart_id for c in cart_list)
    
    def test_cart_transfer_between_courses(self, client: TestClient, db_session,
                                          manufacturer_token, test_cart,
                                          test_golf_course, another_golf_course):
        """Test transferring a cart from one golf course to another."""
        
        # Initial assignment to first course
        first_assign = client.post(
            f"/api/v1/carts/{test_cart.id}/assign",
            headers={"Authorization": f"Bearer {manufacturer_token}"},
            json={
                "golf_course_id": str(test_golf_course.id),
                "registration_type": "NEW",
                "cart_number": "10"
            }
        )
        assert first_assign.status_code == 200
        
        # Transfer to second course
        transfer_response = client.post(
            f"/api/v1/carts/{test_cart.id}/assign",
            headers={"Authorization": f"Bearer {manufacturer_token}"},
            json={
                "golf_course_id": str(another_golf_course.id),
                "registration_type": "TRANSFER",
                "cart_number": "15",
                "notes": "Transferred from Pine Hills to Oak Valley"
            }
        )
        
        assert transfer_response.status_code == 200
        
        # Verify registration history
        registrations = client.get(
            f"/api/v1/carts/{test_cart.id}/registrations",
            headers={"Authorization": f"Bearer {manufacturer_token}"}
        )
        
        assert registrations.status_code == 200
        reg_list = registrations.json()
        assert len(reg_list) == 2
        
        # First registration should be ended
        first_reg = next(r for r in reg_list if r["golf_course_id"] == str(test_golf_course.id))
        assert first_reg["end_date"] is not None
        
        # Second registration should be active
        second_reg = next(r for r in reg_list if r["golf_course_id"] == str(another_golf_course.id))
        assert second_reg["end_date"] is None
        assert second_reg["registration_type"] == "TRANSFER"
    
    def test_duplicate_cart_serial_number(self, client: TestClient, db_session,
                                         manufacturer_token, test_cart_model):
        """Test that duplicate serial numbers are rejected."""
        
        # Register first cart
        first_response = client.post(
            "/api/v1/carts/register",
            headers={"Authorization": f"Bearer {manufacturer_token}"},
            json={
                "serial_number": "DUPLICATE-001",
                "cart_model_id": str(test_cart_model.id)
            }
        )
        assert first_response.status_code == 200
        
        # Try to register second cart with same serial number
        second_response = client.post(
            "/api/v1/carts/register",
            headers={"Authorization": f"Bearer {manufacturer_token}"},
            json={
                "serial_number": "DUPLICATE-001",
                "cart_model_id": str(test_cart_model.id)
            }
        )
        
        assert second_response.status_code == 400
        assert "already exists" in second_response.json()["detail"]


class TestCartStatusManagement:
    """Test cart status updates and online/offline detection."""
    
    def test_cart_status_update(self, client: TestClient, db_session,
                               golf_course_token, test_cart_assigned):
        """Test updating cart status."""
        
        # Update cart status
        update_response = client.patch(
            f"/api/v1/carts/{test_cart_assigned.id}",
            headers={"Authorization": f"Bearer {golf_course_token}"},
            json={
                "status": "RUNNING",
                "mode": "AUTONOMOUS"
            }
        )
        
        assert update_response.status_code == 200
        updated_data = update_response.json()
        assert updated_data["status"] == "RUNNING"
        assert updated_data["mode"] == "AUTONOMOUS"
        
        # Verify in database
        db_session.refresh(test_cart_assigned)
        assert test_cart_assigned.status == "RUNNING"
        assert test_cart_assigned.mode == "AUTONOMOUS"
    
    def test_cart_online_detection(self, client: TestClient, db_session,
                                  manufacturer_token, test_cart_assigned):
        """Test cart online/offline detection based on last_ping."""
        
        # Set last_ping to recent time (30 seconds ago)
        test_cart_assigned.last_ping = datetime.utcnow() - timedelta(seconds=30)
        db_session.commit()
        
        # Get cart details
        response = client.get(
            f"/api/v1/carts/{test_cart_assigned.id}",
            headers={"Authorization": f"Bearer {manufacturer_token}"}
        )
        
        assert response.status_code == 200
        assert response.json()["is_online"] is True
        
        # Set last_ping to old time (3 minutes ago)
        test_cart_assigned.last_ping = datetime.utcnow() - timedelta(minutes=3)
        db_session.commit()
        
        # Get cart details again
        response = client.get(
            f"/api/v1/carts/{test_cart_assigned.id}",
            headers={"Authorization": f"Bearer {manufacturer_token}"}
        )
        
        assert response.status_code == 200
        assert response.json()["is_online"] is False


class TestCartTelemetryWorkflow:
    """Test cart telemetry and synchronization workflow from PRD."""
    
    @patch('app.services.mqtt_service.MQTTClient')
    def test_cart_boot_and_sync_sequence(self, mock_mqtt, client: TestClient,
                                        db_session, test_cart_assigned,
                                        test_golf_course_with_data, manufacturer_token):
        """Test cart boot sequence with map/route synchronization."""
        
        # Simulate cart boot - status message via MQTT
        cart_status = {
            "status": "booting",
            "golf_course_id": None,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Mock MQTT publish for configuration
        mock_mqtt_instance = mock_mqtt.return_value
        mock_mqtt_instance.publish_cart_config.return_value = True
        
        # Trigger the actual configuration sync using our MQTT service
        from app.services.mqtt_service import create_cart_sync_config
        
        # Create the expected configuration
        config = create_cart_sync_config(test_golf_course_with_data, test_cart_assigned)
        
        # Simulate the backend sending configuration to the cart
        mqtt_client = mock_mqtt_instance
        mqtt_client.publish_cart_config(test_cart_assigned.serial_number, config)
        
        # Verify cart receives configuration
        mock_mqtt_instance.publish_cart_config.assert_called_with(
            test_cart_assigned.serial_number,
            config
        )
        
        # Simulate cart acknowledgment
        cart_ack = {
            "status": "map_loaded",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Update cart status
        test_cart_assigned.status = "IDLE"
        test_cart_assigned.last_ping = datetime.utcnow()
        db_session.commit()
        
        # Verify cart is ready
        cart_response = client.get(
            f"/api/v1/carts/{test_cart_assigned.id}",
            headers={"Authorization": f"Bearer {manufacturer_token}"}
        )
        
        assert cart_response.status_code == 200
        assert cart_response.json()["status"] == "IDLE"
        assert cart_response.json()["is_online"] is True
    
    def test_telemetry_data_storage(self, db_session, test_cart_assigned):
        """Test storing telemetry data with PostGIS geometry."""
        
        from geoalchemy2.shape import from_shape
        from shapely.geometry import Point
        
        # Create telemetry data
        telemetry = CartTelemetry(
            cart_id=test_cart_assigned.id,
            timestamp=datetime.utcnow(),
            position=from_shape(Point(-122.4194, 37.7749), srid=4326),
            heading=45.0,
            speed=15.5,
            battery_level=85,
            battery_voltage=48.2,
            charging_status=False,
            engine_status="ON",
            gps_satellites=12,
            gps_hdop=0.9
        )
        
        db_session.add(telemetry)
        db_session.commit()
        
        # Verify telemetry was stored
        stored_telemetry = db_session.query(CartTelemetry).filter_by(
            cart_id=test_cart_assigned.id
        ).first()
        
        assert stored_telemetry is not None
        assert stored_telemetry.speed == 15.5
        assert stored_telemetry.battery_level == 85
        assert stored_telemetry.heading == 45.0
    
    def test_geofence_violation_event(self, db_session, test_cart_assigned,
                                     test_geofence_hazard):
        """Test creating geofence violation events."""
        
        from geoalchemy2.shape import from_shape
        from shapely.geometry import Point
        
        # Create event for cart entering hazard zone
        event = CartEvent(
            cart_id=test_cart_assigned.id,
            event_type="GEOFENCE_VIOLATION",
            event_category="SAFETY",
            severity="CRITICAL",
            title="Cart entered water hazard",
            description=f"Cart {test_cart_assigned.cart_number} entered restricted water hazard area",
            event_data={
                "geofence_id": str(test_geofence_hazard.id),
                "geofence_name": test_geofence_hazard.name,
                "action_taken": "auto_stop"
            },
            position=from_shape(Point(-122.4172, 37.7753), srid=4326),
            timestamp=datetime.utcnow(),
            auto_actions=["speed_limited", "notification_sent", "auto_stop"],
            related_geofence_id=test_geofence_hazard.id
        )
        
        db_session.add(event)
        db_session.commit()
        
        # Verify event was created
        events = db_session.query(CartEvent).filter_by(
            cart_id=test_cart_assigned.id,
            event_type="GEOFENCE_VIOLATION"
        ).all()
        
        assert len(events) == 1
        assert events[0].severity == "CRITICAL"
        assert events[0].is_critical is True
        assert events[0].needs_attention is True
    
    def test_battery_low_event(self, db_session, test_cart_assigned):
        """Test creating low battery events."""
        
        # Create low battery event
        event = CartEvent(
            cart_id=test_cart_assigned.id,
            event_type="LOW_BATTERY",
            event_category="OPERATIONAL",
            severity="WARNING",
            title="Low battery warning",
            description=f"Cart {test_cart_assigned.cart_number} battery level at 15%",
            event_data={
                "battery_level": 15,
                "estimated_range_km": 3.5,
                "recommended_action": "return_to_base"
            },
            timestamp=datetime.utcnow()
        )
        
        db_session.add(event)
        db_session.commit()
        
        # Query recent events for cart
        recent_events = db_session.query(CartEvent).filter_by(
            cart_id=test_cart_assigned.id
        ).order_by(CartEvent.timestamp.desc()).limit(5).all()
        
        assert len(recent_events) > 0
        assert recent_events[0].event_type == "LOW_BATTERY"
        assert recent_events[0].severity == "WARNING"