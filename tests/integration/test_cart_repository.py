import pytest
from uuid import uuid4
from datetime import datetime, timezone
from app.domain.fleet.entities import GolfCart
from app.domain.fleet.value_objects import CartNumber, Position, Battery
from app.domain.shared.cart_status import CartStatus
from app.domain.fleet.events.cart_events import CartRegistered

@pytest.mark.asyncio
async def test_save_and_get_cart(async_uow):
    cart_id = uuid4()
    cart = GolfCart(
        entity_id=cart_id,
        cart_number=CartNumber("TEST001"),
        position=Position(0, 0),
        battery=Battery(100),
        status=CartStatus.IDLE,
        last_maintenance=datetime.now(timezone.utc),
    )

    async with async_uow.transaction():
        await async_uow.golf_cart_repository.save(cart)

    async with async_uow.transaction():
        retrieved_cart = await async_uow.golf_cart_repository.get_by_id(cart_id)

    assert retrieved_cart is not None
    assert retrieved_cart.id == cart_id
    assert retrieved_cart.cart_number.value == "TEST001"

@pytest.mark.asyncio
async def test_update_cart(async_uow):
    cart_id = uuid4()
    cart = GolfCart(
        entity_id=cart_id,
        cart_number=CartNumber("TEST002"),
        position=Position(0, 0),
        battery=Battery(100),
        status=CartStatus.IDLE,
        last_maintenance=datetime.now(timezone.utc),
    )

    async with async_uow.transaction():
        await async_uow.golf_cart_repository.save(cart)

    cart.start_trip()
    async with async_uow.transaction():
        await async_uow.golf_cart_repository.save(cart)

    async with async_uow.transaction():
        updated_cart = await async_uow.golf_cart_repository.get_by_id(cart_id)

    assert updated_cart is not None
    assert updated_cart.status == CartStatus.RUNNING

@pytest.mark.asyncio
async def test_delete_cart(async_uow):
    cart_id = uuid4()
    cart = GolfCart(
        entity_id=cart_id,
        cart_number=CartNumber("TEST003"),
        position=Position(0, 0),
        battery=Battery(100),
        status=CartStatus.IDLE,
    )

    async with async_uow.transaction():
        await async_uow.golf_cart_repository.save(cart)

    async with async_uow.transaction():
        await async_uow.golf_cart_repository.delete(cart_id)

    async with async_uow.transaction():
        deleted_cart = await async_uow.golf_cart_repository.get_by_id(cart_id)

    assert deleted_cart is None

@pytest.mark.asyncio
async def test_get_all_carts(async_uow):
    # Clear all carts first
    async with async_uow.transaction():
        carts = await async_uow.golf_cart_repository.get_all()
        for cart in carts:
            await async_uow.golf_cart_repository.delete(cart.id)

    cart1 = GolfCart(entity_id=uuid4(), cart_number=CartNumber("TEST004"), position=Position(0, 0), battery=Battery(100), status=CartStatus.IDLE)
    cart2 = GolfCart(entity_id=uuid4(), cart_number=CartNumber("TEST005"), position=Position(0, 0), battery=Battery(100), status=CartStatus.RUNNING)

    async with async_uow.transaction():
        await async_uow.golf_cart_repository.save(cart1)
        await async_uow.golf_cart_repository.save(cart2)

    async with async_uow.transaction():
        all_carts = await async_uow.golf_cart_repository.get_all()
        running_carts = await async_uow.golf_cart_repository.get_all(status=CartStatus.RUNNING)

    assert len(all_carts) == 2
    assert len(running_carts) == 1
    assert running_carts[0].cart_number.value == "TEST005"

@pytest.mark.asyncio
async def test_event_generation_on_save(async_uow):
    cart = GolfCart(
        cart_number=CartNumber("TEST006"),
        position=Position(0, 0),
        battery=Battery(100),
        status=CartStatus.IDLE,
    )
    events = cart.pull_events()
    assert len(events) == 1
    assert isinstance(events[0], CartRegistered)

    async with async_uow.transaction():
        await async_uow.golf_cart_repository.save(cart)

    # After saving, the events should be cleared from the entity
    assert len(cart.pull_events()) == 0

@pytest.mark.asyncio
async def test_uow_commit(async_uow):
    cart_id = uuid4()
    cart = GolfCart(
        entity_id=cart_id,
        cart_number=CartNumber("TEST007"),
        position=Position(0, 0),
        battery=Battery(100),
        status=CartStatus.IDLE,
    )

    async with async_uow.transaction():
        await async_uow.golf_cart_repository.save(cart)

    # The cart should be in the database after the transaction is committed
    async with async_uow.transaction():
        retrieved_cart = await async_uow.golf_cart_repository.get_by_id(cart_id)
    assert retrieved_cart is not None

@pytest.mark.asyncio
async def test_uow_rollback(async_uow):
    cart_id = uuid4()
    cart = GolfCart(
        entity_id=cart_id,
        cart_number=CartNumber("TEST008"),
        position=Position(0, 0),
        battery=Battery(100),
        status=CartStatus.IDLE,
    )

    with pytest.raises(Exception):
        async with async_uow.transaction():
            await async_uow.golf_cart_repository.save(cart)
            raise Exception("Something went wrong")

    # The cart should not be in the database after the transaction is rolled back
    async with async_uow.transaction():
        retrieved_cart = await async_uow.golf_cart_repository.get_by_id(cart_id)
    assert retrieved_cart is None
