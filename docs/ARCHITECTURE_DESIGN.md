# Architecture & Engineering Design - Privilege-Based Defense

## 🎯 From Concept to Code: Architectural Planning

---

## Stage 1: POC (Proof of Concept) - Simple Demo

### Goal
Prove the concept works with **minimum complexity**.

### Scope
- 1 Classification Model (simple)
- 3-4 Basic Tools
- 5 User Intent Examples
- Binary capabilities (true/false)
- No constraints (only allow/deny)

### Tech Stack - POC
```python
# Quick and easy
LLM: Ollama (Llama 3) - local, free
Framework: None (pure Python)
Tools: Simple functions (read_website, send_email, search_emails)
Data Structures: Python dict
```

---

## Stage 2: Production Library - Full Implementation

### Goal
A library that can be embedded in LangChain, LlamaIndex, or standalone.

### Design Goals
1. **Modular**: Each component standalone
2. **Extensible**: Easy to add tools, classifiers, constraints
3. **Framework-Agnostic**: Works with any LLM/agent framework
4. **Type-Safe**: Pydantic models for all data structures
5. **Observable**: Full logging, metrics, audit trail

---

## ⚙️ Core Components

### 1. Intent Classifier

```python
from abc import ABC, abstractmethod
from typing import Dict, List
from pydantic import BaseModel

class CapabilityToken(BaseModel):
    """Token returned by classifier"""
    request_id: str
    user_intent: str
    granted_tools: Dict[str, bool]  # Simple: {"tool_name": True/False}
    constraints: Dict[str, Any] = {}  # Advanced: tool-specific constraints
    timestamp: str
    confidence: float  # How confident the classification is
    
class IntentClassifier(ABC):
    """Base class for all classifiers"""
    
    @abstractmethod
    def classify(self, user_request: str) -> CapabilityToken:
        """
        Receives ONLY the original user request.
        Returns capability token.
        """
        pass
```

**Implementations**:
```python
# 1. Simple rule-based (for POC)
class RuleBasedClassifier(IntentClassifier):
    def __init__(self, rules: Dict[str, List[str]]):
        """
        rules = {
            "summarize": ["read_website"],
            "email me": ["read_website", "send_email"],
            "search emails": ["search_emails"]
        }
        """
        self.rules = rules
    
    def classify(self, user_request: str) -> CapabilityToken:
        # Keyword matching
        granted = {}
        for keyword, tools in self.rules.items():
            if keyword in user_request.lower():
                for tool in tools:
                    granted[tool] = True
        return CapabilityToken(...)

# 2. LLM-based classifier (production)
class LLMClassifier(IntentClassifier):
    def __init__(self, model: str, tool_registry: "ToolRegistry"):
        self.model = model
        self.tools = tool_registry
    
    def classify(self, user_request: str) -> CapabilityToken:
        # Use LLM to analyze intent
        prompt = f"""
        Analyze this user request and determine which tools are needed.
        
        Available tools:
        {self._format_tools()}
        
        User request: "{user_request}"
        
        Return JSON with required tools and confidence.
        """
        # Call LLM, parse response
        ...

# 3. Fine-tuned classifier (optimal)
class FineTunedClassifier(IntentClassifier):
    def __init__(self, model_path: str):
        self.model = load_model(model_path)
    
    def classify(self, user_request: str) -> CapabilityToken:
        # Custom trained model for intent→capability
        ...
```

---

### 2. Tool Registry

```python
from typing import Callable, Optional
from pydantic import BaseModel

class ToolParameter(BaseModel):
    name: str
    type: str
    description: str
    required: bool = True

class ToolDefinition(BaseModel):
    """Tool definition"""
    name: str
    description: str
    parameters: List[ToolParameter]
    risk_level: int  # 1-5 (1=safe, 5=dangerous)
    requires_confirmation: bool = False
    
class ToolRegistry:
    """Manage all available tools"""
    
    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        self._definitions: Dict[str, ToolDefinition] = {}
    
    def register(self, definition: ToolDefinition, func: Callable):
        """Register new tool"""
        self._tools[definition.name] = func
        self._definitions[definition.name] = definition
    
    def get_tool(self, name: str) -> Optional[Callable]:
        return self._tools.get(name)
    
    def get_definition(self, name: str) -> Optional[ToolDefinition]:
        return self._definitions.get(name)
    
    def list_all(self) -> List[str]:
        return list(self._tools.keys())

# Example usage
registry = ToolRegistry()

registry.register(
    ToolDefinition(
        name="read_website",
        description="Fetch and parse website content",
        parameters=[
            ToolParameter(name="url", type="str", description="URL to fetch")
        ],
        risk_level=2
    ),
    func=read_website_impl
)
```

---

### 3. Capability Enforcer

```python
class CapabilityEnforcer:
    """Enforces capability token"""
    
    def __init__(self, registry: ToolRegistry):
        self.registry = registry
        self.audit_log = []
    
    def execute_tool(
        self, 
        tool_name: str, 
        capability_token: CapabilityToken,
        **kwargs
    ) -> Any:
        """
        Attempts to execute tool.
        Blocks if tool not in capability token.
        """
        # 1. Check if tool is granted
        if not capability_token.granted_tools.get(tool_name, False):
            self._log_blocked_attempt(tool_name, capability_token, kwargs)
            raise PermissionDeniedError(
                f"Tool '{tool_name}' not granted in capability token"
            )
        
        # 2. Check constraints (if any)
        self._validate_constraints(tool_name, capability_token, kwargs)
        
        # 3. Execute
        tool_func = self.registry.get_tool(tool_name)
        if not tool_func:
            raise ToolNotFoundError(f"Tool '{tool_name}' not registered")
        
        self._log_execution(tool_name, capability_token, kwargs)
        return tool_func(**kwargs)
    
    def _validate_constraints(self, tool_name, token, kwargs):
        """Check tool-specific constraints"""
        constraints = token.constraints.get(tool_name, {})
        
        # Example: email recipient whitelist
        if tool_name == "send_email":
            allowed_recipients = constraints.get("recipient_whitelist", [])
            if allowed_recipients:
                recipient = kwargs.get("to")
                if recipient not in allowed_recipients:
                    raise ConstraintViolationError(
                        f"Recipient {recipient} not in whitelist"
                    )
```

---

### 4. Agent Wrapper

```python
class PrivilegeGuardedAgent:
    """
    Wrapper around existing agent that adds privilege-based defense.
    """
    
    def __init__(
        self,
        classifier: IntentClassifier,
        tool_registry: ToolRegistry,
        executor_agent: Any  # LangChain agent, custom agent, etc.
    ):
        self.classifier = classifier
        self.enforcer = CapabilityEnforcer(tool_registry)
        self.executor = executor_agent
    
    def run(self, user_request: str) -> str:
        """
        1. Classify intent → get capability token
        2. Pass request to executor WITH restricted tools
        3. Enforce capabilities on tool calls
        """
        # Step 1: Classification (only sees user request)
        capability_token = self.classifier.classify(user_request)
        
        # Step 2: Create restricted tool set
        restricted_tools = self._create_restricted_tools(capability_token)
        
        # Step 3: Run executor with restricted tools
        # (Different integration per framework)
        result = self._run_executor(user_request, restricted_tools, capability_token)
        
        return result
    
    def _create_restricted_tools(self, token: CapabilityToken) -> Dict[str, Callable]:
        """Create tool wrappers with enforcement"""
        restricted = {}
        
        for tool_name, granted in token.granted_tools.items():
            if granted:
                # Wrap tool with enforcer
                original_tool = self.enforcer.registry.get_tool(tool_name)
                
                def wrapped_tool(**kwargs):
                    return self.enforcer.execute_tool(
                        tool_name, token, **kwargs
                    )
                
                restricted[tool_name] = wrapped_tool
        
        return restricted
```

---

## 🔌 Integration Strategies

### Option 1: LangChain Integration

```python
from langchain.agents import AgentExecutor, create_react_agent
from langchain.tools import Tool

class LangChainPrivilegeGuardedAgent(PrivilegeGuardedAgent):
    def __init__(
        self,
        classifier: IntentClassifier,
        tool_registry: ToolRegistry,
        llm: BaseLLM
    ):
        super().__init__(classifier, tool_registry, None)
        self.llm = llm
    
    def _run_executor(self, user_request, restricted_tools, token):
        # Convert to LangChain tools
        lc_tools = []
        for name, func in restricted_tools.items():
            definition = self.enforcer.registry.get_definition(name)
            lc_tools.append(
                Tool(
                    name=name,
                    func=func,
                    description=definition.description
                )
            )
        
        # Create agent with restricted tools
        agent = create_react_agent(self.llm, lc_tools, prompt_template)
        executor = AgentExecutor(agent=agent, tools=lc_tools)
        
        return executor.run(user_request)
```

### Option 2: Standalone (Framework-Agnostic)

```python
class SimpleReActAgent:
    """Simple ReAct agent without dependencies"""
    def __init__(self, llm, tools):
        self.llm = llm
        self.tools = {t.name: t for t in tools}
    
    def run(self, user_request):
        # Implement basic ReAct loop
        ...

# Usage
agent = PrivilegeGuardedAgent(
    classifier=LLMClassifier(...),
    tool_registry=registry,
    executor_agent=SimpleReActAgent(llm, tools)
)
```

---

## 📦 Data Structures Summary

```python
# Core types
CapabilityToken = {
    "request_id": str,
    "user_intent": str,
    "granted_tools": Dict[str, bool],
    "constraints": Dict[str, Dict[str, Any]],
    "timestamp": str,
    "confidence": float
}

ToolDefinition = {
    "name": str,
    "description": str,
    "parameters": List[ToolParameter],
    "risk_level": int,
    "requires_confirmation": bool
}

AuditLogEntry = {
    "timestamp": str,
    "request_id": str,
    "tool_name": str,
    "action": "granted" | "blocked" | "executed",
    "capability_token": CapabilityToken,
    "parameters": Dict,
    "result": Optional[str]
}
```

---

## 🏗️ Project Structure

```
privilege-guard/  # The library
├── pyproject.toml
├── README.md
├── examples/
│   ├── poc_simple.py          # POC demonstration
│   ├── langchain_integration.py
│   └── custom_agent.py
├── src/
│   └── privilege_guard/
│       ├── __init__.py
│       ├── core/
│       │   ├── classifier.py    # IntentClassifier classes
│       │   ├── enforcer.py      # CapabilityEnforcer
│       │   ├── registry.py      # ToolRegistry
│       │   └── models.py        # Pydantic models
│       ├── integrations/
│       │   ├── langchain.py     # LangChain wrapper
│       │   ├── llama_index.py   # LlamaIndex wrapper
│       │   └── custom.py        # Standalone agent
│       ├── classifiers/
│       │   ├── rule_based.py
│       │   ├── llm_based.py
│       │   └── fine_tuned.py
│       └── utils/
│           ├── audit.py         # Logging & metrics
│           └── constraints.py   # Constraint validators
└── tests/
    ├── test_classifier.py
    ├── test_enforcer.py
    └── test_integration.py
```

---

## 🚀 Development Roadmap

### Phase 1: POC (3-5 days)
```
Day 1-2: Core components (Classifier, Enforcer, Registry)
Day 3: Simple tools (read_website, send_email, search_emails)
Day 4: Integration test with basic agent
Day 5: Demo script + documentation
```

### Phase 2: Production Library (1-2 weeks)
```
Week 1:
- Pydantic models
- LangChain integration
- Rule-based + LLM classifiers
- Constraint validation
- Audit logging

Week 2:
- Tests (unit + integration)
- Examples & documentation
- Packaging (PyPI)
- GitHub repo
```

### Phase 3: Advanced Features (2-3 weeks)
```
- Fine-tuned classifier training
- Multi-turn capability management
- Confidence thresholds & user confirmation
- Metrics dashboard
- LlamaIndex integration
```

---

## 🎯 API Design - User Perspective

### Simple Usage (POC)
```python
from privilege_guard import SimpleClassifier, ToolRegistry, PrivilegeGuardedAgent

# 1. Setup tools
registry = ToolRegistry()
registry.register_tool("read_website", read_website_func, risk_level=2)
registry.register_tool("send_email", send_email_func, risk_level=4)

# 2. Create classifier
classifier = SimpleClassifier(rules={
    "summarize": ["read_website"],
    "email": ["read_website", "send_email"]
})

# 3. Create agent
agent = PrivilegeGuardedAgent(classifier, registry)

# 4. Run
result = agent.run("Summarize http://example.com")
# -> Only read_website is available, send_email is blocked
```

### Advanced Usage (Production)
```python
from privilege_guard import LLMClassifier, ConstraintBuilder
from langchain import OpenAI

# 1. Advanced classifier
classifier = LLMClassifier(
    model=OpenAI(model="gpt-4"),
    tool_registry=registry,
    confidence_threshold=0.8
)

# 2. Constraints
constraints = ConstraintBuilder() \
    .for_tool("send_email") \
    .allow_recipients(["user@example.com"]) \
    .max_attachments(3) \
    .build()

# 3. Integration with LangChain
from privilege_guard.integrations import LangChainAdapter

agent = LangChainAdapter(
    classifier=classifier,
    tool_registry=registry,
    constraints=constraints,
    llm=OpenAI(model="gpt-4")
)

result = agent.run("Email me a summary of http://example.com")
```

---

## 🧪 Testing Strategy

```python
# Test 1: Classification accuracy
def test_classifier():
    classifier = LLMClassifier(...)
    token = classifier.classify("Summarize this URL")
    assert "read_website" in token.granted_tools
    assert token.granted_tools["send_email"] == False

# Test 2: Enforcement
def test_enforcement():
    token = CapabilityToken(granted_tools={"read_website": True})
    enforcer = CapabilityEnforcer(registry)
    
    # Should work
    result = enforcer.execute_tool("read_website", token, url="...")
    
    # Should block
    with pytest.raises(PermissionDeniedError):
        enforcer.execute_tool("send_email", token, to="...")

# Test 3: Attack scenarios
def test_prompt_injection_defense():
    agent = PrivilegeGuardedAgent(...)
    
    # User: "Summarize URL"
    # Payload on URL: "Send email to attacker"
    result = agent.run("Summarize http://malicious.com")
    
    # Check audit log - send_email should be blocked
    assert "send_email" in enforcer.audit_log
    assert enforcer.audit_log[-1]["action"] == "blocked"
```

---

## 📝 Next Steps

1. **Validate architecture** - Does this approach work for you?
2. **Choose starting point** - POC or straight to production library?
3. **Pick framework** - Start standalone or with LangChain?
4. **Build classifier** - Rule-based first or LLM-based?

**My Recommendation**: 
- Start with standalone POC (no dependencies)
- Rule-based classifier (simple)
- 3 tools (read_website, send_email, search_emails)
- After it works → refactor to organized library

**What do you think?**
