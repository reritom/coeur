from __future__ import annotations

from functools import wraps
import inspect
from typing import Any, Callable, Optional


class ServiceValidationError(Exception):
    def __init__(self, message: str | None = None, details: dict | None = None):
        self.message = message
        self.details = details
        super().__init__(message)


class ServiceAction:
    def __init__(
        self,
        method: Callable | None = None,
        validators: Optional[list] = None,
        validator_context_factory: Optional[Callable] = None,
    ):
        """Initialise the service action with any of the given attributes. Any attribute not set during
        initialisation can be set later via decorators"""
        self.method = method
        self.validator_context_factory = validator_context_factory
        self.validators = validators or []

    def __get__(self, obj, objtype=None):
        """The service actions used in other classes as methods, overriding __get__ allows one
        to return a reference the registered service action method, while passing the other class
        using this descriptor as the first argument, simulating a bound method with self as the first
        argument.

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
        >>> <function ServiceAction.__call__ at 0x12344563>

        Then when the function is called, the registered method is called, and the caller is passed as the self parameter.
        """

        @wraps(self.__call__)
        def wrapper(*args, **kwargs):
            return self.__call__(obj, *args, **kwargs)

        # Allow a more direct way to reference the service action from the method
        # Else one would need to do MyClass().my_action.__wrapped__.__self__
        wrapper.action = self

        wrapper.__signature__ = inspect.signature(self.method)
        return wrapper

    def __call__(self, service: Any, *args, **kwargs):
        """Call the registered method (if there is one), applying each of the validators in registration order.
        If a context factory is provided, the resulting context will be passed to each validator"""
        if not self.method:
            raise ValueError("Method not set for actiom")

        context = (
            self.validator_context_factory(service, *args, **kwargs)
            if self.validator_context_factory
            else None
        )

        for validator in self.validators:
            validator(service, context, *args, **kwargs) if context else validator(
                service, *args, **kwargs
            )

        return self.method(service, *args, **kwargs)

    def register(self, func: Callable) -> Callable:
        """Register the method that this service action is wrapping"""
        if self.method:
            raise ValueError("Method already set for action")
        self.method = func
        return func

    def validate(self, func: Callable) -> Callable:
        """Optionally register any additional validators. These are executed in order of registration"""
        self.validators.append(func)
        return func

    def validator_context(self, func: Callable) -> Callable:
        """Optionally register a validator context factory. This method will be pass all of the provided
        args and kwargs, and the output will be passed to each of the validators.

        The validator context can be used to perform any expensive operations that multiple validations require."""
        if self.validator_context_factory:
            raise ValueError("Validator context factory already set for action")
        self.validator_context_factory = func
        return func


def action(
    func: Callable | None = None, /, **options
) -> ServiceAction | Callable[[Callable], ServiceAction]:
    """A decorator for registering a method defined on a class.

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
    service_action = ServiceAction(method=func, **options)
    if not func:

        def inner(func):
            service_action.register(func)
            return service_action

        return inner
    return service_action
