from distutils.version import LooseVersion

__version__ = "2.1.1"
__version_info__ = tuple(LooseVersion(__version__).version)


from .service import ServiceAction, ServiceValidationError, action

__all__ = [
    "ServiceAction",
    "action",
    "ServiceValidationError",
]
