"""
CapGuard: Capability-based security for LLM agents.

Prevents prompt injection attacks with architectural guarantees.
"""

__version__ = "0.1.0"

from .core import (
    # Models
    CapabilityToken,
    ToolDefinition,
    ToolParameter,
    AuditLogEntry,
    
    # Core classes
    ToolRegistry,
    IntentClassifier,
    CapabilityEnforcer,
    
    # Helpers
    create_tool_definition,
    
    # Exceptions
    CapGuardError,
    PermissionDeniedError,
    ConstraintViolationError,
    ToolNotFoundError,
    ToolAlreadyRegisteredError,
    ClassificationError,
)

from .classifiers import (
    RuleBasedClassifier,
    create_default_rules,
)

__all__ = [
    # Version
    '__version__',
    
    # Models
    'CapabilityToken',
    'ToolDefinition',
    'ToolParameter',
    'AuditLogEntry',
    
    # Core
    'ToolRegistry',
    'IntentClassifier',
    'CapabilityEnforcer',
    'create_tool_definition',
    
    # Classifiers
    'RuleBasedClassifier',
    'create_default_rules',
    
    # Exceptions
    'CapGuardError',
    'PermissionDeniedError',
    'ConstraintViolationError',
    'ToolNotFoundError',
    'ToolAlreadyRegisteredError',
    'ClassificationError',
]
