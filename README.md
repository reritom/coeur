# Coeur
A simple service framework for python applications.

## Introduction
When creating python based applications, there is typically some core business logic. There are countless ways to organise this logic, including by using functions, or by building the business logic into other frameworks. For example, in a Flask application one may put the business logic directly into a `View`, or in Django Rest Framework, one might put the business logic into the `Serializer`.

For smaller applications, coupling the business logic with the main framework you are using isn't problematic, but in larger applications it can become a limitation. For example, if you have a single interface to the business logic that is a REST API, then having the business logic in the views/serializers isn't problematic, but if your application grows and you end up having CLIs, or celery workers that also need to interface with the business logic, then the business logic can't be coupled with the framework used by one of the interfaces.

The purpose of this library is to a create a service framework that allows the different interfaces to consume the core business logic.

Practically speaking, the Flask and DRF examples would be as follows:
- Flask: View will call the Service
- DRF: ViewSet will either call the Service, or will call a Serializer that calls the Service
- Celery: Task will call the service directly


## ServiceAction
### Action
A service action is a method on a service that can have any number of validations.

A service action is defined as a class attribute. The action is then used as a decorator to set the permissions, validators, and the method that will be called.

When the service is called, the permissions will be checked, then each validator will be called in order of definition, and if all of those pass, the action method will be called.

```python
class MyService:
    @action
    def create_something(self, data):
        # The method that will be called from service.action()
        ...

    # Optionally specify a validator context factory
    @action.validator_context
    def make_context(self, data):
        # The return value will be passed to each validator
        return MyContext()

    @create_something.validate
    def validate_creation(self, context, data):
        # Perform some validation
        ...
```
The action can be initialised with validators directly, or any combination thereof.
```python
class MyService:
    @action(
        validator_context_factory=make_context,
        validators=[validate_something]
    )
    def create_something(self, data):
        # The method that will be called from service.action()
        ...
```

### Validators
A service action can have multiple validators, defined using:
```python
@my_action.validate
def my_validation_function(self, data):
    # Perform the validation
    ...
```
The validators are called in the order of definition, and the validation function shouldn't mutate the data (any returned value is be discarded). The framework can work in conjunction with more powerful validation specific libraries such as `Marshmallow`, for example:
```python
class OrderService:
    @action
    def create(self, data: dict):
        # Do something

    @create.validate
    def validate_order_creation(self, data: dict):
        OrderMarshmallowSchema().load(data)
```
