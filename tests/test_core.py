import pytest
from datetime import datetime
from capguard.models import CapabilityToken, ToolDefinition, ToolParameter, AuditLogEntry
from capguard.core.registry import ToolRegistry, create_tool_definition
from capguard.core.enforcer import CapabilityEnforcer
from capguard import PermissionDeniedError, ToolNotFoundError, ToolAlreadyRegisteredError

# --- Fixtures ---

@pytest.fixture
def empty_registry():
    return ToolRegistry()

@pytest.fixture
def populated_registry():
    registry = ToolRegistry()
    registry.register(
        create_tool_definition(
            name="read_file",
            description="Read a file",
            risk_level=2,
            parameters=[{"name": "path", "type": "str", "description": "File path"}]
        ),
        lambda path: f"Content of {path}"
    )
    registry.register(
        create_tool_definition(
            name="delete_file",
            description="Delete a file",
            risk_level=5,
            parameters=[{"name": "path", "type": "str", "description": "File path"}]
        ),
        lambda path: f"Deleted {path}"
    )
    return registry

@pytest.fixture
def enforcer(populated_registry):
    return CapabilityEnforcer(populated_registry)

# --- Registry Tests ---

def test_registry_registration(empty_registry):
    def dummy_tool(): pass
    defn = create_tool_definition("test_tool", "Description", 1)
    
    empty_registry.register(defn, dummy_tool)
    assert "test_tool" in empty_registry
    assert len(empty_registry) == 1
    assert empty_registry.get_tool("test_tool") == dummy_tool

def test_registry_duplicate_error(empty_registry):
    def dummy(): pass
    defn = create_tool_definition("tool", "Desc", 1)
    empty_registry.register(defn, dummy)
    
    with pytest.raises(ToolAlreadyRegisteredError):
        empty_registry.register(defn, dummy)

def test_registry_overwrite(empty_registry):
    def dummy1(): return 1
    def dummy2(): return 2
    defn = create_tool_definition("tool", "Desc", 1)
    
    empty_registry.register(defn, dummy1)
    empty_registry.register(defn, dummy2, overwrite=True)
    
    assert empty_registry.get_tool("tool")() == 2

# --- Enforcer Tests ---

def test_enforcer_allow(enforcer):
    token = CapabilityToken(
        user_request="Read file",
        granted_tools={"read_file": True}
    )
    
    result = enforcer.execute_tool("read_file", token, path="test.txt")
    assert result == "Content of test.txt"
    
    log = enforcer.get_audit_log()
    assert len(log) == 1
    assert log[0].action == "executed"

def test_enforcer_deny(enforcer):
    token = CapabilityToken(
        user_request="Read file",
        granted_tools={"read_file": True, "delete_file": False}
    )
    
    with pytest.raises(PermissionDeniedError):
        enforcer.execute_tool("delete_file", token, path="test.txt")
        
    blocked = enforcer.get_blocked_attempts()
    assert len(blocked) == 1
    assert blocked[0].tool_name == "delete_file"
    assert blocked[0].potential_attack == True

def test_enforcer_explicit_deny_missing_tool(enforcer):
    # Tool not in granted_tools at all -> implies denied
    token = CapabilityToken(
        user_request="Read file", 
        granted_tools={"read_file": True}
    )
    
    with pytest.raises(PermissionDeniedError):
        enforcer.execute_tool("delete_file", token, path="t.txt")

def test_enforcer_tool_not_found(enforcer):
    token = CapabilityToken(user_request="x", granted_tools={"missing": True})
    
    with pytest.raises(ToolNotFoundError):
        enforcer.execute_tool("missing", token)
