#!/usr/bin/env python3
"""
Test script to verify map persistence functionality.
Tests the complete flow from upload to database storage.
"""
import sys
import os
from pathlib import Path
from uuid import uuid4
import json

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.database import init_db, get_db_context
from app.services.map_service import map_service
from app.models.map import Map


def test_map_persistence():
    """Test map creation and persistence to database."""
    print("🧪 Testing Map Persistence...\n")
    
    # Initialize database first
    print("1️⃣ Initializing database...")
    try:
        init_db()
        print("   ✅ Database initialized\n")
    except Exception as e:
        print(f"   ❌ Database initialization failed: {e}")
        return False
    
    # Test data
    test_map_data = b"Test GeoJSON content"
    test_filename = "test_golf_course.geojson"
    
    # Test 1: Create and persist a map
    print("2️⃣ Creating and persisting map...")
    try:
        result = map_service.process_map_upload(
            file_data=test_map_data,
            filename=test_filename,
            name="Test Golf Course Map",
            version="1.0.0",
            center_lat=37.7749,
            center_lng=-122.4194,
            zoom_levels=[10, 12, 14, 16, 18],
            uploaded_by_id=str(uuid4()),
            golf_course_id=None
        )
        
        map_id = result.get('map_id')
        print(f"   ✅ Map created with ID: {map_id}")
        print(f"   📍 Storage URL: {result.get('storage_url')}")
        print(f"   📊 Status: {result.get('status')}\n")
        
    except Exception as e:
        print(f"   ❌ Map creation failed: {e}")
        return False
    
    # Test 2: Retrieve map from database
    print("3️⃣ Retrieving map from database...")
    try:
        with get_db_context() as db:
            retrieved_map = db.query(Map).filter(Map.id == map_id).first()
            
            if retrieved_map:
                print(f"   ✅ Map retrieved successfully")
                print(f"   📋 Name: {retrieved_map.name}")
                print(f"   📋 Version: {retrieved_map.version}")
                print(f"   📋 Status: {retrieved_map.status}")
                print(f"   📋 File Type: {retrieved_map.file_type}")
                print(f"   📋 File Size: {retrieved_map.file_size} bytes\n")
            else:
                print(f"   ❌ Map not found in database")
                return False
                
    except Exception as e:
        print(f"   ❌ Map retrieval failed: {e}")
        return False
    
    # Test 3: List maps
    print("4️⃣ Listing all maps...")
    try:
        with get_db_context() as db:
            maps = map_service.list_maps({'status': 'active'}, db)
            print(f"   ✅ Found {len(maps)} active map(s)")
            
            for map_record in maps:
                print(f"   - {map_record.name} v{map_record.version} ({map_record.status})")
            print()
            
    except Exception as e:
        print(f"   ❌ Map listing failed: {e}")
        return False
    
    # Test 4: Update map status
    print("5️⃣ Updating map status...")
    try:
        with get_db_context() as db:
            success = map_service.update_map_status(str(map_id), 'archived', db)
            
            if success:
                print(f"   ✅ Map status updated to 'archived'")
                
                # Verify the update
                archived_map = db.query(Map).filter(Map.id == map_id).first()
                if archived_map and archived_map.status == 'archived':
                    print(f"   ✅ Status change verified\n")
                else:
                    print(f"   ⚠️ Status change not verified\n")
            else:
                print(f"   ❌ Map status update failed")
                return False
                
    except Exception as e:
        print(f"   ❌ Map status update failed: {e}")
        return False
    
    # Test 5: Test map service get_map_data method
    print("6️⃣ Testing get_map_data service method...")
    try:
        map_data = map_service.get_map_data(str(map_id))
        
        if map_data:
            print(f"   ✅ Map data retrieved via service")
            print(f"   📋 Data keys: {list(map_data.keys())[:5]}...")  # Show first 5 keys
            print()
        else:
            print(f"   ❌ Map data not retrieved")
            return False
            
    except Exception as e:
        print(f"   ❌ Map data retrieval failed: {e}")
        return False
    
    print("✨ All tests passed successfully!")
    return True


def cleanup_test_data():
    """Clean up test data from database."""
    print("\n🧹 Cleaning up test data...")
    try:
        with get_db_context() as db:
            # Delete all test maps
            test_maps = db.query(Map).filter(Map.name.like("Test%")).all()
            for map_record in test_maps:
                db.delete(map_record)
            db.commit()
            print(f"   ✅ Cleaned up {len(test_maps)} test map(s)")
            
    except Exception as e:
        print(f"   ❌ Cleanup failed: {e}")


def main():
    """Main test runner."""
    print("=" * 50)
    print("MAP PERSISTENCE TEST SUITE")
    print("=" * 50)
    print()
    
    success = test_map_persistence()
    
    if success:
        print("\n" + "=" * 50)
        print("✅ ALL TESTS PASSED")
        print("=" * 50)
        
        # Ask if user wants to clean up
        response = input("\nClean up test data? (y/n): ")
        if response.lower() == 'y':
            cleanup_test_data()
    else:
        print("\n" + "=" * 50)
        print("❌ TESTS FAILED")
        print("=" * 50)
        sys.exit(1)


if __name__ == "__main__":
    main()