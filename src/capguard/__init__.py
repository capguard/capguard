"""
CapGuard: Capability-based security for LLM agents.

Prevents prompt injection attacks with architectural guarantees.
"""

__version__ = "0.1.6"

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
    LLMClassifier,
    create_default_rules,
)

from .decorators import (
    capguard_tool,
    get_global_registry,
    reset_global_registry,
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
    'LLMClassifier',
    'create_default_rules',
    
    # Decorators
    'capguard_tool',
    'get_global_registry',
    'reset_global_registry',
    
    # Exceptions
    'CapGuardError',
    'PermissionDeniedError',
    'ConstraintViolationError',
    'ToolNotFoundError',
    'ToolAlreadyRegisteredError',
    'ClassificationError',
]
