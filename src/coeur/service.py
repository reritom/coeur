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
    def __init__(self, name: str, use_service_permissions: bool = True):
        self.name = name
        self.__use_service_permissions = use_service_permissions
        self.__method = None
        self.__permission_method = None
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
            raise ValueError(f"Method not set for action {self!r}")

        for permission in self._get_permissions(_service, *args, **kwargs):
            permission().check_permission(_service, *args, **kwargs)

        for validator in self.__validators:
            validator(_service, *args, **kwargs)

        return self.__method(_service, *args, **kwargs)

    def method(self, func: Callable) -> Callable:
        if self.__method:
            raise ValueError(f"Method already set for {self!r}")
        self.__method = func
        return func

    def validate(self, func: Callable) -> Callable:
        self.__validators.append(func)
        return func

    def permissions(self, func: Callable) -> Callable:
        if self.__permission_method:
            raise ValueError(f"Permission method already set for {self!r}")
        self.__permission_method = func
        return func

    def __repr__(self):
        return f"ServiceAction(name='{self.name}')"
