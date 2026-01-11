# Groq Demo - CapGuard Protection Demo
# Runs fast with external Groq API (no local Ollama needed)

$SCRIPT_DIR = Split-Path $MyInvocation.MyCommand.Path
$PROJECT_ROOT = Resolve-Path "$SCRIPT_DIR/../../"
$NET_NAME = "capguard-decorator-net"

Write-Host "`n=== CapGuard Groq Demo ===" -ForegroundColor Cyan

# Read API key from .env
$GROQ_API_KEY = ""
if (Test-Path "$SCRIPT_DIR/.env") {
    Get-Content "$SCRIPT_DIR/.env" | ForEach-Object {
        if ($_ -match '^GROQ_API_KEY=(.+)$') {
            $GROQ_API_KEY = $matches[1].Trim()
        }
    }
}
if (-not $GROQ_API_KEY) {
    Write-Host "ERROR: GROQ_API_KEY not found in .env" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] API key loaded" -ForegroundColor Green

# 1. Cleanup old containers
Write-Host "`n[1/5] Cleanup..." -ForegroundColor Yellow
docker rm -f demo-archive demo-mailhog v-agent p-agent 2>$null

# 2. Start infrastructure
Write-Host "[2/5] Starting infrastructure..." -ForegroundColor Yellow
Set-Location $SCRIPT_DIR
docker-compose up -d --build 2>$null
Start-Sleep 3
Write-Host "  Archive: http://localhost:8080/tomato.html"
Write-Host "  MailHog: http://localhost:8025"

# 3. Build base image
Write-Host "[3/5] Building base image..." -ForegroundColor Yellow
Set-Location $PROJECT_ROOT
docker build -t base-agent -f "$SCRIPT_DIR/agents/Dockerfile.base" . 2>$null

# 4. Build agents
Write-Host "[4/5] Building agents..." -ForegroundColor Yellow
docker build -t vulnerable-agent "$SCRIPT_DIR/agents/vulnerable" 2>$null
docker build -t protected-agent "$SCRIPT_DIR/agents/protected" 2>$null

# 5. Run scenarios
Write-Host "`n[5/5] Running scenarios..." -ForegroundColor Yellow

Write-Host "`n--- VULNERABLE AGENT ---" -ForegroundColor Red
docker run --rm --network $NET_NAME -e GROQ_API_KEY=$GROQ_API_KEY --name v-agent vulnerable-agent

Write-Host "`n--- PROTECTED AGENT (CapGuard) ---" -ForegroundColor Green
docker run --rm --network $NET_NAME -e GROQ_API_KEY=$GROQ_API_KEY --name p-agent protected-agent

Write-Host "`n=== Demo Complete ===" -ForegroundColor Cyan
Write-Host "Check MailHog: http://localhost:8025"
Write-Host "Vulnerable should have sent email, Protected should show PERMISSION DENIED"
