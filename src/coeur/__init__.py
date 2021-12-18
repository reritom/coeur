from distutils.version import LooseVersion

__version__ = "1.1.0"
__version_info__ = tuple(LooseVersion(__version__).version)


from .service import (
    PermissionProtocol,
    Service,
    ServiceAction,
    ServiceValidationError,
    action,
)

__all__ = [
    "Service",
    "ServiceAction",
    "action",
    "ServiceValidationError",
    "PermissionProtocol",
]
