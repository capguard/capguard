"""Custom exceptions for CapGuard."""


class CapGuardError(Exception):
    """Base exception for all CapGuard errors."""
    pass


class PermissionDeniedError(CapGuardError):
    """
    Raised when a tool is requested but not granted in capability token.
    
    This is the PRIMARY security enforcementmechanism - if this is raised,
    an attack attempt was likely blocked.
    """
    pass


class ConstraintViolationError(CapGuardError):
    """
    Raised when tool parameters violate constraints.
    
    Example: Trying to email someone not on the whitelist.
    """
    pass


class ToolNotFoundError(CapGuardError):
    """Raised when trying to execute a tool that doesn't exist."""
    pass


class ToolAlreadyRegisteredError(CapGuardError):
    """Raised when trying to register a tool that already exists."""
    pass


class ClassificationError(CapGuardError):
    """Raised when classifier fails to determine capabilities."""
    pass
