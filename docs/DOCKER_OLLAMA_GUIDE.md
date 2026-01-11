# Docker & Ollama Integration Guide

This guide explains how to use CapGuard with Ollama (local LLMs) running in Docker. This is the **recommended setup** for development and cost-effective production deployment.

---

## Why Ollama?

| Feature | Ollama | OpenAI API | Anthropic API |
|---------|---------|------------|---------------|
| **Cost** | $0 (free) | ~$0.01/request | ~$0.015/request |
| **Latency** | <100ms (local) | 500-2000ms | 500-2000ms |
| **Privacy** | 100% local | Data sent to OpenAI | Data sent to Anthropic |
| **Offline** | ✅ Works | ❌ Requires internet | ❌ Requires internet |
| **Setup** | Docker compose | API key | API key |

**Bottom line**: Ollama is perfect for development and can handle production workloads when cost/privacy matter.

---

## Quick Start with Ollama

### 1. Install Docker

```bash
# Windows/Mac: Download Docker Desktop
# https://www.docker.com/products/docker-desktop

# Linux:
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
```

### 2. Start Ollama Container

```bash
# Pull and run Ollama
docker run -d -v ollama:/root/.ollama -p 11434:11434 --name ollama ollama/ollama

# Pull a model (e.g., Llama 3)
docker exec -it ollama ollama pull llama3

# Test it works
curl http://localhost:11434/v1/models
```

### 3. Use with CapGuard

```python
from capguard import ToolRegistry, CapabilityEnforcer
from capguard.classifiers import LLMClassifier

# Create classifier pointing to Ollama
classifier = LLMClassifier(
    tool_registry=registry,
    base_url="http://localhost:11434/v1",  # Ollama endpoint
    model="llama3",  # or "mistral", "codellama", etc.
    api_key="ollama"  # Not used, but required by client
)

# Use it - works exactly like OpenAI!
token = classifier.classify("Summarize http://example.com")
print(token.granted_tools)  # {'read_website': True, 'send_email': False}
```

**That's it!** CapGuard abstracts the provider - your code works with Ollama, OpenAI, or Anthropic.

---

## Docker Compose Setup (Production-Ready)

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  ollama:
    image: ollama/ollama:latest
    container_name: capguard-ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama-data:/root/.ollama
    restart: unless-stopped
    # Optional: Use GPU
    # deploy:
    #   resources:
    #     reservations:
    #       devices:
    #         - driver: nvidia
    #           count: 1
    #           capabilities: [gpu]

  # Your CapGuard application
  capguard-app:
    build: .
    depends_on:
      - ollama
    environment:
      - OLLAMA_BASE_URL=http://ollama:11434/v1
      - OLLAMA_MODEL=llama3
volumes:
  ollama-data:
```

Start everything:
```bash
docker-compose up -d

# Pull model
docker-compose exec ollama ollama pull llama3

# View logs
docker-compose logs -f
```

---

## ⚡ enabling GPU Support (Optional but Recommended)

For faster performance, you can use your NVIDIA GPU.

### 1. Prerequisites
- NVIDIA GPU (GTX 1650 or better)
- Latest NVIDIA Drivers
- [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html) installed on host.

### 2. Configure docker-compose.yml
Uncomment the `deploy` section in `examples/docker_full/docker-compose.yml`:

```yaml
services:
  ollama:
    # ... other settings ...
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

### 3. Verification
Check if Ollama is using GPU logs:
```bash
docker-compose logs ollama | grep "NVIDIA"
```
You should see "detected 1 CUDA device".

---

## Model Recommendations

### For Classification (Fast & Accurate)

| Model | Size | Speed | Accuracy | Use Case |
|-------|------|-------|----------|----------|
| **llama3:8b** | 8GB | ⚡⚡⚡ Fast | ✅✅✅ High | **Recommended** |
| mistral:7b | 7GB | ⚡⚡⚡ Fast | ✅✅ Good | Alternative |
| phi-3:mini | 3.8GB | ⚡⚡⚡⚡ Very fast | ✅✅ Good | Low-resource |
| llama3:70b | 70GB | ⚡ Slow | ✅✅✅✅ Excellent | GPU only |

**Recommendation**: Start with `llama3:8b` - best balance of speed/accuracy.

### Pull a model:
```bash
docker exec -it ollama ollama pull llama3:8b
```

---

## Switching Between Providers

CapGuard uses the **OpenAI-compatible API**, so switching is trivial:

### Ollama (local):
```python
classifier = LLMClassifier(
    registry=registry,
    base_url="http://localhost:11434/v1",
    model="llama3",
    api_key="ollama"
)
```

### OpenAI:
```python
classifier = LLMClassifier(
    registry=registry,
    base_url="https://api.openai.com/v1",  # or omit - this is default
    model="gpt-4o-mini",
    api_key=os.getenv("OPENAI_API_KEY")
)
```

### Anthropic (via OpenAI-compatible proxy):
```python
# Use LiteLLM proxy or similar
classifier = LLMClassifier(
    registry=registry,
    base_url="http://localhost:4000",  # LiteLLM
    model="claude-3-haiku-20240307",
    api_key=os.getenv("ANTHROPIC_API_KEY")
)
```

**Your application code doesn't change!**

---

## Performance Tuning

### Classification Latency Optimization

```python
from capguard.classifiers import HybridClassifier, RuleBasedClassifier, LLMClassifier

# Tier 1: Rules (instant, 0ms)
rule_classifier = RuleBasedClassifier(registry, create_default_rules())

# Tier 2: LLM (fast, 50-200ms)
llm_classifier = LLMClassifier(
    registry,
    base_url="http://localhost:11434/v1",
    model="llama3:8b"
)

# Hybrid: Use rules first, LLM as fallback
classifier = HybridClassifier(
    rule_classifier=rule_classifier,
    fallback_classifier=llm_classifier,
    confidence_threshold=0.8
)
```

**Result**: 80% of requests use rules (0ms), 20% use LLM (50-200ms).

### Model Fine-Tuning (Advanced)

Fine-tune Llama 3 on your specific tool set for better accuracy:

```bash
# Create training data (see docs/fine-tuning.md)
# Format: {"request": "...", "tools": ["tool1", "tool2"]}

# Fine-tune with Ollama
ollama create my-capguard-classifier -f Modelfile
```

---

## Monitoring

### Check Ollama Status

```bash
# Is it running?
curl http://localhost:11434/api/tags

# Model info
docker exec -it ollama ollama list

# Logs
docker logs ollama -f
```

### CapGuard Metrics

```python
# Classification latency
import time
start = time.time()
token = classifier.classify(request)
latency_ms = (time.time() - start) * 1000
print(f"Classification took {latency_ms:.2f}ms")

# Audit blocked attempts
blocked = enforcer.get_blocked_attempts()
print(f"Blocked {len(blocked)} unauthorized tool calls")
```

---

## Troubleshooting

### `ConnectionRefusedError: [Errno 61] Connection refused`

**Problem**: Ollama not running  
**Solution**:
```bash
docker start ollama
# Or
docker run -d -p 11434:11434 ollama/ollama
```

### `Model not found: llama3`

**Problem**: Model not pulled  
**Solution**:
```bash
docker exec -it ollama ollama pull llama3
```

### Slow classification (>2 seconds)

**Problem**: Model too large or CPU-only  
**Solution**:
- Use smaller model: `phi-3:mini` instead of `llama3:70b`
- Enable GPU support (see docker-compose above)
- Use hybrid classifier (rules + LLM)

---

## Production Deployment

### Recommended Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Your Application                      │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │          CapGuard Classifier                     │  │
│  │  (Tier 1: Rules → Tier 2: LLM if needed)        │  │
│  └──────────────┬────────────────────────────────────┘  │
│                 │                                        │
│                 ↓                                        │
│  ┌──────────────────────────────────────────────────┐  │
│  │     Ollama (Docker container)                    │  │
│  │     Model: llama3:8b                             │  │
│  │     Endpoint: http://ollama:11434                │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### Scaling

**Horizontal**:
```yaml
services:
  ollama-1:
    image: ollama/ollama
    ports: ["11434:11434"]
  
  ollama-2:
    image: ollama/ollama
    ports: ["11435:11434"]

  # Load balancer in your app
```

**Vertical** (GPU):
```yaml
services:
  ollama:
    image: ollama/ollama
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
```

---

## Cost Comparison (1M Requests)

| Provider | Model | Cost | Latency |
|----------|-------|------|---------|
| **Ollama (local)** | llama3:8b | **$0** | 50-100ms |
| OpenAI | gpt-4o-mini | $150 | 500-1500ms |
| OpenAI | gpt-4o | $1,500 | 1000-3000ms |
| Anthropic | claude-3-haiku | $250 | 500-1500ms |

**For 1M classifications**: Ollama saves **$150-1,500** compared to cloud APIs.

---

## Next Steps

- ✅ **Try the example**: `examples/ollama_demo.py`
- ✅ **Fine-tune a model**: `docs/fine-tuning.md`
- ✅ **Production deployment**: `docs/deployment.md`

**Questions?** Open an issue: https://github.com/capguard/capguard/issues
