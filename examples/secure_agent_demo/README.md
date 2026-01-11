# Secure Agent Demo (Ollama)

Demonstrates CapGuard protection against indirect prompt injection using local Ollama LLM.

## Prerequisites
- Docker Desktop
- ~5GB disk for Ollama model

## Run

```powershell
.\run_demo.ps1
```

## Components
- **Ollama**: Local LLM (llama3 model)
- **Archive Server**: Hosts malicious webpage with injection payload
- **MailHog**: Captures emails at http://localhost:8025

## Expected Results
1. **Vulnerable Agent**: Gets tricked, sends email to MailHog
2. **Protected Agent**: CapGuard blocks with "PERMISSION DENIED"

## See Also
- `examples/groq_demo/` - Faster version using Groq API
