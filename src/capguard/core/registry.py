"""Tool registry for managing available agent tools."""

from typing import Callable, Optional, Dict
from .models import ToolDefinition, ToolParameter
from .exceptions import ToolNotFoundError, ToolAlreadyRegisteredError


class ToolRegistry:
    """
    Central registry for all tools available to agents.
    
    Manages tool definitions (metadata) and implementations (functions).
    Used by both classifier (to know available tools) and enforcer (to execute).
    """
    
    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        self._definitions: Dict[str, ToolDefinition] = {}
    
    def register(
        self,
        definition: ToolDefinition,
        func: Callable,
        overwrite: bool = False
    ) -> None:
        """
        Register a new tool.
        
        Args:
            definition: Tool metadata (name, description, risk level, etc.)
            func: The actual function to execute
            overwrite: Allow overwriting existing tools (default: False)
            
        Raises:
            ToolAlreadyRegisteredError: If tool exists and overwrite=False
        """
        if definition.name in self._tools and not overwrite:
            raise ToolAlreadyRegisteredError(
                f"Tool '{definition.name}' already registered. "
                f"Use overwrite=True to replace."
            )
        
        self._tools[definition.name] = func
        self._definitions[definition.name] = definition
    
    def get_tool(self, name: str) -> Optional[Callable]:
        """Get tool implementation by name."""
        return self._tools.get(name)
    
    def get_definition(self, name: str) -> Optional[ToolDefinition]:
        """Get tool definition by name."""
        return self._definitions.get(name)
    
    def list_tools(self) -> list[str]:
        """List all registered tool names."""
        return list(self._tools.keys())
    
    def get_all_definitions(self) -> Dict[str, ToolDefinition]:
        """Get all tool definitions (useful for classifiers)."""
        return self._definitions.copy()
    
    def unregister(self, name: str) -> None:
        """
        Unregister a tool.
        
        Args:
            name: Tool name to remove
            
        Raises:
            ToolNotFoundError: If tool doesn't exist
        """
        if name not in self._tools:
            raise ToolNotFoundError(f"Tool '{name}' not registered")
        
        del self._tools[name]
        del self._definitions[name]
    
    def __len__(self) -> int:
        """Number of registered tools."""
        return len(self._tools)
    
    def __contains__(self, name: str) -> bool:
        """Check if tool is registered."""
        return name in self._tools
    
    def __repr__(self) -> str:
        return f"ToolRegistry(tools={len(self)} registered)"


def create_tool_definition(
    name: str,
    description: str,
    risk_level: int,
    parameters: Optional[list[dict]] = None,
    requires_confirmation: bool = False
) -> ToolDefinition:
    """
    Convenience function to create a ToolDefinition.
    
    Example:
        >>> definition = create_tool_definition(
        ...     name="send_email",
        ...     description="Send an email",
        ...     risk_level=4,
        ...     parameters=[
        ...         {"name": "to", "type": "str", "description": "Recipient", "required": True}
        ...     ]
        ... )
    """
    if parameters is None:
        parameters = []
    
    param_models = [ToolParameter(**p) for p in parameters]
    
    return ToolDefinition(
        name=name,
        description=description,
        parameters=param_models,
        risk_level=risk_level,
        requires_confirmation=requires_confirmation
    )
