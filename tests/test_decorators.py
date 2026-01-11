import pytest
from capguard import capguard_tool, get_global_registry, reset_global_registry
from capguard.core.registry import ToolRegistry

@pytest.fixture(autouse=True)
def clean_registry():
    """Reset registry before each test."""
    reset_global_registry()
    yield
    reset_global_registry()

def test_decorator_registration():
    """Test that @capguard_tool registers the function."""
    
    @capguard_tool(risk_level=3)
    def my_tool(x: int) -> int:
        """My tool description."""
        return x * 2
        
    registry = get_global_registry()
    assert "my_tool" in registry
    
    defn = registry.get_definition("my_tool")
    assert defn.name == "my_tool"
    assert defn.description == "My tool description."
    assert defn.risk_level == 3
    
    # Check execution
    implementation = registry.get_implementation("my_tool")
    assert implementation(5) == 10

def test_decorator_parameter_extraction():
    """Test that parameters are correctly extracted from type hints."""
    
    @capguard_tool(risk_level=1)
    def complex_tool(
        name: str, 
        age: int, 
        active: bool = True
    ) -> str:
        """Process user."""
        return "done"
        
    registry = get_global_registry()
    defn = registry.get_definition("complex_tool")
    
    params = {p.name: p for p in defn.parameters}
    assert "name" in params
    assert params["name"].type == "string"  # Mapped from str
    
    assert "age" in params
    assert params["age"].type == "integer"  # Mapped from int
    
    assert "active" in params
    assert params["active"].type == "boolean" # Mapped from bool

def test_decorator_stacking():
    """Test that it works with other decorators (like @tool)."""
    
    # Simulate a decorator that wraps the function
    def other_decorator(func):
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper

    @capguard_tool(risk_level=2)
    @other_decorator
    def stacked_tool():
        """Stacked description."""
        pass
        
    registry = get_global_registry()
    assert "stacked_tool" in registry
    defn = registry.get_definition("stacked_tool")
    # Even if wrapped, we should try to preserve metadata or at least register it
    assert defn.name == "stacked_tool" 
