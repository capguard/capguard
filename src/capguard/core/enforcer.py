"""Capability enforcer - enforces capability tokens at runtime."""

from typing import Any, Dict, List
from ..models import CapabilityToken, AuditLogEntry
from .registry import ToolRegistry
from .exceptions import PermissionDeniedError, ConstraintViolationError, ToolNotFoundError


class CapabilityEnforcer:
    """
    Enforces capability tokens at runtime.
    
    This is where the architectural security guarantee happens:
    Even if an agent is compromised and tries to use unauthorized tools,
    this enforcer will block the attempt programmatically.
    """
    
    def __init__(self, tool_registry: ToolRegistry):
        """
        Initialize enforcer.
        
        Args:
            tool_registry: Registry of available tools
        """
        self.registry = tool_registry
        self.audit_log: List[AuditLogEntry] = []
    
    def execute_tool(
        self,
        tool_name: str,
        capability_token: CapabilityToken,
        **kwargs
    ) -> Any:
        """
        Execute a tool if granted in capability token.
        
        Args:
            tool_name: Name of tool to execute
            capability_token: Token from classifier
            **kwargs: Tool parameters
            
        Returns:
            Tool execution result
            
        Raises:
            PermissionDeniedError: If tool not granted
            ConstraintViolationError: If parameters violate constraints
            ToolNotFoundError: If tool doesn't exist
            
        Example:
            >>> token = CapabilityToken(granted_tools={"read_website": True})
            >>> enforcer.execute_tool("read_website", token, url="http://example.com")
            "Website content..."
            
            >>> enforcer.execute_tool("send_email", token, to="attacker@evil.com")
            PermissionDeniedError: Tool 'send_email' not granted
        """
        # 1. Check if tool is granted
        if not capability_token.granted_tools.get(tool_name, False):
            self._log_blocked_attempt(tool_name, capability_token, kwargs)
            raise PermissionDeniedError(
                f"Tool '{tool_name}' not granted in capability token. "
                f"Request: '{capability_token.user_request}'"
            )
        
        # 2. Validate constraints
        self._validate_constraints(tool_name, capability_token, kwargs)
        
        # 3. Get tool function
        tool_func = self.registry.get_tool(tool_name)
        if tool_func is None:
            raise ToolNotFoundError(
                f"Tool '{tool_name}' not found in registry"
            )
        
        # 4. Execute
        try:
            result = tool_func(**kwargs)
            self._log_execution(tool_name, capability_token, kwargs, result)
            return result
        except Exception as e:
            self._log_failure(tool_name, capability_token, kwargs, str(e))
            raise
    
    def _validate_constraints(
        self,
        tool_name: str,
        token: CapabilityToken,
        kwargs: Dict[str, Any]
    ) -> None:
        """
        Validate tool parameters against constraints.
        
        Constraints are tool-specific rules, e.g.:
        - send_email: recipient must be in whitelist
        - read_file: path must be in allowed directories
        """
        constraints = token.constraints.get(tool_name, {})
        
        if not constraints:
            return  # No constraints to validate
        
        # Example constraint: email recipient whitelist
        if tool_name == "send_email":
            whitelist = constraints.get("recipient_whitelist", [])
            if whitelist:
                recipient = kwargs.get("to")
                if recipient not in whitelist:
                    raise ConstraintViolationError(
                        f"Recipient '{recipient}' not in whitelist: {whitelist}"
                    )
        
        # Example: file path whitelist
        if tool_name == "read_file":
            allowed_paths = constraints.get("path_whitelist", [])
            if allowed_paths:
                path = kwargs.get("path")
                if not any(path.startswith(allowed) for allowed in allowed_paths):
                    raise ConstraintViolationError(
                        f"Path '{path}' not in whitelist: {allowed_paths}"
                    )
        
        # Add more constraint validators as needed
    
    def _log_blocked_attempt(
        self,
        tool_name: str,
        token: CapabilityToken,
        parameters: Dict[str, Any]
    ) -> None:
        """Log a blocked tool attempt (potential attack)."""
        entry = AuditLogEntry(
            request_id=token.request_id,
            tool_name=tool_name,
            action="blocked",
            capability_token=token,
            parameters=parameters,
            potential_attack=True  # Flag for security review
        )
        self.audit_log.append(entry)
    
    def _log_execution(
        self,
        tool_name: str,
        token: CapabilityToken,
        parameters: Dict[str, Any],
        result: Any
    ) -> None:
        """Log successful tool execution."""
        entry = AuditLogEntry(
            request_id=token.request_id,
            tool_name=tool_name,
            action="executed",
            capability_token=token,
            parameters=parameters,
            result=str(result)[:200]  # Truncate long results
        )
        self.audit_log.append(entry)
    
    def _log_failure(
        self,
        tool_name: str,
        token: CapabilityToken,
        parameters: Dict[str, Any],
        error: str
    ) -> None:
        """Log failed tool execution."""
        entry = AuditLogEntry(
            request_id=token.request_id,
            tool_name=tool_name,
            action="failed",
            capability_token=token,
            parameters=parameters,
            error=error
        )
        self.audit_log.append(entry)
    
    def get_audit_log(self) -> List[AuditLogEntry]:
        """Get complete audit log."""
        return self.audit_log.copy()
    
    def get_blocked_attempts(self) -> List[AuditLogEntry]:
        """Get only blocked attempts (potential attacks)."""
        return [entry for entry in self.audit_log if entry.action == "blocked"]
    
    def clear_audit_log(self) -> None:
        """Clear audit log (use with caution)."""
        self.audit_log.clear()
