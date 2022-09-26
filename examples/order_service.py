from __future__ import annotations

import datetime
from dataclasses import dataclass, field

from coeur import ServiceValidationError, action


def yesterday():
    return datetime.date.today() - datetime.timedelta(days=1)


def tomorrow():
    return datetime.date.today() + datetime.timedelta(days=1)

def next_week():
    return datetime.date.today() + datetime.timedelta(days=7)


@dataclass
class OrderItem:
    product: str
    quantity: int
    unit: str


@dataclass
class Order:
    shipping_date: datetime.datetime
    items: list[OrderItem] = field(default_factory=list)


class Dao:
    """A dummy database access layer"""
    def create_order(order: Order) -> Order:
        # Pretend we persisted this
        return order


def validate_something_static(service, order: Order):
    ...


class OrderService:
    def __init__(self, minimum_shipping_duration: datetime.timedelta):
        # Misc attribute to show that actions can reference the service instance
        # The any shipping date that is closer than this minimum duration should be rejected
        self.minimum_shipping_duration = minimum_shipping_duration

    # @action(validators=[validate_something_static])
    # Or
    @action
    def create_order(self, order: Order) -> Order:
        return Dao.create_order(order)

    @create_order.validate
    def validate_order_items(self, order: Order):
        if not order.items:
            raise ServiceValidationError("Order requires order items")
        return order

    @create_order.validate
    def validate_order_shipping_date_not_in_past(self, order: Order):
        if not order.shipping_date >= datetime.date.today():
            raise ServiceValidationError("Order shipping date is in the past")
        return order

    @create_order.validate
    def validate_order_shipping_date_not_too_soon(self, order: Order):
        if (order.shipping_date - datetime.date.today()) < self.minimum_shipping_duration:
            raise ServiceValidationError("Order shipping date is too soon, not enough time to prepare")
        return order


def test_no_items():
    service = OrderService(minimum_shipping_duration=datetime.timedelta(days=5))

    # Both validations will fail
    order = Order(shipping_date=yesterday(), items=[])
    try:
        order = service.create_order(order)
    except ServiceValidationError:
        # Error "Order requires order items"
        pass

def test_no_items_and_invalid_shipping_date():
    service = OrderService(minimum_shipping_duration=datetime.timedelta(days=5))

    # Both the second validation will fail
    order = Order(
        shipping_date=yesterday(),
        items=[OrderItem(product="mayo", quantity=1, unit="litre")],
    )
    try:
        order = service.create_order(order)
    except ServiceValidationError:
        # Error "Order shipping date is in the past"
        pass

def test_shipping_too_soon():
    service = OrderService(minimum_shipping_duration=datetime.timedelta(days=5))

    # Both validations are ok
    order = Order(
        shipping_date=tomorrow(),
        items=[OrderItem(product="mayo", quantity=1, unit="litre")],
    )

    try:
        order = service.create_order(order)
    except ServiceValidationError:
        # Error "Order shipping date is too soon, not enough time to prepare"
        pass

def test_ok():
    service = OrderService(minimum_shipping_duration=datetime.timedelta(days=5))

    # Both validations are ok
    order = Order(
        shipping_date=next_week(),
        items=[OrderItem(product="mayo", quantity=1, unit="litre")],
    )

    service.create_order(order)



if __name__ == "__main__":
    test_no_items()
    test_no_items_and_invalid_shipping_date()
    test_shipping_too_soon()
    test_ok()