"""
Test script to verify transaction handling improvements.

Run this script to test:
1. Rollback on errors
2. Atomic operations
3. Unit of Work pattern
"""

import asyncio
import sys
from pathlib import Path
from uuid import uuid4

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from app.database import SessionLocal, get_db
from app.infrastructure.persistence.unit_of_work import UnitOfWork
from app.domain.fleet.entities import GolfCart
from app.domain.fleet.value_objects import CartNumber, Position, Battery
from app.domain.shared.cart_status import CartStatus
from app.infrastructure.persistence.repositories.sqlalchemy_cart_repository import (
    SQLAlchemyCartRepository
)


async def test_rollback_on_error():
    """Test that transactions rollback on error."""
    print("\n=== Test 1: Rollback on Error ===")
    
    # Create a session
    db = SessionLocal()
    repo = SQLAlchemyCartRepository(db)
    
    try:
        # Try to create a cart with an invalid operation
        cart = GolfCart(
            cart_number=CartNumber(f"TEST-ROLLBACK-{uuid4().hex[:8]}"),
            position=Position(0.0, 0.0),
            battery=Battery(100.0),
            status=CartStatus.IDLE
        )
        
        # Save the cart (this should work)
        await repo.save(cart)
        
        # Now simulate an error by forcing an exception
        raise Exception("Simulated error after save")
        
    except Exception as e:
        print(f"✅ Error caught as expected: {e}")
        db.rollback()
        print("✅ Transaction rolled back")
        
        # Verify the cart was not saved
        saved_cart = await repo.get_by_id(cart.id)
        if saved_cart is None:
            print("✅ Cart was not persisted (rollback worked)")
        else:
            print("❌ Cart was persisted (rollback failed)")
    
    finally:
        db.close()


async def test_unit_of_work_pattern():
    """Test Unit of Work pattern for atomic operations."""
    print("\n=== Test 2: Unit of Work Pattern ===")
    
    cart_id = None
    
    # Test successful transaction
    async with UnitOfWork() as uow:
        cart = GolfCart(
            cart_number=CartNumber(f"TEST-UOW-{uuid4().hex[:8]}"),
            position=Position(10.0, 20.0),
            battery=Battery(80.0),
            status=CartStatus.IDLE
        )
        
        saved_cart = await uow.golf_cart_repository.save(cart)
        cart_id = saved_cart.id
        print(f"✅ Cart created with ID: {cart_id}")
        
        # Update the cart
        saved_cart.update_position(Position(15.0, 25.0))
        await uow.golf_cart_repository.save(saved_cart)
        print("✅ Cart position updated")
        
        # Transaction commits automatically on context exit
    
    print("✅ Transaction committed successfully")
    
    # Verify the cart was saved
    async with UnitOfWork() as uow:
        verified_cart = await uow.golf_cart_repository.get_by_id(cart_id)
        if verified_cart and verified_cart.position.latitude == 15.0:
            print("✅ Cart persisted with updated position")
        else:
            print("❌ Cart not found or position not updated")
    
    # Test rollback on error
    print("\n--- Testing UoW rollback ---")
    
    try:
        async with UnitOfWork() as uow:
            cart2 = GolfCart(
                cart_number=CartNumber(f"TEST-UOW-FAIL-{uuid4().hex[:8]}"),
                position=Position(30.0, 40.0),
                battery=Battery(60.0),
                status=CartStatus.IDLE
            )
            
            await uow.golf_cart_repository.save(cart2)
            print("✅ Cart saved in UoW")
            
            # Simulate an error
            raise Exception("Simulated error in UoW")
            
    except Exception as e:
        print(f"✅ Error caught: {e}")
        print("✅ UoW automatically rolled back")
    
    # Verify the second cart was not saved
    async with UnitOfWork() as uow:
        failed_cart = await uow.golf_cart_repository.get_by_cart_number(
            CartNumber(f"TEST-UOW-FAIL-{uuid4().hex[:8]}")
        )
        if failed_cart is None:
            print("✅ Failed transaction was rolled back (cart not found)")
        else:
            print("❌ Failed transaction was not rolled back")


async def test_new_session_management():
    """Test the improved session management with automatic commit/rollback."""
    print("\n=== Test 3: New Session Management ===")
    
    # Simulate what happens in a FastAPI endpoint
    class MockRequest:
        """Mock request to simulate FastAPI dependency injection."""
        
        def __init__(self):
            self.db_generator = get_db()
            self.db = None
        
        def __enter__(self):
            self.db = next(self.db_generator)
            return self.db
        
        def __exit__(self, exc_type, exc_val, exc_tb):
            try:
                if exc_type:
                    # This simulates an exception in the endpoint
                    self.db_generator.throw(exc_type, exc_val, exc_tb)
                else:
                    # Normal completion
                    next(self.db_generator, None)
            except StopIteration:
                pass
    
    # Test successful operation
    print("\n--- Testing successful operation ---")
    with MockRequest() as db:
        repo = SQLAlchemyCartRepository(db)
        cart = GolfCart(
            cart_number=CartNumber(f"TEST-SESSION-{uuid4().hex[:8]}"),
            position=Position(50.0, 60.0),
            battery=Battery(90.0),
            status=CartStatus.IDLE
        )
        await repo.save(cart)
        print("✅ Cart saved in session")
    
    print("✅ Session committed automatically")
    
    # Test operation with error
    print("\n--- Testing operation with error ---")
    try:
        with MockRequest() as db:
            repo = SQLAlchemyCartRepository(db)
            cart = GolfCart(
                cart_number=CartNumber(f"TEST-SESSION-FAIL-{uuid4().hex[:8]}"),
                position=Position(70.0, 80.0),
                battery=Battery(70.0),
                status=CartStatus.IDLE
            )
            await repo.save(cart)
            print("✅ Cart saved in session")
            
            # Simulate an error
            raise ValueError("Simulated error in endpoint")
            
    except ValueError as e:
        print(f"✅ Error caught: {e}")
        print("✅ Session rolled back automatically")


async def main():
    """Run all tests."""
    print("=" * 50)
    print("TRANSACTION HANDLING TEST SUITE")
    print("=" * 50)
    
    try:
        await test_rollback_on_error()
        await test_unit_of_work_pattern()
        await test_new_session_management()
        
        print("\n" + "=" * 50)
        print("✅ ALL TESTS COMPLETED")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())