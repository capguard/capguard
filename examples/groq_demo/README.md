# CapGuard Demo with Groq

This demo shows CapGuard protecting against indirect prompt injection, using **Groq** for ultra-fast inference.

## Setup

1. **Copy environment file:**
   ```bash
   cp .env.example .env
   ```

2. **Add your Groq API key:**
   Edit `.env` and add your key from https://console.groq.com/keys

3. **Run the demo:**
   ```powershell
   .\run_demo.ps1
   ```

## Configuration

The demo supports multiple LLM providers via `.env`:

```bash
CAPGUARD_PROVIDER=groq          # groq, openai, or ollama
CAPGUARD_MODEL=llama-3.3-70b-versatile
CAPGUARD_DEBUG=false             # Set to 'true' for verbose logging
```

## Debug Mode

Enable debug mode to see the full classification process:

```powershell
# In .env
CAPGUARD_DEBUG=true
```

You'll see:
- System prompt sent to LLM
- User prompt with tool descriptions
- Raw JSON response from LLM
- Parsed capability token

## Expected Results

**Scenario 1 (Vulnerable):** Agent gets tricked, sends email  
**Scenario 2 (Protected):** CapGuard blocks with "PERMISSION DENIED"

Check MailHog at http://localhost:8025 - only vulnerable agent's email should appear.
