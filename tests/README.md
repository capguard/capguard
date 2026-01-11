# CapGuard Tests

Unit and integration tests for CapGuard.

## Running Tests

```bash
# All tests (skip LLM integration by default)
pytest -v

# Include LLM integration tests
RUN_OLLAMA_TESTS=true pytest -v

# With specific provider
GROQ_API_KEY=your-key pytest tests/test_llm_classifier.py -v
```

## Test Files

| File | Description |
|------|-------------|
| `test_core.py` | ToolRegistry, CapabilityEnforcer |
| `test_classifiers.py` | RuleBasedClassifier |
| `test_llm_classifier.py` | LLMClassifier (multi-provider) |
| `conftest.py` | Shared fixtures, provider config |

## Provider Support

Tests can run against multiple LLM providers:
- **Ollama**: Set `RUN_OLLAMA_TESTS=true`
- **Groq**: Set `GROQ_API_KEY=xxx`
- **OpenAI**: Set `OPENAI_API_KEY=xxx`
