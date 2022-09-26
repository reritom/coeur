from __future__ import annotations

import pytest

from coeur import ServiceValidationError, action




def test_service_action_ko_multiple_contexts_defined():
    with pytest.raises(ValueError) as ctx:

        class DummyService:
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
        == "ValueError('Validator context factory already set for action')"
    )


def test_service_action_with_context():
    class Service:
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
        Service().my_action({"test": True})

    Service().my_action({})


def test_service_action_without_options_input():
    """The action action_without_context has two validations that should be
    performed in the order of definition"""  # noqa
    class Service:
        @action
        def action_without_actions(self, data: dict):
            assert isinstance(self, Service)
            return data

        @action_without_actions.validate
        def validate_hello_in_data(self, data: dict):
            if "hello" not in data:
                raise ServiceValidationError("hello not in data")
            return data

        @action_without_actions.validate
        def validate_world_in_data(self, data: dict):
            if "world" not in data:
                raise ServiceValidationError("world not in data")
            return data

    service = Service()

    # The first defined validator should fail
    with pytest.raises(ServiceValidationError) as ctx:
        service.action_without_actions({})

    assert repr(ctx.value) == "ServiceValidationError('hello not in data')"

    # The second defined validator should fail
    with pytest.raises(ServiceValidationError) as ctx:
        service.action_without_actions({"hello": 1})

    assert repr(ctx.value) == "ServiceValidationError('world not in data')"

    # With the correct data, there should be no error
    service.action_without_actions({"hello": 1, "world": 2})


def test_service_action_with_options_input():
    """The action action_with_context has two validations that should be
    performed in the order of definition"""  # noqa
    def first_validation(service, data):
        if "one" not in data:
            raise ServiceValidationError("This is raised first")

    class Service:
        @action(validators=[first_validation])
        def action_with_options(self, data: dict):
            assert isinstance(self, Service)
            return data

        @action_with_options.validate
        def validate_hello_in_data(self, data: dict):
            if "two" not in data:
                raise ServiceValidationError("This is raised second")
            return data


    service = Service()

    # The first defined validator should fail
    with pytest.raises(ServiceValidationError) as ctx:
        service.action_with_options({})

    assert repr(ctx.value) == "ServiceValidationError('This is raised first')"

    # The second defined validator should fail
    with pytest.raises(ServiceValidationError) as ctx:
        service.action_with_options({"one": 1})

    assert repr(ctx.value) == "ServiceValidationError('This is raised second')"

    # With the correct data, there should be no error
    service.action_with_options({"one": 1, "two": 2})


def test_service_ko_method_already_set():
    with pytest.raises(ValueError) as ctx:

        class Service:
            @action
            def my_action(self):
                ...

            @my_action.register
            def second_method(self):
                ...

    assert repr(ctx.value) == "ValueError('Method already set for action')"


def test_service_with_no_parameters():
    class Service:
        @action
        def my_action(self):
            return "something"

        @my_action.validate
        def validate_action(self):
            return

    service = Service()
    output = service.my_action()
    assert output == "something"