# simple-services
Simple service framework for python applications.

## Introduction
When creating python based applications, there is typically some core business logic. There are countless ways to organise this logic, including by using functions, or by building the business logic into other frameworks. For example, in a Flask application one may put the business logic directly into a `View`, or in Django Rest Framework, one might put the business logic into the `Serializer`.

For smaller applications, coupling the business logic with the main framework you are using isn't problematic, but in larger applications it can become a limitation. For example, if you have a single interface to the business logic that is a REST API, then having the business logic in the views/serializers isn't problematic, but if your application grows and you end up having CLIs, or celery workers that also need to interface with the business logic, then the business logic can't be coupled with the framework used by one of the interfaces.

The purpose of this library is to a create a service framework that allows the different interfaces to consume the core business logic.

Practically speaking, the Flask and DRF examples would be as follows:
- Flask: View will call the Service
- DRF: ViewSet will either call the Service, or will call a Serializer that calls the Service
- Celery: Task will call the service directly


## ServiceAction
### Permissions


In usecases where there may not be a direct user, the permissions can either be explicitly set to an empty tuple, or the action can be marked as permission-less, but the service will still need to be instanciated based on the Meta.Args


### Validators
A service action can have multiple validators, defined using:
```
@my_action.validate
def my_validation_function(self, data):
  # Perform the validation
  ...
  return data
```
The validators are called in the order of definition, and the validation function must return the validated data. The reasoning behind this is that the framework can work in conjunction with more powerful validation specific libraries such as `Marshmallow`, and in those cases, the validation schema can also be used to load the data into a model. In those cases, by returning the validated data, it prevents the service layer from duplicating the data validation and loading.

For example:
```
class OrderService(Service):
  @create.validate
  def validate_order_creation(self, data: dict) -> Order:
    order = OrderMarshmallowSchema().load(data)
    return order
```
