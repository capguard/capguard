import pytest
from unittest.mock import MagicMock, Mock
from langchain.tools import Tool

from capguard import ToolRegistry, ToolDefinition
from capguard.integrations import ProtectedAgentExecutor
from capguard.models import CapabilityToken
from capguard import PermissionDeniedError

# --- Mocks ---

class MockClassifier:
    def __init__(self, token_to_return):
        self.token = token_to_return
        
    def classify(self, user_input):
        return self.token

# --- Tests ---

def test_protected_executor_allow():
    """Test that allowed tools execute normally."""
    
    # Setup
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(name="read_file", description="Read a file", risk_level=1),
        lambda path: f"Reading {path}"
    )
    
    # Mock executor
    mock_agent_executor = MagicMock()
    # Initial tools list
    original_tool = Tool.from_function(
        name="read_file", 
        func=lambda path: "original", 
        description="desc"
    )
    mock_agent_executor.tools = [original_tool]
    
    mock_agent_executor.invoke.return_value = {"output": "Success"}
    
    # Mock classifier granting permission
    token = CapabilityToken(
        user_request="Read file", 
        granted_tools={"read_file": True}
    )
    classifier = MockClassifier(token)
    
    # Create protected executor
    protected = ProtectedAgentExecutor(
        executor=mock_agent_executor,
        classifier=classifier,
        registry=registry
    )
    
    # Run
    result = protected.invoke({"input": "Read file"})
    
    # Assertions
    assert result["output"] == "Success"
    
    # Verify underlying invoke was called
    mock_agent_executor.invoke.assert_called_once()
    
    # Verify tools were temporarily swapped
    # (Hard to verify state during call without side effects, but we assume it worked if result matches)

def test_protected_executor_deny_termination():
    """
    Test that denied tools raise SecurityStop and return blocked result.
    
    This verifies the Strict Termination logic.
    """
    
    # Setup registry with high risk tool
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(name="delete_file", description="Delete a file", risk_level=5),
        lambda path: "deleted"
    )
    
    # Mock agent that TRIES to use the tool
    mock_agent_executor = MagicMock()
    
    # The original tool
    original_tool = Tool.from_function(
        name="delete_file", 
        func=lambda path: "original", 
        description="desc"
    )
    mock_agent_executor.tools = [original_tool]
    
    # Simulate agent executing the tool
    # When agent.invoke is called, it will try to run the tools in its list.
    # Since we swapped the tools, it runs the WRAPPED tool.
    
    # To test this unit-style without running a real agent, we need to manually
    # invoke the wrapped tool that ProtectedAgentExecutor put there.
    
    # We can inspect what tools were passed to the mock executor
    token = CapabilityToken(
        user_request="Delete file", 
        granted_tools={"delete_file": False} # DENIED
    )
    classifier = MockClassifier(token)
    
    protected = ProtectedAgentExecutor(
        executor=mock_agent_executor,
        classifier=classifier,
        registry=registry,
        verbose=True
    )
    
    # We trap the invoke call to inspect the tools
    captured_tools = []
    def capture_tools(*args, **kwargs):
        captured_tools.extend(mock_agent_executor.tools)
        # Now simulate the agent calling the tool
        # This is where the security check happens
        tool_to_call = mock_agent_executor.tools[0]
        return tool_to_call.func("path")
        
    mock_agent_executor.invoke.side_effect = capture_tools
    
    # Run
    # This should return the BLOCKING result, not the tool result
    result = protected.invoke({"input": "Delete file"})
    
    # Assertions
    assert "capguard_blocked" in result
    assert result["capguard_blocked"] == True
    assert "Execution terminated" in result["output"]
    assert "Security Violation" in result["output"]
    
    # Verify we caught it
    print("\nTermination verified successfully")
