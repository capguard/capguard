"""CapGuard core module - foundational security primitives."""

from ..models import CapabilityToken, ToolDefinition, ToolParameter, AuditLogEntry
from .registry import ToolRegistry, create_tool_definition
from .classifier import IntentClassifier
from .enforcer import CapabilityEnforcer
from .exceptions import (
    CapGuardError,
    PermissionDeniedError,
    ConstraintViolationError,
    ToolNotFoundError,
    ToolAlreadyRegisteredError,
    ClassificationError
)

__all__ = [
    # Models
    'CapabilityToken',
    'ToolDefinition',
    'ToolParameter',
    'AuditLogEntry',
    
    # Core classes
    'ToolRegistry',
    'IntentClassifier',
    'CapabilityEnforcer',
    
    # Helpers
    'create_tool_definition',
    
    # Exceptions
    'CapGuardError',
    'PermissionDeniedError',
    'ConstraintViolationError',
    'ToolNotFoundError',
    'ToolAlreadyRegisteredError',
    'ClassificationError',
]
