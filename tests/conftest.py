from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

import pytest

from coeur import PermissionProtocol, Service, ServiceValidationError, action


@pytest.fixture
def is_authenticated():
    class IsAuthenticated:
        def check_permission(self, service, *args, **kwargs):
            if service.context.user_id is None:
                raise PermissionError("User is not authenticated")

    return IsAuthenticated


@pytest.fixture
def is_superuser():
    class IsSuperuser:
        def check_permission(self, service, *args, **kwargs):
            if not service.context.is_superuser:
                raise PermissionError("User is not superuser")

    return IsSuperuser


@pytest.fixture
def service_class(is_superuser, is_authenticated):
    class DummyService(Service):
        permissions = (is_authenticated,)

        class Meta:
            @dataclass
            class Context:
                is_superuser: bool
                user_id: int | None = None

        @action
        def action_with_multiple_validations(self, data: dict):
            return data

        @action(use_service_permissions=False)
        def permissionless_action(self, data: dict):
            return data

        @action
        def action_using_service_permissions(self, data: dict):
            return data

        @action_with_multiple_validations.validate
        def validate_hello_in_data(self, data: dict):
            if "hello" not in data:
                raise ServiceValidationError("hello not in data")
            return data

        @action_with_multiple_validations.validate
        def validate_world_in_data(self, data: dict):
            if "world" not in data:
                raise ServiceValidationError("world not in data")
            return data

        @action_with_multiple_validations.permissions
        def item_creation_permissions(self, data: dict):
            return (is_superuser,)

    return DummyService


@pytest.fixture
def service_class_using_dataclass():
    class IsAuthenticated:
        def check_permission(self, service, *args, **kwargs):
            if service.user_id is None:
                raise PermissionError("User is not authenticated")

    class IsSuperuser:
        def check_permission(self, service, *args, **kwargs):
            if not service.is_superuser:
                raise PermissionError("User is not superuser")

    @dataclass
    class DummyService:
        is_superuser: bool
        user_id: int | None = None
        permissions: ClassVar[tuple[PermissionProtocol]] = (IsAuthenticated,)

        @action
        def my_action(self, data: dict):
            return data

        @my_action.validate
        def validate_hello_in_data(self, data: dict):
            if "hello" not in data:
                raise ServiceValidationError("hello not in data")
            return data

        @my_action.permissions
        def method_permissions(self, data: dict):
            return (IsSuperuser,)

    return DummyService
