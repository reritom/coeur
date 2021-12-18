from __future__ import annotations

from dataclasses import is_dataclass
from functools import wraps
from typing import Callable, Protocol


class ServiceValidationError(Exception):
    pass


class PermissionProtocol(Protocol):
    def check_permission(self, service: Service, *args, **kwargs):
        ...


class ServiceMetaClass(type):
    def __new__(cls, name, bases, namespace):
        if (
            "Meta" in namespace
            and hasattr(namespace["Meta"], "Context")
            and not is_dataclass(namespace["Meta"].Context)
        ):
            raise TypeError("Meta needs to be a dataclass")

        return super().__new__(cls, name, bases, namespace)


class Service(metaclass=ServiceMetaClass):
    def __init__(self, *args, **kwargs):
        self.context = None

        if hasattr(self, "Meta") and hasattr(self.Meta, "Context"):
            self.context = self.Meta.Context(**kwargs)
        else:
            for key, value in kwargs.items():
                setattr(self, key, value)


class ServiceAction:
    def __init__(
        self, method: Callable | None = None, use_service_permissions: bool = True
    ):
        self.__use_service_permissions = use_service_permissions
        self.__method = method
        self.__permission_method = None
        self.__validator_context_func = None
        self.__permission_checks = []
        self.__validators = []

    def __get__(self, obj, objtype=None):
        @wraps(self.__call__)
        def wrapper(*args, **kwargs):
            return self.__call__(obj, *args, **kwargs)

        return wrapper

    def _get_permissions(
        self, _service: Service, *args, **kwargs
    ) -> tuple[PermissionProtocol, ...]:
        if self.__permission_method:
            return self.__permission_method(_service, *args, **kwargs)
        elif self.__use_service_permissions and hasattr(_service, "permissions"):
            return _service.permissions
        else:
            return tuple()

    def __call__(self, _service: Service, *args, **kwargs):
        if not self.__method:
            raise ValueError("Method not set for actiom")

        context = (
            self.__validator_context_func(_service, *args, **kwargs)
            if self.__validator_context_func
            else None
        )

        for permission in self._get_permissions(_service, *args, **kwargs):
            permission().check_permission(_service, *args, **kwargs)

        for permission_check in self.__permission_checks:
            permission_check(_service, *args, **kwargs)

        for validator in self.__validators:
            validator(_service, context, *args, **kwargs) if context else validator(
                _service, *args, **kwargs
            )

        return self.__method(_service, *args, **kwargs)

    def method(self, func: Callable) -> Callable:
        if self.__method:
            raise ValueError("Method already set for action")
        self.__method = func
        return func

    def validate(self, func: Callable) -> Callable:
        self.__validators.append(func)
        return func

    def permissions(self, func: Callable) -> Callable:
        if self.__permission_method:
            raise ValueError("Permission method already set for action")
        self.__permission_method = func
        return func

    def permission_check(self, func: Callable) -> Callable:
        self.__permission_checks.append(func)
        return func

    def validator_context(self, func: Callable) -> Callable:
        if self.__validator_context_func:
            raise ValueError("Validator context maker already set for action")
        self.__validator_context_func = func
        return func


def action(func: Callable | None = None, **options):
    service_action = ServiceAction(method=func, **options)
    if not func:

        def inner(func):
            service_action.method(func)
            return service_action

        return inner
    return service_action
