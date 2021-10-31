from distutils.version import LooseVersion

__version__ = "0.0.1b"
__version_info__ = tuple(LooseVersion(__version__).version)


from .service import PermissionProtocol, Service, ServiceAction, ServiceValidationError

__all__ = ["Service", "ServiceAction", "ServiceValidationError", "PermissionProtocol"]
