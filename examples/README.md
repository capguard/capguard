# CapGuard Examples

Demonstrations of CapGuard protecting agents against indirect prompt injection.

## Quick Start

| Example | Description | Requirements |
|---------|-------------|--------------|
| `basic_demo.py` | Rule-based classifier, no LLM needed | Python only |
| `ollama_demo.py` | LLM classifier with local Ollama | Docker + Ollama |
| `groq_demo/` | Full Docker demo with Groq API | Docker + Groq API key |
| `secure_agent_demo/` | Full Docker demo with local Ollama | Docker + 5GB disk |

## Running Examples

### Basic Demo (Quickest)
```bash
cd examples
python basic_demo.py
```

### Ollama Demo (Local LLM)
```bash
# Start Ollama first
docker run -d -p 11434:11434 ollama/ollama
docker exec -it $(docker ps -q) ollama pull llama3

# Run demo
python ollama_demo.py
```

### Groq Demo (Fastest Inference)
```powershell
cd groq_demo
cp .env.example .env
# Edit .env with your GROQ_API_KEY
.\run_demo.ps1
```

### Secure Agent Demo (Full Local)
```powershell
cd secure_agent_demo
.\run_demo.ps1
```

## Expected Results

All demos show:
1. **Vulnerable Agent**: Gets tricked by hidden payload, sends unauthorized email
2. **Protected Agent**: CapGuard blocks the attack with "PERMISSION DENIED"
