from distutils.version import LooseVersion


__version__ = "0.0.1"
__version_info__ = tuple(LooseVersion(__version__).version)


from .service import Service, ServiceAction, ServiceValidationError, PermissionProtocol

__all__ = ["Service", "ServiceAction", "ServiceValidationError", "PermissionProtocol"]
