"""
CapGuard decorators for easy tool registration.

Usage:
    from langchain.tools import tool
    from capguard.decorators import capguard_tool
    
    @tool
    @capguard_tool(risk_level=4)
    def send_email(to: str, subject: str, body: str) -> str:
        '''Send an email'''
        return send_email_impl(to, subject, body)
"""

import inspect
from typing import Callable, Optional
from functools import wraps

from .core import ToolRegistry, ToolDefinition, ToolParameter


# Global registry for decorated tools
_global_registry = ToolRegistry()


def get_global_registry() -> ToolRegistry:
    """Get the global tool registry populated by @capguard_tool decorators."""
    return _global_registry


def capguard_tool(
    risk_level: int,
    description: Optional[str] = None
) -> Callable:
    """
    Decorator that auto-registers a tool with CapGuard.
    
    This decorator:
    1. Extracts function metadata (name, params, docstring)
    2. Registers the tool with a global CapGuard registry
    3. Returns the original function unchanged
    
    Args:
        risk_level: Risk level (1-5) where 1=safe, 5=critical
        description: Optional description (defaults to function docstring)
    
    Example:
        @tool  # LangChain decorator
        @capguard_tool(risk_level=2)
        def read_website(url: str) -> str:
            '''Fetch and read content from URL'''
            return requests.get(url).text
    
    The decorated function works exactly as before, but is now
    registered with CapGuard for permission enforcement.
    """
    def decorator(func: Callable) -> Callable:
        # Extract function metadata
        func_name = func.__name__
        func_description = description or func.__doc__ or f"{func_name} function"
        
        # Extract parameters from function signature
        sig = inspect.signature(func)
        parameters = []
        
        for param_name, param in sig.parameters.items():
            # Skip *args, **kwargs
            if param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
                continue
            
            # Determine type
            param_type = "string"  # Default
            if param.annotation != inspect.Parameter.empty:
                annotation = param.annotation
                if annotation == int:
                    param_type = "integer"
                elif annotation == float:
                    param_type = "number"
                elif annotation == bool:
                    param_type = "boolean"
                elif annotation == str:
                    param_type = "string"
                else:
                    param_type = str(annotation)
            
            parameters.append(ToolParameter(
                name=param_name,
                type=param_type,
                description=f"{param_name} parameter",
                required=(param.default == inspect.Parameter.empty)
            ))
        
        # Register with global registry
        _global_registry.register(
            ToolDefinition(
                name=func_name,
                description=func_description.strip(),
                parameters=parameters,
                risk_level=risk_level
            ),
            func
        )
        
        # Return function unchanged (transparent to caller)
        return func
    
    return decorator


def reset_global_registry():
    """Reset the global registry. Useful for testing."""
    global _global_registry
    _global_registry = ToolRegistry()
