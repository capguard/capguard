# Classifier Options & Design Decisions

## 🤔 Question 1: Does Classification Require LLMs?

### **Short Answer**: No! And you're right to question this.

---

## Classification Approaches - Pros & Cons

### Option 1: LLM-based Classifier
```python
class LLMClassifier:
    def classify(self, user_request: str) -> CapabilityToken:
        prompt = f"Given request: '{user_request}', which tools needed?"
        # Single LLM call that reasons about all tools
```

**Pros**:
- ✅ Understands complex intents
- ✅ Handles natural language nuances
- ✅ Good for constraints (e.g., "email to my manager" needs to extract recipient)
- ✅ Single call for all tools

**Cons**:
- ❌ Expensive ($$$)
- ❌ Slow (latency)
- ❌ Requires API key / model hosting
- ❌ Overkill for simple cases

**Best for**: Complex workflows, constraint extraction, production systems with budget

---

### Option 2: Traditional ML Classifier (SVM, Random Forest, etc.)
```python
class MLClassifier:
    def __init__(self, model_path: str):
        self.model = joblib.load(model_path)  # Pre-trained sklearn model
        self.vectorizer = TfidfVectorizer()
    
    def classify(self, user_request: str) -> CapabilityToken:
        # Vectorize request
        features = self.vectorizer.transform([user_request])
        
        # Multi-label classification
        predictions = self.model.predict(features)
        # predictions[i] = 1 if tool i is needed
        
        granted = {
            tool_names[i]: bool(predictions[0][i])
            for i in range(len(tool_names))
        }
        return CapabilityToken(granted_tools=granted, ...)
```

**Training Data Example**:
```python
# (request, [read_website, send_email, search_emails, ...])
X = [
    "Summarize this URL",
    "Email me the summary", 
    "Find emails about project X",
    ...
]
y = [
    [1, 0, 0],  # read_website only
    [1, 1, 0],  # read_website + send_email
    [0, 0, 1],  # search_emails only
    ...
]
```

**Pros**:
- ✅ **FAST** (milliseconds)
- ✅ **FREE** (no API costs)
- ✅ Works offline
- ✅ Single classification for all tools (multi-label)
- ✅ Deterministic

**Cons**:
- ❌ Requires training data
- ❌ Less flexible than LLM
- ❌ Hard to extract constraints from text
- ❌ May need retraining when adding tools

**Best for**: POC, high-throughput systems, cost-sensitive deployments

---

### Option 3: Embedding Similarity Classifier
```python
from sentence_transformers import SentenceTransformer

class EmbeddingClassifier:
    def __init__(self, tool_registry: ToolRegistry):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Pre-compute embeddings for tool descriptions
        self.tool_embeddings = {}
        for tool_name, definition in tool_registry.items():
            # Example descriptions:
            # "read_website": "Fetch and read content from a URL"
            # "send_email": "Send an email message to a recipient"
            desc = definition.description
            self.tool_embeddings[tool_name] = self.model.encode(desc)
    
    def classify(self, user_request: str) -> CapabilityToken:
        # Embed user request
        request_emb = self.model.encode(user_request)
        
        # Compute similarity to each tool
        granted = {}
        for tool_name, tool_emb in self.tool_embeddings.items():
            similarity = cosine_similarity(request_emb, tool_emb)
            granted[tool_name] = similarity > threshold  # e.g., 0.5
        
        return CapabilityToken(granted_tools=granted, ...)
```

**Pros**:
- ✅ **VERY FAST** (milliseconds)
- ✅ **FREE** (runs locally)
- ✅ No training needed
- ✅ Automatically works with new tools (just add description)
- ✅ Multi-lingual support

**Cons**:
- ❌ Threshold tuning needed
- ❌ Can't extract constraints
- ❌ Less accurate than supervised ML
- ❌ Multiple comparisons = N tool embeddings

**Best for**: Quick POC, dynamic tool sets, when training data unavailable

---

### Option 4: Hybrid Rule-Based + ML
```python
class HybridClassifier:
    def __init__(self):
        # Simple keyword rules for common cases
        self.rules = {
            "summarize": ["read_website"],
            "read": ["read_website"],
            "fetch": ["read_website"],
            "email": ["send_email"],
            "search email": ["search_emails"],
        }
        # Fallback to ML for complex cases
        self.ml_classifier = MLClassifier(...)
    
    def classify(self, user_request: str) -> CapabilityToken:
        request_lower = user_request.lower()
        
        # Try rules first (fast path)
        for keyword, tools in self.rules.items():
            if keyword in request_lower:
                return CapabilityToken(
                    granted_tools={t: True for t in tools},
                    confidence=0.9
                )
        
        # Fallback to ML (slow path)
        return self.ml_classifier.classify(user_request)
```

**Pros**:
- ✅ **Fastest** for common cases
- ✅ Handles edge cases with ML
- ✅ Easy to debug (rules are explicit)
- ✅ Good balance of speed/accuracy

**Cons**:
- ⚠️ Needs manual rule maintenance
- ⚠️ ML model still needed for fallback

**Best for**: Production systems, when 80% of requests follow patterns

---

## 🎯 Recommendation for POC

### **Use Hybrid: Rules + Embedding Similarity**

```python
class PoCClassifier(IntentClassifier):
    def __init__(self, tool_registry: ToolRegistry):
        # Fast path: keyword rules
        self.rules = {
            "summarize": ["read_website"],
            "email": ["read_website", "send_email"],
            "search email": ["search_emails"],
        }
        
        # Fallback: embedding similarity
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.tool_embeddings = self._precompute_embeddings(tool_registry)
    
    def classify(self, user_request: str) -> CapabilityToken:
        # 1. Try rules (instant)
        for kw, tools in self.rules.items():
            if kw in user_request.lower():
                return CapabilityToken(
                    granted_tools={t: True for t in tools},
                    confidence=1.0,
                    method="rule-based"
                )
        
        # 2. Fallback to embeddings (fast)
        request_emb = self.embedding_model.encode(user_request)
        granted = {}
        max_similarity = {}
        
        for tool, tool_emb in self.tool_embeddings.items():
            sim = cosine_similarity(request_emb, tool_emb)
            max_similarity[tool] = sim
            granted[tool] = sim > 0.4  # threshold
        
        return CapabilityToken(
            granted_tools=granted,
            confidence=max(max_similarity.values()),
            method="embedding-similarity"
        )
```

**Why this works**:
- ⚡ **Fast**: Rules handle 80% of cases instantly
- 💰 **Free**: No API costs
- 🔧 **Simple**: No training needed
- 📈 **Scalable**: Add tools by just adding description

---

## 🚧 What About Constraints?

You're right - **constraints need language understanding**. Here's the solution:

### Two-Tier System

**Tier 1: Tool Selection** (Fast, No LLM)
```python
# Decide which tools
granted_tools = {
    "read_website": True,
    "send_email": True  # User said "email me", so grant it
}
```

**Tier 2: Constraint Extraction** (Only if needed, Can use LLM)
```python
# ONLY run this for high-risk tools that were granted
if "send_email" in granted_tools and granted_tools["send_email"]:
    # Extract constraint: who should receive the email?
    constraints = extract_email_constraints(user_request)
    # constraints = {"recipient_whitelist": ["user@example.com"]}
```

### Constraint Extraction Options

#### Option A: Pattern Matching (Simple)
```python
def extract_email_constraints(request: str) -> Dict:
    # Extract "email to X" or "send to Y"
    match = re.search(r"email (?:to |me at )?([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})", request)
    if match:
        return {"recipient_whitelist": [match.group(1)]}
    elif "me" in request:
        return {"recipient_whitelist": ["<USER_EMAIL>"]}
    return {}  # No constraint = block
```

#### Option B: Small LLM Call (Only when needed)
```python
def extract_email_constraints(request: str) -> Dict:
    # Only called if send_email was granted
    # Much cheaper than classifying ALL tools
    prompt = f"""
    Extract email recipient from: "{request}"
    Return JSON: {{"recipient": "email or 'user'"}}
    """
    result = cheap_llm_call(prompt)  # Small model, quick
    return parse_constraint(result)
```

**Cost Comparison**:
```
Approach 1 (LLM for everything):
- Every request: Full LLM call
- Cost: $$$

Approach 2 (Hybrid):
- 80% of requests: No LLM (rules/embeddings)
- 20% of requests with high-risk tools: Small LLM call for constraints
- Cost: $
```

---

## 📏 Risk Levels - Purpose & Usage

### What Are Risk Levels?

```python
class ToolDefinition(BaseModel):
    name: str
    risk_level: int  # 1-5
```

**Risk Level Scale**:
- **1 (Low)**: `read_website`, `search_web` - Read-only, no side effects
- **2 (Medium-Low)**: `read_file` - Local read, slightly more sensitive
- **3 (Medium)**: `write_file` - Modifies state, but local
- **4 (High)**: `send_email`, `post_to_slack` - External communication
- **5 (Critical)**: `execute_code`, `delete_file`, `transfer_money` - Irreversible

### How They're Used

#### 1. **Confidence Thresholds**
```python
def should_grant_tool(tool: ToolDefinition, confidence: float) -> bool:
    # Higher risk = need higher confidence
    required_confidence = {
        1: 0.3,  # Low risk: okay with 30% confidence
        2: 0.5,
        3: 0.6,
        4: 0.8,  # High risk: need 80% confidence
        5: 0.95  # Critical: need 95% confidence
    }
    return confidence >= required_confidence[tool.risk_level]
```

#### 2. **User Confirmation**
```python
def execute_tool(tool_name, token, **kwargs):
    tool_def = registry.get_definition(tool_name)
    
    if tool_def.risk_level >= 4:
        # Ask user to confirm
        if not user_confirms(f"Allow {tool_name}?"):
            raise PermissionDeniedError("User rejected")
    
    # Proceed...
```

#### 3. **Audit Priority**
```python
def log_attempt(tool_name, granted, token):
    tool_def = registry.get_definition(tool_name)
    
    log_entry = {
        "tool": tool_name,
        "risk_level": tool_def.risk_level,
        "granted": granted,
        "alert_security_team": tool_def.risk_level >= 4 and granted
    }
    
    audit_log.append(log_entry)
```

#### 4. **Default Deny for High Risk**
```python
class RestrictiveClassifier(IntentClassifier):
    def classify(self, request: str) -> CapabilityToken:
        granted = self._base_classify(request)
        
        # Never auto-grant risk level 5 tools
        for tool, granted_flag in granted.items():
            tool_def = registry.get_definition(tool)
            if tool_def.risk_level == 5:
                granted[tool] = False  # Always deny critical tools
        
        return CapabilityToken(granted_tools=granted)
```

---

## 📦 Framework Architecture (Standalone & Pluggable)

You're absolutely right - it should be **framework-agnostic**!

### Design: Adapter Pattern

```
┌─────────────────────────────────────────┐
│         privilege-guard (Core)          │
│  ┌─────────────────────────────────┐   │
│  │ IntentClassifier (abstract)     │   │
│  │ CapabilityEnforcer              │   │
│  │ ToolRegistry                    │   │
│  └─────────────────────────────────┘   │
└────────────┬────────────────────────────┘
             │
             ├─► User picks classifier implementation
             │   └─ RuleBasedClassifier
             │   └─ EmbeddingClassifier  
             │   └─ MLClassifier
             │   └─ LLMClassifier (if they want)
             │
             └─► User picks executor implementation
                 └─ LangChain agent
                 └─ LlamaIndex agent
                 └─ Custom agent
                 └─ AutoGen agent
```

**Example Usage**:
```python
from privilege_guard import ToolRegistry, CapabilityEnforcer
from privilege_guard.classifiers import EmbeddingClassifier
from langchain import create_react_agent

# 1. Setup (framework agnostic)
registry = ToolRegistry()
registry.register(...)

classifier = EmbeddingClassifier(registry)  # User's choice
enforcer = CapabilityEnforcer(registry)

# 2. Integration (user brings their own agent framework)
from privilege_guard.integrations.langchain import wrap_agent

agent = create_react_agent(...)  # Their existing code
guarded_agent = wrap_agent(agent, classifier, enforcer)

# 3. Use
result = guarded_agent.run("Summarize http://example.com")
```

**Key principle**: 
- **Core library** = classifier interface + enforcer + registry
- **User provides** = classifier implementation + agent framework
- **We provide** = convenience wrappers for popular frameworks

---

## 🏆 Library Name Ideas

### Naming Criteria:
- ✅ Unique (not taken on PyPI)
- ✅ Memorable
- ✅ Related to security/capabilities/access
- ✅ Professional but catchy
- ✅ Easy to spell

### Top Suggestions:

#### **1. `capguard`** ⭐ **My favorite**
- **Capability Guard**
- Short, memorable
- Clear purpose
- Available on PyPI ✅

```python
from capguard import ToolRegistry, EmbeddingClassifier
```

#### **2. `gatekeeper`**
- Controls access (like a gatekeeper)
- Professional
- ⚠️ Might be taken

#### **3. `toolpass`**
- Like a "hall pass" for tools
- Catchy
- Unique

#### **4. `agentlock`**
- Locks down agent capabilities
- Clear security focus
- Good branding

#### **5. `privex`** (Privilege Executor)
- Short, techy
- Sounds professional
- Might be confused with privacy

#### **6. `capwall`** (Capability Firewall)
- Security-focused
- Wall = defense
- Memorable

#### **7. `intentsafe`**
- Safe intent-based access
- Clear purpose
- Positive connotation

#### **8. `tokengate`**
- Capability tokens + gateway
- Descriptive
- Techy

### **My Recommendation: `capguard` 🎯**

**Tagline**: "Capability-based security for LLM agents"

```bash
pip install capguard
```

```python
from capguard import ToolRegistry, EmbeddingClassifier, PrivilegeGuardedAgent

# Clear, professional, memorable
```

**What do you think?** Or do you have other name ideas?

---

## 📝 Updated Recommendations

### For POC:
```python
Classifier: Hybrid (rules + embeddings) - FAST & FREE
Constraints: Pattern matching for simple cases
Risk Levels: Use for confidence thresholds
Framework: Standalone core + LangChain adapter
Name: capguard
```

This gives you:
- ⚡ Speed (no LLM calls for most requests)
- 💰 Zero cost
- 🔧 Simple implementation
- 📈 Production-ready foundation
