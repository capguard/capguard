# CapGuard Test Suite

This directory contains the entire test suite for CapGuard.

## 1. Quick Start

Run standard unit tests (no extra dependencies):
```bash
pytest tests/test_core.py tests/test_decorators.py
```

## 2. Test Structure

| File | Purpose | Deps |
|------|---------|------|
| `test_core.py` | Core logic (Registry, Enforcer) | standard |
| `test_decorators.py` | Decorator pattern logic | standard |
| `test_langchain.py` | LangChain integration | `langchain` |
| `test_llm_classifier.py` | Real LLM classification | `openai`/`groq` |

## 3. Running Integration Tests

### LangChain Tests
Requires `langchain` package installed:
```bash
pip install langchain langchain-openai langchain-community
pytest tests/test_langchain.py
```

### LLM Classifier Tests
Requires API keys or local Ollama:

**With Groq (Fastest):**
```bash
export GROQ_API_KEY=your_key
pytest tests/test_llm_classifier.py
```

**With Ollama (Local):**
```bash
export RUN_OLLAMA_TESTS=true
pytest tests/test_llm_classifier.py
```

## 4. Run Everything in Docker (Recommended)
You can run the full suite using the base agent image:

```bash
docker build -t capguard-test -f tests/Dockerfile .
docker run --env-file .env capguard-test
```
