# Future Research: Fine-Tuning & Function-Calling LLMs

**Status:** Research Direction (Post-MVP)  
**Timeline:** After achieving product-market fit  
**Goal:** Optimize classification accuracy, latency, and cost

---

## Current Approach (v0.1.0)

**3-Tier Classifier System:**
1. **Rules** (instant, free, 70% coverage)
2. **Embeddings** (50ms, free, 85% accuracy) 
3. **LLM** (Llama3/GPT-4, 100-500ms, 90-95% accuracy)

**Works well but:** LLMs are general-purpose - overkill for narrow capability classification task.

---

## Research Direction 1: Function-Calling LLMs

### FunctionGemma (Google)

**Reference:** https://ai.google.dev/gemma/docs/functiongemma

**What is it?**  
Gemma 2 variant fine-tuned specifically for function calling and structured output.

**Why it's perfect for CapGuard:**
- Pre-trained to map natural language → function calls
- Outputs structured JSON (fewer parsing errors)
- Understands "which tools are needed" natively
- Optimized for low latency

### Example Integration

```python
import google.generativeai as genai

class FunctionGemmaClassifier(IntentClassifier):
    def __init__(self, tool_registry: ToolRegistry):
        self.model = genai.GenerativeModel('gemma-2-9b-it')
        self.registry = tool_registry
    
    def classify(self, user_request: str) -> CapabilityToken:
        # Convert CapGuard tools to FunctionGemma format
        tools = [
            {
                "name": name,
                "description": defn.description,
                "parameters": {
                    p.name: {"type": p.type, "description": p.description}
                    for p in defn.parameters
                }
            }
            for name, defn in self.registry.get_all_definitions().items()
        ]
        
        # FunctionGemma determines which functions are needed
        response = self.model.generate_content(
            user_request,
            tools=tools
        )
        
        # Parse function calls → capability token
        granted_tools = {
            tool["name"]: True
            for tool in response.function_calls
        }
        
        # Default to False for tools not called
        for tool_name in self.registry.list_tools():
            if tool_name not in granted_tools:
                granted_tools[tool_name] = False
        
        return CapabilityToken(
            user_request=user_request,
            granted_tools=granted_tools,
            confidence=0.95,  # FunctionGemma is reliable
            classification_method="functiongemma-2-9b"
        )
```

**Expected Results:**
- **Latency:** 50-100ms (2-5x faster than GPT-4)
- **Accuracy:** 95%+ (specialized for this task)
- **Reliability:** Structured output (no JSON parsing failures)
- **Cost:** $0 (can run on Ollama)

**Availability:**
- Weights: https://huggingface.co/google/gemma-2-9b-it
- Ollama: `ollama pull gemma2:9b`

---

## Research Direction 2: Fine-Tuned Llama 3

### Approach

Fine-tune Llama 3 8B specifically on capability classification task.

### Training Data Format

```json
{
  "messages": [
    {
      "role": "system",
      "content": "You are a capability classifier for CapGuard. Analyze user requests and output which tools are required as JSON."
    },
    {
      "role": "user",
      "content": "Available tools:\n- read_website (risk: 2): Fetch and read content from URL\n- send_email (risk: 4): Send email message\n- search_emails (risk: 3): Search user's emails\n\nUser request: 'Summarize http://example.com'"
    },
    {
      "role": "assistant",
      "content": "{\"granted_tools\": {\"read_website\": true, \"send_email\": false, \"search_emails\": false}, \"confidence\": 0.95}"
    }
  ]
}
```

### Data Collection Strategy

**Phase 1: Synthetic (5,000 examples)**
```python
# Use GPT-4 to generate diverse examples
templates = [
    "Summarize {url}",
    "Email me {content}",
    "Search my emails for {query}",
    "Read {url} and send summary to {email}",
    ...
]

# Generate with variations
for template in templates:
    for _ in range(100):
        example = generate_example(template)
        label_with_gpt4(example)  # Automatic labeling
        training_data.append(example)
```

**Phase 2: Production Logs (3,000 examples)**
```python
# Log all classifications in production
@classifier.classify.log
def classify(user_request):
    token = real_classify(user_request)
    
    # Log for training
    log_classification(user_request, token)
    
    return token

# Review flagged cases
if token.confidence < 0.8:
    queue_for_human_review(user_request, token)
```

**Phase 3: Human Annotation (2,000 examples)**
- Edge cases
- Multi-tool scenarios  
- Constraint extraction
- Attack scenarios

### Fine-Tuning Process

```bash
# Use Hugging Face libraries
python train.py \\
  --model_name meta-llama/Llama-3-8B \\
  --dataset capability_classification_train.jsonl \\
  --output_dir ./capguard-llama3-8b \\
  --num_epochs 3 \\
  --learning_rate 2e-5 \\
  --batch_size 4

# Convert to Ollama
ollama create capguard-classifier -f Modelfile
```

**Expected Results:**
- **Latency:** 50-100ms (local, GPU)
- **Accuracy:** 95-98% (specialized > general)
- **Cost:** $500-2k (one-time training)
- **Maintenance:** Periodic retraining as tools change

---

## Research Direction 3: Multi-Label Classification (ML)

### Approach

Treat as pure ML problem - not LLM-based.

### Architecture

```
User Request 
  ↓
BERT/sentence-BERT Embedding (768-dim)
  ↓
Dense Layer (256 neurons, ReLU)
  ↓
Dense Layer (num_tools neurons, Sigmoid)
  ↓
[P(tool1), P(tool2), P(tool3), ...]
```

### Code

```python
import torch
import torch.nn as nn
from sentence_transformers import SentenceTransformer

class MultiLabelToolClassifier(nn.Module):
    def __init__(self, num_tools: int, embedding_dim: int = 768):
        super().__init__()
        self.layers = nn.Sequential(
            nn.Linear(embedding_dim, 256),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(256, num_tools),
            nn.Sigmoid()
        )
    
    def forward(self, embeddings):
        return self.layers(embeddings)

# Training
model = MultiLabelToolClassifier(num_tools=10)
embedder = SentenceTransformer('all-MiniLM-L6-v2')

# User request → embedding
embedding = embedder.encode("Summarize URL")

# Predict tool probabilities
probs = model(torch.tensor(embedding))

# Threshold at 0.5
granted = {tool_names[i]: float(probs[i]) > 0.5 for i in range(len(tool_names))}
```

**Advantages:**
- **Fastest:** <10ms inference (vs 100-500ms for LLMs)
- **Cheapest:** Tiny model (<10MB)
- **Simplest:** No prompt engineering

**Disadvantages:**
- Requires substantial training data (10k+ examples)
- Less flexible (hard to add new tools - requires retraining)
- Can't extract constraints (need separate model)

---

## Constraint Extraction

**Current:** Separate step after classification  
**Future:** Single model does both

### Example

**Current (2-step):**
```python
# Step 1
token = classifier.classify("Email summary to bob@company.com")
# {send_email: True}

# Step 2
constraints = extract_constraints("Email summary to bob@company.com", "send_email")
# {recipient_whitelist: ["bob@company.com"]}
```

**Future (1-step with FunctionGemma):**
```python
# FunctionGemma outputs both
response = functiongemma.classify("Email summary to bob@company.com")

# Output:
{
  "function_calls": [
    {
      "name": "send_email",
      "arguments": {
        "to": "bob@company.com",  # Extracted!
        "subject": "Summary",
        "body": "..."
      }
    }
  ]
}

# CapGuard validates: is "bob@company.com" in user's org?
```

---

## Proposed Timeline

### Month 1-2: Data Collection
- Synthetic: 5k examples
- Production logs: Start collecting
- Human annotation: 1k edge cases

**Deliverable:** 10k labeled examples

### Month 3: Model Experiments

**Experiment 1:** FunctionGemma (zero-shot)
- No training needed
- Just adapt prompts

**Experiment 2:** Fine-tuned Llama 3
- Train on 10k examples
- Compare vs base Llama 3

**Experiment 3:** SBERT Multi-Label
- Fastest option
- Train neural network

**Evaluation:**
- Accuracy (exact match)
- Per-tool precision/recall
- Latency (p50, p95, p99)
- False negative rate (security critical!)

### Month 4: A/B Test

- 50% traffic: Current LLM
- 50% traffic: Best model

**Metrics:**
- Classification accuracy
- Latency
- User satisfaction
- Attack prevention rate

**Decision:** Roll out if:
- Accuracy >95%
- Latency <100ms p95
- False positive <1%

---

## Open Research Questions

1. **Minimum training data?**
   - Hypothesis: 1k → 90%, 10k → 95%, 100k → 98%
   - Need ablation studies

2. **Handling Concept Drift**
   - Tools added/removed frequently
   - Solution: Continuous learning? Periodic retraining?

3. **Few-Shot Learning**
   - Can model adapt to new tools with 5-10 examples?
   - Meta-learning approaches?

4. **Optimal Model Size**
   - 1B (fast, less accurate) vs 8B (slow, accurate)
   - Target: Sub-100ms on CPU for 3B model

5. **Constraint Extraction**
   - Joint model (classification + constraints) vs separate?
   - FunctionGemma approach vs custom fine-tuning?

---

## Recommendation

**Short-term (v0.1-0.3):** Stick with current approach
- Rules + LLM (Llama 3 via Ollama)
- Free, fast enough, good accuracy

**Medium-term (v0.4-0.6):** Add FunctionGemma
- **Why:** Designed for this task, structured output, fast
- **When:** After validating with 1k production examples
- **Effort:** Low (just change model, no training)

**Long-term (v1.0+):** Fine-tune if needed
- **Why:** Custom to CapGuard's exact tool set
- **When:** After 10k+ users, clear ROI
- **Effort:** High (3 months, data + training)

---

## Success Criteria

**We know it worked if:**
1. ✅ Latency <50ms p95 (vs 200ms now)
2. ✅ Accuracy >98% (vs ~90% now)
3. ✅ Cost $0 (Ollama-compatible)
4. ✅ Reliability: <0.01% parsing errors
5. ✅ User NPS increases

---

## References

- **FunctionGemma:** https://ai.google.dev/gemma/docs/functiongemma
- **Llama 3 Fine-tuning:** https://huggingface.co/meta-llama/Llama-3-8B
- **Sentence-BERT:** https://www.sbert.net/
- **Multi-Label Classification:** https://scikit-learn.org/stable/modules/multiclass.html

---

**Status:** Research direction - not implemented yet  
**Next Step:** Collect 1k production examples, run FunctionGemma pilot

---

## Research Direction 4: Multi-Agent Capability Handling

### Concept
In complex agentic systems, a "Root Agent" (Orchestrator) often spawns "Sub-Agents" (Workers) to handle specific sub-tasks. CapGuard must enforce the **Principle of Least Privilege** across this hierarchy.

### Challenge 1: Capability Inheritance & Transfer
**Scenario:** Root Agent has `{read_all_files: True}`. It spawns a "Summarizer Agent" to summarize *one* file.
**Risk:** If Root Agent passes its full token to Sub-Agent, the Sub-Agent is over-privileged.
**Solution:** **Capability Downscoping (Minting).**

The Root Agent (via CapGuard SDK) requests a *new, narrower* token for the Sub-Agent.

```python
# Root Agent Logic
root_token = context.capability_token

# Mint a restricted token for the worker
worker_token = capguard.mint_sub_token(
    parent_token=root_token,
    constraints={
        "allowed_tools": ["read_file"],
        "file_path_allowlist": ["/data/report.txt"]  # Constraint propagation
    }
)

# Initialize Sub-Agent with restricted token
worker = SubAgent(token=worker_token)
worker.run()
```

### Challenge 2: Parallel Sub-Agent Execution & Privilege Escalation
**Scenario:** Root Agent spawns two parallel workers:
1. `EmailSearcher` (Can read emails)
2. `PublicWebReader` (Can read public web)

**Risk:** If `PublicWebReader` is compromised via prompt injection, it might try to define *new* tools or access shared memory to use `EmailSearcher`'s tools.

**CapGuard Enforcement:**
- **Strict Isolation:** Each parallel execution thread/process is bound to a specific `CapabilityToken`.
- **No Dynamic Capability Granting:** If `PublicWebReader` asks the Orchestrator for "more tools", CapGuard must re-classify the request at the Orchestrator level with the *original* user intent as context.

### Architecture Proposal

```mermaid
graph TD
    User[User Request] --> Orchestrator
    Orchestrator -->|Classify| CapGuard
    CapGuard -->|Token A (Full)| Orchestrator
    
    Orchestrator -->|Mint Token B (Web Only)| SubAgent1[Web Reader]
    Orchestrator -->|Mint Token C (Email Only)| SubAgent2[Email Searcher]
    
    SubAgent1 --x|Blocked: Search Email| MailServer
    SubAgent1 -->|Allowed: Read Web| Internet
    
    SubAgent2 -->|Allowed: Search Email| MailServer
```

**Key Research Item:** Designing the cryptographic or logical `mint_sub_token` protocol to ensure tokens cannot be forged or escalated by sub-agents.
