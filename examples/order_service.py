from __future__ import annotations
from coeur import Service, ServiceAction, ServiceValidationError
from dataclasses import dataclass, field
from typing import List
import datetime


def yesterday():
    return datetime.date.today() - datetime.timedelta(days=1)

def tomorrow():
    return datetime.date.today() + datetime.timedelta(days=1)


@dataclass
class User:
    name: str
    can_create_orders: bool


@dataclass
class OrderItem:
    product: str
    quantity: int
    unit: str

@dataclass
class Order:
    shipping_date: datetime.datetime
    items: List[OrderItemDataclass] = field(default_factory=list)



class Permission:
    pass

class Authenticated(Permission):
    """We'll assume that if the service is initialised with a user, that the user
    has been authenticated"""

    def check_permission(self, service: Service, *args, **kwargs):
        if not bool(service.user):
            raise PermissionError("Authenticated user required")


class CanCreateOrders(Permission):
    """A user can only create an order if they have a feature flag on their user model"""

    def check_permission(self, service: Service, *args, **kwargs):
        if not (service.user and service.user.can_create_orders):
            raise PermissionError("User cannot create orders")


class Dao:
    """A dummy database access layer"""
    def create_order(order: Order) -> Order:
        # Pretend we persisted this
        return order

    def get_orders() -> List[Order]:
        # Pretend we got this from a database
        return [
            Order(
                shipping_date=tomorrow(),
                items=[OrderItem(product="mayo", quantity=5, unit="kg")]
            )
        ]





class OrderService(Service):
    permissions = (Authenticated)
    create = ServiceAction("create")
    list = ServiceAction("list")
    emails = ServiceAction("email", use_service_permissions=False)

    class Meta:
        @dataclass
        class Context:
            user: Optional[User] = None

    @create.permissions
    def get_order_creation_permissions(self, order: Order) -> List[Permission]:
        return (Authenticated, CanCreateOrders)

    @create.validate
    def validate_order_items(self, order: Order):
        if not order.items:
            raise ServiceValidationError("Order requires order items")
        return order

    @create.validate
    def validate_order_shipping_date(self, order: Order):
        if not order.shipping_date >= datetime.date.today():
            raise ServiceValidationError("Order shipping date is in the past")
        return order

    @create.method
    def create_order(self, order: Order) -> Order:
        return Dao.create_order(order)

    @list.method
    def get_orders(self) -> List[Order]:
        return Dao.get_orders()

    @emails.method
    def send_daily_emails(self):
        # Some method that is used without a specific authenticated user, maybe
        # called by a celery task. Note it can still have validators if needed
        ...




def user_cant_create_order():
    # Permission error, user can't create an order
    user = User(name="Tom", can_create_orders=False)
    service = OrderService(user=user)

    order = Order(shipping_date=tomorrow(), items=[])
    try:
        order = service.create_order(order)
    except PermissionError:
        # Error ""User cannot create orders""
        pass

def validation_errors():
    # An example for a valid user, with invalid order parameters
    user = User(name="Tom", can_create_orders=True)
    service = OrderService(user=user)

    # Both validations will fail
    order = Order(shipping_date=yesterday(), items=[])
    try:
        order = service.create_order(order)
    except ServiceValidationError:
        # Error "Order requires order items"
        pass

    # Both the second validation will fail
    order = Order(shipping_date=yesterday(), items=[OrderItem(product="mayo", quantity=1, unit="litre")])
    try:
        order = service.create_order(order)
    except ServiceValidationError:
        # Error "Order shipping date is in the past"
        pass

    # Both validations are ok
    order = Order(shipping_date=tomorrow(), items=[OrderItem(product="mayo", quantity=1, unit="litre")])

def getting_orders_with_service_level_permissions():
    # Unauthenticated (no user set on service)
    service = OrderService()
    try:
        orders = service.get_orders()
    except PermissionError:
        # Error "Authenticated user required"
        pass

    # Authenticated user can retrieve orders, based on service level permissions
    # instead of permissions set on the action
    user = User(name="Jack", can_create_orders=False)
    service = OrderService(user=user)
    orders = service.get_orders()


if __name__ == "__main__":
    user_cant_create_order()
    validation_errors()
    getting_orders_with_service_level_permissions()
