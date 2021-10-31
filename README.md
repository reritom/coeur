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


## Service
A Service is class that populates a context using the args at initialisation time. Not necessary to use the Service class to use the ServiceAction class. It just allows the class to be organised slightly differently. Alternatively, a dataclass could be used a service.

Using the Service:
```python
class MyService(Service):
  class Meta:
    @dataclass
    class Context:
      account_id: int = None
      user_id: Optional[int] = None

  action = ActionService("action")
```

Using a dataclass:
```python
@dataclass
class MyService:
  account_id: int = None
  user_id: Optional[int] = None
  action: ClassVar[ActionService] = ActionService("action")
```

Though note the Service child will have the inputs accessible through `service.context`, while the dataclass instance will have the attributes directly accessible through the instance.

## ServiceAction
### Action
A service action is a method on the service that can have any number of validations, and specific permissions set for it.

A service action is defined as a class attribute. The action is then used as a decorator to set the permissions, validators, and the method that will be called.

When the service is called, the permissions will be checked, then each validator will be called in order of definition, and if all of those pass, the action method will be called.

```python
class MyService(Service):
  action = ServiceAction("action")

  @action.permissions
  def get_creation_permissions(self, data):
    return (IsSuperuser,)

  @action.validate
  def validate_creation(self, data):
    # Perform some validation
    ...

  @action.method
  def create_something(self, data):
    # The method that will be called from service.action()
    ...
```

### Permissions
For a given action, permissions can be defined for the specific action using the `@my_action.permission` decorator, which should return a list of permissions to be applied to the method.

Any permission class should have a `check_permission` method that is passed the action call `args` and `kwargs`, and an instance of the service so that the permission check can refer to the service context.

```python
class IsAuthenticated:
  def check_permission(self, service, *args, **kwargs):
    if not service.context.user:
      raise PermissionError()
```

If not permissions are explicitly set for the action, any service level permissions will be used that have been defined on `MyService.permissions: List[Permission]`.

In usecases where there may not be a direct user, the permissions can either be explicitly set to an empty tuple, or the action can be marked as permission-less (`action = ServiceAction("action", use_service_permissions=False)`), but the service will still need to be instantiated based on the Meta.Args.


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
class OrderService(Service):
  @create.validate
  def validate_order_creation(self, data: dict):
    OrderMarshmallowSchema().load(data)
```
