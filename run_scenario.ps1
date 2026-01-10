# CapGuard Demo Orchestration Script
# Automates setup, cleanup, and interactive execution of the CapGuard demo.

$ErrorActionPreference = "Stop"

# Configuration
$COMPOSE_FILE = "examples/docker_full/docker-compose.yml"
$OLLAMA_URL = "http://localhost:11434"
$MODEL_NAME = "llama3"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "   CapGuard Demo Orchestration v1.0" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# 1. Cleanup
Write-Host "`n[-] Cleaning up previous containers..." -ForegroundColor Yellow
docker-compose -f $COMPOSE_FILE down --remove-orphans
# docker rm -f capguard-demo-runner capguard-ollama capguard-recipe-site capguard-mailhog 2>$null

# 2. Start Infrastructure (Ollama, Recipe Site, MailHog)
Write-Host "[-] Starting infrastructure..." -ForegroundColor Cyan
docker-compose -f $COMPOSE_FILE up -d --build ollama recipe-site mailhog
# Note: Using service names from compose

# 3. Wait for Ollama
Write-Host "[-] Waiting for Ollama ($OLLAMA_URL)..." -ForegroundColor Yellow
$retries = 0
$ollamaUp = $false
do {
    try {
        $response = Invoke-WebRequest -Uri "$OLLAMA_URL" -Method Head -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) { $ollamaUp = $true }
    } catch {
        Start-Sleep -Seconds 2
        $retries++
        Write-Host "." -NoNewline
        if ($retries -gt 45) { 
            Write-Error "Ollama failed to start."
            exit 1 
        }
    }
} until ($ollamaUp)
Write-Host "`n[+] Ollama is UP." -ForegroundColor Green

# 4. Check/Pull Model
Write-Host "[-] Checking for model '$MODEL_NAME'..." -ForegroundColor Yellow
# We execute command inside container to check
$models = docker exec capguard-ollama ollama list
if ($models -match $MODEL_NAME) {
    Write-Host "[+] Model '$MODEL_NAME' is present." -ForegroundColor Green
} else {
    Write-Host "[!] Pulling '$MODEL_NAME' (This may take a while)..." -ForegroundColor Magenta
    docker exec capguard-ollama ollama pull $MODEL_NAME
    Write-Host "[+] Model pulled successfully." -ForegroundColor Green
}

# 5. Build Demo Runner
Write-Host "[-] Building Demo Runner..." -ForegroundColor Cyan
docker-compose -f $COMPOSE_FILE build demo-runner

# 6. Interactive Step
Write-Host "`n[READY] Infrastructure is live." -ForegroundColor Green
Write-Host "  - Malicious Site: http://localhost:8080/index.html"
Write-Host "  - MailHog UI:     http://localhost:8025"
Write-Host "`n[ACTION] Open these URLs in your browser to observe."
# Read-Host "Press ENTER to RUN THE DEMO (Vulnerable vs Protected)..."

# 7. Run Demo
Write-Host "[-] Running Demo..." -ForegroundColor Cyan
# IMPORANT: using 'up' guarantees correct network attachment as defined in yaml
docker-compose -f $COMPOSE_FILE up --force-recreate demo-runner

Write-Host "`n[+] Demo Complete." -ForegroundColor Green
