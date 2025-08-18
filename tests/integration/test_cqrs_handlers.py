import pytest
from app.application.fleet.commands.register_cart import RegisterCartCommand, RegisterCartHandler

@pytest.mark.asyncio
async def test_register_cart_handler(async_uow):
    command = RegisterCartCommand(cart_number="TESTCQRS001")

    async with async_uow.transaction():
        handler = RegisterCartHandler(async_uow.golf_cart_repository)
        cart_id = await handler.handle(command)

    async with async_uow.transaction():
        cart = await async_uow.golf_cart_repository.get_by_id(cart_id)

    assert cart is not None
    assert cart.cart_number.value == "TESTCQRS001"
