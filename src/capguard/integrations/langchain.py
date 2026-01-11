"""
LangChain integration for CapGuard.

Provides ProtectedAgentExecutor - a drop-in wrapper for LangChain's AgentExecutor
that adds CapGuard protection with minimal code changes.
"""

from typing import Any, Dict, Optional


from ..core import ToolRegistry, CapabilityEnforcer, PermissionDeniedError
from ..core.classifier import IntentClassifier
from ..decorators import get_global_registry


class ProtectedAgentExecutor:
    """
    Drop-in wrapper for LangChain AgentExecutor that adds CapGuard protection.
    
    This wrapper:
    1. Intercepts invoke() calls
    2. Classifies user intent before agent execution
    3. Restricts tools to only those granted by classifier
    4. Enforces permissions on tool calls
    
    Usage:
        # Your existing agent
        executor = AgentExecutor(agent=agent, tools=tools)
        
        # Wrap with CapGuard (5 lines)
        from capguard.integrations import ProtectedAgentExecutor
        from capguard.classifiers import LLMClassifier
        
        protected_executor = ProtectedAgentExecutor(
            executor,
            classifier=LLMClassifier(model="gpt-4")
        )
        
        # Use exactly the same API
        result = protected_executor.invoke({"input": "Summarize URL"})
    
    The agent never knows it's restricted - tools are filtered before execution.
    """
    
    def __init__(
        self,
        executor,  # LangChain AgentExecutor (no type hint to avoid import)
        classifier: IntentClassifier,
        registry: Optional[ToolRegistry] = None,
        verbose: bool = False
    ):
        """
        Initialize protected executor.
        
        Args:
            executor: Existing LangChain AgentExecutor
            classifier: CapGuard classifier (LLMClassifier, RuleBasedClassifier, etc.)
            registry: Tool registry (defaults to global registry from decorators)
            verbose: If True, print CapGuard decisions
        """
        self.executor = executor
        self.classifier = classifier
        self.registry = registry or get_global_registry()
        self.enforcer = CapabilityEnforcer(self.registry)
        self.verbose = verbose
        
        # Store original tools
        self.all_tools = list(executor.tools)
    
    class SecurityStop(BaseException):
        """Special exception to immediately stop agent execution on security violation."""
        pass

    def invoke(self, inputs: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        Execute agent with CapGuard protection.
        
        Same API as AgentExecutor.invoke(), but with these steps:
        1. Extract user request from inputs
        2. Classify → get capability token
        3. Wrap ALL tools (granted=execute, denied=block)
        4. Run executor
        5. Catch SecurityStop to terminate immediately
        """
        # Extract user input
        user_input = inputs.get("input", "")
        if not user_input:
            raise ValueError("No 'input' key found in inputs dict")
        
        if self.verbose:
            print(f"\n[CapGuard] User Request: {user_input}")
        
        # Step 1: Classify intent
        if self.verbose:
            print("[CapGuard] Classifying intent...")
        
        token = self.classifier.classify(user_input)
        
        if self.verbose:
            granted = [name for name, g in token.granted_tools.items() if g]
            denied = [name for name, g in token.granted_tools.items() if not g]
            print(f"[CapGuard] ✓ Granted: {granted}")
            print(f"[CapGuard] ✗ Denied: {denied}")
        
        # Step 2: Create wrapped tool set (ALL tools wrapped)
        # We do NOT filter tools out anymore, so the agent sees them but they are blocked.
        wrapped_tools = []
        
        for tool in self.all_tools:
            wrapped_tool = self._wrap_tool(tool, token)
            wrapped_tools.append(wrapped_tool)
        
        # Step 3: Temporarily replace tools in executor
        original_tools = self.executor.tools
        original_agent_tools = getattr(self.executor.agent, 'tools', None)
        
        self.executor.tools = wrapped_tools
        if original_agent_tools is not None:
            self.executor.agent.tools = wrapped_tools
        
        try:
            # Step 4: Run executor
            if self.verbose:
                print("[CapGuard] Executing agent...\n")
            
            result = self.executor.invoke(inputs, **kwargs)
            return result
            
        except self.SecurityStop as e:
            # Step 5: Handle security termination
            print("\n[CapGuard] 🛑 SECURITY VIOLATION DETECTED 🛑")
            print(f"[CapGuard] Incident: {e}")
            print("[CapGuard] Action: Terminating agent execution immediately.")
            return {
                "output": f"Security Violation: {e}. Execution terminated by CapGuard.",
                "capguard_blocked": True
            }
            
        finally:
            # Step 6: Restore original tools
            self.executor.tools = original_tools
            if original_agent_tools is not None:
                self.executor.agent.tools = original_tools
    
    def _wrap_tool(self, langchain_tool, token):
        """
        Wrap a LangChain tool to enforce CapGuard permissions.
        """
        # Lazy import
        from langchain.tools import Tool
        
        tool_name = langchain_tool.name
        
        def guarded_func(*args, **kwargs):
            """
            Wrapper function that enforces permissions.
            """
            # Helper to map args to kwargs
            if args and not kwargs:
                definition = self.registry.get_definition(tool_name)
                if definition and len(args) == 1 and len(definition.parameters) == 1:
                    kwargs = {definition.parameters[0].name: args[0]}
                elif definition and len(args) == len(definition.parameters):
                    kwargs = {p.name: arg for p, arg in zip(definition.parameters, args)}
            
            try:
                # Execute through enforcer (checks token)
                return self.enforcer.execute_tool(tool_name, token, **kwargs)
                
            except PermissionDeniedError:
                # Attack blocked! Raise SecurityStop to kill the agent loop
                msg = f"Unauthorized access to tool '{tool_name}' blocked."
                if self.verbose:
                    definition = self.registry.get_definition(tool_name)
                    risk_level = definition.risk_level if definition else "Unknown"
                    print(f"\n[CapGuard] ⛔ BLOCKED: {tool_name} (Risk Level: {risk_level})")
                    print("[CapGuard] Reason: Tool not granted in capabilities token.")
                
                # We raise BaseException to bypass LangChain's try/except Exception blocks
                raise self.SecurityStop(msg)
                
            except Exception as e:
                # Other errors
                return f"Error executing {tool_name}: {e}"
        
        # Create new Tool
        return Tool.from_function(
            name=langchain_tool.name,
            func=guarded_func,
            description=langchain_tool.description
        )
    
    def __getattr__(self, name):
        """Proxy other attributes to underlying executor."""
        return getattr(self.executor, name)
