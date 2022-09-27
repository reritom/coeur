from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Callable


class ServiceValidationError(Exception):
    def __init__(self, message: str | None = None, details: dict | None = None):
        self.message = message
        self.details = details
        super().__init__(message)


class _WrappedMethod:
    """A wrapper for the service action registered method. It provides tools
    for overriding the registered validators, useful for testing purposes."""

    def __init__(self, action: ServiceAction, caller: Any):
        self.action = action
        self.caller = caller

    def __call__(self, *args, **kwargs):
        """Call the ServiceAction.__call__, which subsequently calls the actual method"""
        return self.action.run(self.caller, *args, **kwargs)

    @property
    def validators(self) -> list[Callable]:
        """A proxy getter for the action validators"""
        return self.action.validators

    @validators.setter
    def validators(self, validators: list[Callable]):
        """A proxy setter for the action validators"""
        self.action.validators = validators

    @contextmanager
    def only(self, validators: list[str]):
        """A context manager for running only the validators with the given names.

        Note:
            Validator functions with the same names aren't distinguished

        Example:
            class Service:
                @action(validators=[a, b])
                def my_action(self, my_arg):
                    ...

            service = Service()
            with Service().my_action.only([a.__name__]):
                service.my_action(my_arg=my_arg)
        """
        existing = self.validators
        self.validators = [
            existing for existing in existing if existing.__name__ in validators
        ]
        try:
            yield
            self.validators = existing
        except Exception:
            self.validators = existing
            raise

    @contextmanager
    def using(self, validators: list[Callable]):
        """A context manager for calling the action with overridden validators applied to it

        Example:
            class Service:
                @action(validators=[a, b])
                def my_action(self, my_arg):
                    ...

            service = Service()
            with Service().my_action.using([a]):
                service.my_action(my_arg=my_arg)
        """
        existing = self.validators
        self.validators = validators
        try:
            yield
            self.validators = existing
        except Exception:
            self.validators = existing
            raise

    @contextmanager
    def excluding(self, validators: list[str]):
        """A context manager for excluding the given validator names.

        Note:
            Validator functions with the same names aren't distinguished

        Example:
            class Service:
                @action(validators=[a, b])
                def my_action(self, my_arg):
                    ...

            service = Service()
            with Service().my_action.exclude([a.__name__]):
                service.my_action(my_arg=my_arg)
        """
        existing = self.validators
        self.validators = [
            existing for existing in existing if existing.__name__ not in validators
        ]
        try:
            yield
            self.validators = existing
        except Exception:
            self.validators = existing
            raise


class ServiceAction:
    def __init__(
        self,
        registered_method: Callable | None = None,
        validators: list | None = None,
        validator_context_factory: Callable | None = None,
    ):
        """Initialise the service action with any of the given attributes.
        Any attribute not set during initialisation can be set later via decorators"""
        self.registered_method = registered_method
        self.validator_context_factory = validator_context_factory
        self.validators = validators or []

    def __get__(self, obj, objtype=None):
        """The service actions are used in other classes as methods.
        Overriding __get__ allows us to return a reference the registered service action method,
        while passing the other class using this descriptor as the first argument,
        simulating a bound method with self as the first argument.

        Given:

        class MyService:
            @action
            def my_action(self: MyService):
                ...

        Without this __get__ method:

        >>> MyService().my_action
        >>> <ServiceAction object at 0x12345678>

        With this __get__ method:

        >>> MyService().my_action
        >>> <_WrappedMethod object at 0x12344563>

        Then when the wrapped method is called, the registered method is called,
        and the caller is passed as the self parameter.
        """
        return _WrappedMethod(action=self, caller=obj)

    def run(self, caller: Any, *args, **kwargs):
        """Call the registered method (if there is one),
        applying each of the validators in registration order.
        If a context factory is provided, the resulting context will be passed to each validator.

        Raises:
            ValueError: If no method is registered for this action
        """
        if not self.registered_method:
            raise ValueError("Method not set for action")

        if self.validators:

            context = (
                self.validator_context_factory(caller, *args, **kwargs)
                if self.validator_context_factory
                else None
            )

            for validator in self.validators:
                """This is more complex than it seems.

                Decorator registered validators are unbound at registration time, but bind after,
                so the default behaviour of passing the service is fine.

                Validators passed as options are unbound to the given service,
                so the default behaviour of injecting the service is fine.

                Bound validators (from either the service class, or external class instances)
                can be registered afterwards.

                For external bound methods, it is ok to inject service.

                For methods bound to the actions service though,
                it doesn't make sense for python to implicitly pass self
                and then for this method to inject the service again.

                So any bound validator that is bound to the given caller skips the service injection
                and relies on the implicitly self injection.
                """
                self_bound = getattr(validator, "__self__", None) == caller
                validator_args = list(args)
                if context:
                    validator_args.insert(0, context)
                if not self_bound:
                    validator_args.insert(0, caller)

                validator(*validator_args, **kwargs)

        return self.registered_method(caller, *args, **kwargs)

    def __call__(self, caller: Any, *args, **kwargs):
        return self.run(caller=caller, *args, **kwargs)

    def register(self, func: Callable) -> Callable:
        """Register the method that this service action is wrapping

        Raises:
            ValueError: If attempting to register a method when one is already registered
        """
        if self.registered_method:
            raise ValueError("Method already set for action")
        self.registered_method = func
        return func

    def validate(self, func: Callable) -> Callable:
        """Optionally register any additional validators.
        These are executed in order of registration"""
        self.validators.append(func)
        return func

    def validator_context(self, func: Callable) -> Callable:
        """Optionally register a validator context factory.
        This method will be pass all of the provided args and kwargs,
        and the output will be passed to each of the validators.

        The validator context can be used to perform any expensive operations
        that multiple validations require.

        Raises:
            ValueError: If attempting to set a validator context factory when one is already set
        """
        if self.validator_context_factory:
            raise ValueError("Validator context factory already set for action")
        self.validator_context_factory = func
        return func


def action(
    func: Callable | None = None, /, **options
) -> ServiceAction | Callable[[], ServiceAction()]:
    """A decorator for registering a method defined on a class.

    Examples:
        With no options:

            class MyClass:
                @action
                def my_action(self):
                    ...

        With options:

            class MyClass:
                @action(
                    validator_context_factory=make_context,
                    validators=[
                        validator_1,
                        validator_n
                    ]
                )
                def my_action(self):
                    ...
    """
    service_action = ServiceAction(registered_method=func, **options)

    if not func:

        def inner(func) -> ServiceAction:
            service_action.register(func)
            return service_action

        return inner
    return service_action
