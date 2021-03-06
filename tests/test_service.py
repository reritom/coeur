from __future__ import annotations

import pytest

from coeur import Service, ServiceValidationError, action


def test_service_init_missing_required_context_arg_ko(service_class):
    with pytest.raises(TypeError):
        service_class()


def test_service_init_ko_meta_context_not_dataclass():
    with pytest.raises(TypeError):

        class TestService(Service):
            class Meta:
                class Context:
                    user_id: int | None = None
                    is_superuser: bool


def test_service_init_validate_against_meta_ok(service_class):
    service = service_class(user_id=1, is_superuser=True)
    assert service.context.user_id == 1
    assert service.context.is_superuser is True


def test_service_init_validate_against_meta_ko(service_class):
    with pytest.raises(TypeError):
        service_class(something_else=5)


def test_service_action_ko_explicit_permission_failure(service_class):
    """For the action_with_multiple_validations action the permission is explicitly stated
    as is_superuser, so if the user isn't a superuser, the method should fail"""  # noqa
    service = service_class(is_superuser=False, user_id=1)

    with pytest.raises(PermissionError) as ctx:
        service.action_with_multiple_validations({})

    assert repr(ctx.value) == "PermissionError('User is not superuser')"


def test_service_action_ko_multiple_contexts_defined():
    with pytest.raises(ValueError) as ctx:

        class DummyService(Service):
            @action
            def my_action(self, data):
                ...

            @my_action.validator_context
            def get_context(self, data):
                return {}

            @my_action.validator_context
            def get_context_again(self, data):
                return {}

    assert (
        repr(ctx.value)
        == "ValueError('Validator context maker already set for action')"
    )


def test_service_action_with_context():
    class DummyService(Service):
        @action
        def my_action(self, data):
            ...

        @my_action.validator_context
        def get_context(self, data):
            if data.get("test"):
                return {"context_a": "value"}
            return {"normal_context": "value"}

        @my_action.validate
        def validate_action(self, context, data):
            if "context_a" in context:
                raise ServiceValidationError()

    with pytest.raises(ServiceValidationError):
        DummyService().my_action({"test": True})

    DummyService().my_action({})


def test_service_action_ko_service_permission_failure(service_class):
    """The action action_using_service_permissions has not explicit permissions, so it will use
    the service level permissions to check that the user is authenticated (not none)"""  # noqa
    service = service_class(is_superuser=False, user_id=None)

    with pytest.raises(PermissionError) as ctx:
        service.action_using_service_permissions({})

    assert repr(ctx.value) == "PermissionError('User is not authenticated')"


def test_service_action_validate_input(service_class):
    """The action action_with_multiple_validations has two validations that should be
    performed in the order of definition"""  # noqa
    service = service_class(is_superuser=True, user_id=1)

    # The first defined validator should fail
    with pytest.raises(ServiceValidationError) as ctx:
        service.action_with_multiple_validations({})

    assert repr(ctx.value) == "ServiceValidationError('hello not in data')"

    # The second defined validator should fail
    with pytest.raises(ServiceValidationError) as ctx:
        service.action_with_multiple_validations({"hello": 1})

    assert repr(ctx.value) == "ServiceValidationError('world not in data')"

    # With the correct data, there should be no error
    service.action_with_multiple_validations({"hello": 1, "world": 2})


def test_service_action_validate_input_using_dataclass_service(
    service_class_using_dataclass,
):
    """The action action_with_multiple_validations has two validations that should be
    performed in the order of definition"""  # noqa
    service = service_class_using_dataclass(is_superuser=True, user_id=1)

    # The first defined validator should fail
    with pytest.raises(ServiceValidationError) as ctx:
        service.my_action({})

    assert repr(ctx.value) == "ServiceValidationError('hello not in data')"

    service.my_action({"hello": 1})


def test_service_action_dont_use_service_permissions(service_class):
    """The action permissionless_action has no explicit permissions, and is set to
    not use the service permissions, so even an unauthenticated user can use it"""  # noqa
    service = service_class(is_superuser=False, user_id=None)

    service.permissionless_action({})


def test_service_ko_method_already_set():
    with pytest.raises(ValueError) as ctx:

        class DummyService(Service):
            @action
            def my_action(self):
                ...

            @my_action.method
            def second_method(self):
                ...

    assert repr(ctx.value) == "ValueError('Method already set for action')"


def test_service_ko_permission_method_already_set():
    with pytest.raises(ValueError) as ctx:

        class DummyService(Service):
            @action
            def my_action(self):
                ...

            @my_action.permissions
            def first_permissions(self):
                ...

            @my_action.permissions
            def second_permissions(self):
                ...

    assert (
        repr(ctx.value)
        == "ValueError('Permission method already set for action')"  # noqa
    )


def test_service_action_with_check_permissions():
    class DummyService(Service):
        @action
        def my_action(self, data):
            return "something"

        @my_action.permission_check
        def check_permission(self, data):
            raise PermissionError("Check failed")

    # The first defined validator should fail
    with pytest.raises(PermissionError) as ctx:
        DummyService().my_action({})

    assert repr(ctx.value) == "PermissionError('Check failed')"


def test_service_with_no_parameters():
    class DummyService(Service):
        @action
        def my_action(self):
            return "something"

        @my_action.validate
        def validate_action(self):
            return

    service = DummyService()
    output = service.my_action()
    assert output == "something"


def test_service_init_with_no_meta():
    class DummyService(Service):
        ...

    service = DummyService(hello=1, world=2)
    assert service.hello == 1
    assert service.world == 2
