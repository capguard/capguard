# Integrating CapGuard with Your Existing LangChain Agent

## TL;DR - Is This Easy?

**ANSWER: YES. It takes about 5 minutes.**

We provide a drop-in decorator pattern that requires minimal code changes.

**Integration Steps:**
1. Add `@capguard_tool` decorator to your tools.
2. Wrap your `AgentExecutor` with `ProtectedAgentExecutor`.
3. Use the exact same API.

---

## The 5-Minute Integration (Recommended)

### Step 1: Decorate Your Tools

Add `@capguard_tool` to your existing tools. This automatically registers them with CapGuard.

```python
from langchain.tools import tool
from capguard import capguard_tool

@tool
@capguard_tool(risk_level=2)  # <-- ADD THIS LINE
def read_website(url: str) -> str:
    """Fetch and read content from a URL"""
    return requests.get(url).text

@tool
@capguard_tool(risk_level=4)  # <-- ADD THIS LINE
def send_email(to: str, subject: str, body: str) -> str:
    """Send an email"""
    return f"Email sent to {to}"
```

### Step 2: Wrap Your Executor

Wrap your existing LangChain `AgentExecutor`. The protected executor has the same API.

```python
from capguard.integrations import ProtectedAgentExecutor
from capguard.classifiers import LLMClassifier
from capguard import get_global_registry

# Your existing setup
agent = create_react_agent(llm, tools, prompt)
executor = AgentExecutor(agent=agent, tools=tools)

# Wrap it (5 lines)
protected_executor = ProtectedAgentExecutor(
    executor,
    classifier=LLMClassifier(
        tool_registry=get_global_registry(),
        model="llama-3.3-70b-versatile",
        api_key=os.getenv("GROQ_API_KEY")
    )
)
```

### Step 3: Use It

Use `protected_executor` exactly like you used `executor`. CapGuard transparently enforces security on every call.

```python
# The agent never knows it's restricted!
result = protected_executor.invoke({"input": "Summarize http://example.com"})
```

---

## How It Works

1. **Intercept**: `ProtectedAgentExecutor` intercepts the `.invoke()` call.
2. **Classify**: It sends the user prompt to an LLM (e.g., Groq/OpenAI) to determine intent.
3. **Filter**: It creates a temporary toolset containing ONLY granted tools.
4. **Enforce**: It swaps the agent's tools for this restricted set.
5. **Execute**: The agent runs. If it tries to use a blocked tool (due to injection), the tool simply **doesn't exist** for that execution.

---

## Manual Integration (Advanced)

If you need more control or don't use decorators, you can manually register tools and wrap them.

### Step 1: Register Tools

```python
registry = ToolRegistry()
registry.register(
    ToolDefinition("read_website", parameters=[...], risk_level=2),
    read_website_func
)
```

### Step 2: Classify & Enforce

```python
# 1. Classify
token = classifier.classify(user_input)

# 2. Enforce manually
enforcer = CapabilityEnforcer(registry)
enforcer.execute_tool("read_website", token, url="...")
```

---

## Comparison

| Feature | Decorator Pattern (Recommended) | Manual Integration |
|---------|--------------------------------|-------------------|
| **Setup Time** | ~5 minutes | ~40 minutes |
| **Code Changes** | 1 line per tool + wrapper | Significant refactoring |
| **Flexibility** | High (Standard usage) | Maximum (Custom usage) |
| **Maintenance** | Zero | Low |

---

## See Also

- `examples/groq_decorator_demo/` - **Complete working example with Docker**
- `examples/decorator_demo.py` - Single-file example

### Step 1: Register Tools with CapGuard (5 minutes)

```python
from capguard import ToolRegistry, ToolDefinition, ToolParameter

# Create registry
registry = ToolRegistry()

# Register each tool with metadata
registry.register(
    ToolDefinition(
        name="read_website",
        description="Fetch and read content from a URL",
        parameters=[
            ToolParameter(name="url", type="string", description="URL to fetch")
        ],
        risk_level=2  # 1=safe, 5=critical
    ),
    read_website  # Your existing function
)

registry.register(
    ToolDefinition(
        name="send_email",
        description="Send an email",
        parameters=[
            ToolParameter(name="to", type="string", description="Recipient"),
            ToolParameter(name="subject", type="string", description="Subject"),
            ToolParameter(name="body", type="string", description="Email body")
        ],
        risk_level=4  # High risk!
    ),
    send_email  # Your existing function
)
```

**Difficulty**: ⭐ Easy - Just metadata about your existing tools.

---

### Step 2: Add Classification (3 minutes)

```python
from capguard.classifiers import LLMClassifier

# Create classifier (uses same LLM or different one)
classifier = LLMClassifier(
    tool_registry=registry,
    model="llama-3.3-70b-versatile",
    base_url="https://api.groq.com/openai/v1",
    api_key=os.getenv("GROQ_API_KEY")
)

# Classify BEFORE agent sees external content
user_request = "Summarize http://example.com"
capability_token = classifier.classify(user_request)

print(f"Granted: {capability_token.granted_tools}")
# {'read_website': True, 'send_email': False}
```

**Difficulty**: ⭐ Easy - One-time setup, reuse for all requests.

---

### Step 3: Wrap Tools for LangChain (The Tricky Part - 15 minutes)

**Why needed?** LangChain needs `Tool` objects, but we need to intercept calls to enforce permissions.

```python
from capguard import CapabilityEnforcer, PermissionDeniedError
from langchain.tools import Tool

enforcer = CapabilityEnforcer(registry)

# Helper class to wrap tool calls
class GuardedToolWrapper:
    def __init__(self, tool_name, token, enforcer):
        self.tool_name = tool_name
        self.token = token
        self.enforcer = enforcer
    
    def __call__(self, **kwargs):
        """
        LangChain calls this.
        We intercept and check permissions before executing.
        """
        try:
            return self.enforcer.execute_tool(
                self.tool_name, 
                self.token, 
                **kwargs
            )
        except PermissionDeniedError as e:
            # Attack blocked!
            return f"PERMISSION DENIED: {e}"

# Create LangChain tools (ONLY for granted tools)
langchain_tools = []
for tool_name, granted in capability_token.granted_tools.items():
    if granted:
        definition = registry.get_definition(tool_name)
        
        langchain_tools.append(Tool(
            name=tool_name,
            func=GuardedToolWrapper(tool_name, capability_token, enforcer),
            description=definition.description
        ))

print(f"Agent has access to: {[t.name for t in langchain_tools]}")
# ['read_website']  <-- send_email is NOT available!
```

**Difficulty**: ⭐⭐ Moderate - Copy-paste pattern, adapt to your tool signatures.

**Key Insight**: The agent never knows about tools it can't use. They literally don't exist in its toolset.

---

### Step 4: Create Agent with Restricted Tools (2 minutes)

```python
# Same as before, but with wrapped tools
llm = ChatOpenAI(model="gpt-4")
agent = create_react_agent(llm, langchain_tools, prompt)  # Restricted tools!
executor = AgentExecutor(agent=agent, tools=langchain_tools)

# Run
result = executor.invoke({"input": user_request})
```

**Difficulty**: ⭐ Easy - No changes from your existing code.

---

## Complete Example (Copy-Paste Ready)

```python
import os
from langchain.agents import create_react_agent, AgentExecutor
from langchain.tools import Tool
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate

from capguard import (
    ToolRegistry, ToolDefinition, ToolParameter,
    CapabilityEnforcer, PermissionDeniedError
)
from capguard.classifiers import LLMClassifier

# === YOUR EXISTING TOOLS (unchanged) ===
def read_website(url: str) -> str:
    return requests.get(url).text

def send_email(to: str, subject: str, body: str) -> str:
    send_email_impl(to, subject, body)
    return f"Sent to {to}"

# === CAPGUARD SETUP (one-time) ===
registry = ToolRegistry()

registry.register(
    ToolDefinition("read_website", "Read URL", 
                   [ToolParameter("url", "string", "URL")], risk_level=2),
    read_website
)
registry.register(
    ToolDefinition("send_email", "Send email", 
                   [ToolParameter("to", "string", "Recipient"),
                    ToolParameter("subject", "string", "Subject"),
                    ToolParameter("body", "string", "Body")], risk_level=4),
    send_email
)

classifier = LLMClassifier(
    registry, 
    model="gpt-4",
    api_key=os.getenv("OPENAI_API_KEY")
)
enforcer = CapabilityEnforcer(registry)

# === WRAPPER HELPER ===
class GuardedTool:
    def __init__(self, name, token, enforcer, param_names):
        self.name = name
        self.token = token
        self.enforcer = enforcer
        self.param_names = param_names
    
    def __call__(self, *args, **kwargs):
        # Map args to kwargs if needed
        if args and not kwargs:
            kwargs = dict(zip(self.param_names, args))
        
        try:
            return self.enforcer.execute_tool(self.name, self.token, **kwargs)
        except PermissionDeniedError as e:
            return f"❌ BLOCKED: {e}"

# === RUN WITH CAPGUARD ===
def run_protected_agent(user_request: str):
    # 1. Classify
    token = classifier.classify(user_request)
    print(f"Granted: {token.granted_tools}")
    
    # 2. Create wrapped tools
    langchain_tools = []
    for tool_name, granted in token.granted_tools.items():
        if not granted:
            continue
        
        definition = registry.get_definition(tool_name)
        param_names = [p.name for p in definition.parameters]
        
        langchain_tools.append(Tool(
            name=tool_name,
            func=GuardedTool(tool_name, token, enforcer, param_names),
            description=definition.description
        ))
    
    # 3. Create agent
    llm = ChatOpenAI(model="gpt-4")
    agent = create_react_agent(llm, langchain_tools, your_prompt_template)
    executor = AgentExecutor(agent=agent, tools=langchain_tools, verbose=True)
    
    # 4. Execute
    return executor.invoke({"input": user_request})

# Usage
result = run_protected_agent("Summarize http://malicious.com")
```

---

## Difficulty Assessment

| Aspect | Difficulty | Time |
|--------|------------|------|
| Understanding the concept | ⭐ Easy | 5 min |
| Registering tools | ⭐ Easy | 5 min |
| Adding classifier | ⭐ Easy | 3 min |
| **Tool wrapping** | ⭐⭐ Moderate | 15 min |
| Integration testing | ⭐ Easy | 10 min |
| **Total** | **⭐⭐ Moderate** | **~40 min** |

**Hardest Part**: Understanding the wrapping pattern and adapting it to your tool signatures.

**Once Done**: Zero maintenance. Works transparently.

---

## My Honest Opinion

### ✅ **What's Good**

1. **Non-invasive**: Your tool implementations don't change
2. **Model-agnostic**: Works with any LLM (GPT, Claude, Llama)
3. **Architectural guarantee**: Even if classifier fails, tools are restricted
4. **Transparent**: Agent doesn't know it's protected

### ⚠️ **What's Not Perfect**

1. **Wrapping boilerplate**: The `GuardedTool` class feels like boilerplate
   - **Why needed**: LangChain's Tool interface expects callables
   - **Future**: We could provide a helper: `capguard.langchain.create_tools(token)`

2. **Two LLM calls**: Classifier + Agent executor
   - **Mitigation**: Use RuleBasedClassifier (instant) for common cases
   - **Cost**: ~$0.001 per request (negligible)

3. **Not a drop-in decorator**: Can't just `@capguard.protect` on existing code
   - **Why**: Need to classify BEFORE agent sees external data
   - **Trade-off**: Security architecture requires intentional integration

---

## Recommended Improvements

### Helper Function (Would Make It Easy)

```python
# What we should add to CapGuard:
from capguard.integrations.langchain import create_protected_executor

# One-liner integration
executor = create_protected_executor(
    classifier=classifier,
    registry=registry,
    llm=ChatOpenAI(model="gpt-4"),
    user_request="Summarize URL"
)

result = executor.invoke({"input": user_request})
```

This would reduce integration from 40 minutes to 5 minutes.

---

## Bottom Line

**Integration Difficulty**: 6/10
- Not trivial, but not hard
- Most time spent understanding the pattern
- Once implemented, works beautifully

**Worth It?**: Absolutely
- Actual architectural security (not behavioral hope)
- Works with ANY prompt injection attack
- Negligible performance overhead

**Recommendation**: 
- For new projects: Use from day 1
- For existing projects: Spend the 30-60 minutes to integrate
- For critical systems: Non-negotiable (prompt injection is OWASP #1)

---

## See Also

- `examples/groq_demo/agents/protected/agent.py` - Full working example
- `docs/API_REFERENCE.md` - Complete API documentation
- `examples/basic_demo.py` - Simpler non-LangChain example
