from __future__ import annotations

from unittest.mock import Mock, call, sentinel

import pytest

from coeur import ServiceValidationError, action


def test_service_action_ko_multiple_contexts_defined():
    """Assert than an error is raised if a second validator context factory is registered"""
    with pytest.raises(ValueError) as ctx:

        class Service:
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
    """Assert that the output of the validator context factory gets passed to the validators"""
    context = Mock()
    validator = Mock()
    perform = Mock()

    class Service:
        @action
        def my_action(self, data):
            return perform(self=self, data=data)

        @my_action.validator_context
        def get_context(self, data):
            context(self=self, data=data)
            return context

        @my_action.validate
        def validate_action(self, context, data):
            validator(self=self, context=context, data=data)

    service = Service()
    output = service.my_action(data=sentinel.data)
    context.assert_called_with(self=service, data=sentinel.data)
    validator.assert_called_with(self=service, context=context, data=sentinel.data)
    perform.assert_called_with(self=service, data=sentinel.data)
    assert output == perform.return_value


def test_service_action_without_options_input():
    """The action action_without_context has two validations that should be
    performed in the order of definition"""  # noqa
    validator_a = Mock()
    validator_b = Mock()
    perform = Mock()

    class Service:
        @action
        def my_action(self, data):
            return perform(self=self, data=data)

        @my_action.validate
        def validate_a(self, data):
            validator_a(self=self, data=data)

        @my_action.validate
        def validate_b(self, data):
            validator_b(self=self, data=data)

    service = Service()
    output = service.my_action(data=sentinel.data)
    assert output == perform.return_value
    validator_a.assert_called_with(self=service, data=sentinel.data)
    perform.assert_called_with(self=service, data=sentinel.data)


def test_service_action_validator_raise():
    """Test that any validations have their exceptions raised"""

    class Service:
        @action
        def my_action(self, data):
            return action(self=self, data=data)

        @my_action.validate
        def validate_a(self, data):
            raise ServiceValidationError()

    with pytest.raises(ServiceValidationError):
        Service().my_action(data=sentinel.data)


def test_service_action_with_options_input():
    """The action action_with_context has two validations that should be
    performed in the order of definition"""  # noqa

    unbound_validator = Mock()
    bound_validator = Mock()
    perform = Mock()

    def first_validation(service, data):
        unbound_validator(service=service, data=data)

    class Service:
        @action(validators=[first_validation])
        def my_action(self, data):
            return perform(self=self, data=data)

        @my_action.validate
        def validate_hello_in_data(self, data):
            bound_validator(self=self, data=data)

    service = Service()

    output = service.my_action(data=sentinel.data)
    assert output == perform.return_value
    unbound_validator.assert_called_with(service=service, data=sentinel.data)
    bound_validator.assert_called_with(self=service, data=sentinel.data)
    perform.assert_called_with(self=service, data=sentinel.data)


def test_service_action_external_bound_validator():
    external_validator = Mock()

    class ExternalValidator:
        def external_validate(self, service, data):
            external_validator(self=self, service=service, data=data)

    external = ExternalValidator()

    class Service:
        @action(validators=[external.external_validate])
        def my_action(self, data):
            return data

    service = Service()
    service.my_action(data=sentinel.data)
    external_validator.assert_called_with(
        self=external, service=service, data=sentinel.data
    )


def test_service_action_internal_bound_validator__lazy_registration_on_non_instance():
    internal_validator = Mock()

    class Service:
        @action
        def my_action(self):
            pass

        def lazy_registered_validator(self):
            internal_validator(self=self)

    Service.my_action.action.validate(Service.lazy_registered_validator)
    service = Service()
    service.my_action()
    internal_validator.assert_called_with(self=service)


def test_service_action_internal_bound_validator__lazy_registration_on_instance():
    internal_validator = Mock()

    class Service:
        @action
        def my_action(self):
            pass

        def lazy_registered_validator(self):
            internal_validator(self=self)

    service = Service()
    service.my_action.action.validate(service.lazy_registered_validator)
    service.my_action()
    internal_validator.assert_called_with(self=service)


def test_service_action_internal_bound_validator__lazy_registration_on_instance_of_static_validator():
    internal_validator = Mock()

    class Service:
        @action
        def my_action(self):
            pass

        @staticmethod
        def lazy_registered_validator(service):
            internal_validator(service=service)

    service = Service()
    service.my_action.action.validate(service.lazy_registered_validator)
    service.my_action()
    internal_validator.assert_called_with(service=service)


def test_service_action_validator_call_order():
    """Assert that the validations are called in order of definition"""
    log = Mock()

    def first_validation(service):
        log("first")

    def second_validation(service):
        log("second")

    class Service:
        @action(validators=[first_validation, second_validation])
        def my_action(self):
            pass

        @my_action.validate
        def third_validation(self):
            log("third")

        @my_action.validate
        def fourth_validation(self):
            log("fourth")

    service = Service()
    service.my_action()
    assert log.call_args_list == [
        call("first"),
        call("second"),
        call("third"),
        call("fourth"),
    ]


def test_service_action_ko_method_already_set():
    """Assert that an error is raised if we attempt to register a second method"""
    with pytest.raises(ValueError) as ctx:

        class Service:
            @action
            def my_action(self):
                ...

            @my_action.register
            def second_method(self):
                ...

    assert repr(ctx.value) == "ValueError('Method already set for action')"


def test_service_action_with_no_parameters():
    """Simple test to make sure the flow works when no parameters are required by the action method"""

    class Service:
        @action
        def my_action(self):
            return sentinel.output

        @my_action.validate
        def validate_action(self):
            return

    service = Service()
    output = service.my_action()
    assert output == sentinel.output


def test_service_action_wrapped_method_using():
    validator_a = Mock()
    validator_b = Mock()

    def validate_a(service):
        validator_a()

    class Service:
        @action(validators=[validate_a])
        def my_action(self):
            pass

        @my_action.validate
        def validate_b(self):
            validator_b()

    service = Service()
    # Assert the initial state
    assert [v.__name__ for v in service.my_action.action.validators] == [
        "validate_a",
        "validate_b",
    ]

    with service.my_action.using([service.validate_b]):
        assert [v.__name__ for v in service.my_action.action.validators] == [
            "validate_b"
        ]
        service.my_action()

    validator_a.assert_not_called()
    validator_b.assert_called()

    # Assert the final state
    assert [v.__name__ for v in service.my_action.action.validators] == [
        "validate_a",
        "validate_b",
    ]


def test_service_action_wrapped_method_using__bound_method__external_bound():
    """The behaviour for normal validator registration is that the values passed
    to the action are unbound, so when they are consumed, we inject the service class as self.

    If the validator is a bound method, but bound to a different instance,
    we should still inject the service as an argument."""
    external_validator = Mock()

    class ExternalValidator:
        def external_validate(self, service, data):
            external_validator(self=self, service=service, data=data)

    external = ExternalValidator()

    class Service:
        @action()
        def my_action(self, data):
            return data

    service = Service()
    with service.my_action.using([external.external_validate]):
        service.my_action(data=sentinel.data)

    external_validator.assert_called_with(
        self=external, service=service, data=sentinel.data
    )


def test_service_action_wrapped_method_using__bound_method__service_bound():
    """The behaviour for normal validator registration is that the values passed
    to the action are unbound, so when they are consumed, we inject the service class as self.

    However if we override with "using", we can pass bound-methods.
    In this case, if the method is already bound to the same service,
    we don't want to inject the service, because this is done implicitly.

    If the validator is a bound method, but bound to a different instance,
    we should still inject the service as an argument."""
    validator = Mock()

    class Service:
        @action
        def my_action(self, data):
            return data

        def validate(self, data):
            validator(self=self, data=data)

    service = Service()
    with service.my_action.using([service.validate]):
        service.my_action(data=sentinel.data)

    validator.assert_called_with(self=service, data=sentinel.data)


def test_service_action_wrapped_method_exclude():
    log = Mock()

    class Service:
        @action
        def my_action(self):
            pass

        @my_action.validate
        def validate_a(self):
            log("a")

        @my_action.validate
        def validate_b(self):
            log("b")

    service = Service()

    # Check the initial state
    service.my_action()
    assert log.call_args_list == [call("a"), call("b")]
    log.reset_mock()

    # Check the excluded state
    with service.my_action.excluding([service.validate_a.__name__]):
        service.my_action()
    assert log.call_args_list == [call("b")]
    log.reset_mock()

    # Check the final state
    service.my_action()
    assert log.call_args_list == [call("a"), call("b")]
    log.reset_mock()


def test_service_action_wrapped_method_only():
    log = Mock()

    class Service:
        @action
        def my_action(self):
            pass

        @my_action.validate
        def validate_a(self):
            log("a")

        @my_action.validate
        def validate_b(self):
            log("b")

    service = Service()

    # Check the initial state
    service.my_action()
    assert log.call_args_list == [call("a"), call("b")]
    log.reset_mock()

    # Check the excluded state
    with service.my_action.only([service.validate_a.__name__]):
        service.my_action()
    assert log.call_args_list == [call("a")]
    log.reset_mock()

    # Check the final state
    service.my_action()
    assert log.call_args_list == [call("a"), call("b")]
    log.reset_mock()


def test_service_action_skip_context_if_no_validators():
    context = Mock()

    class Service:
        @action
        def my_action(self):
            pass

        @my_action.validator_context
        def make_context(self):
            context()

    Service().my_action()
    context.assert_not_called()
