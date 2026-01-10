$ErrorActionPreference = "Stop"

$HOST_COMPOSE = "docker-compose.yml"
$AGENT_BASE_IMAGE = "base-agent"
$DEMO_DIR = "examples/secure_agent_demo"

# Ensure we are in root
if (!(Test-Path "pyproject.toml")) {
    Write-Error "Please run from project root (capguard/)"
    exit 1
}

cd $DEMO_DIR

Write-Host "`n=== CapGuard Secure Agent Demo ===" -ForegroundColor Cyan

# 1. Cleanup
Write-Host "[-] Cleaning old containers..." -ForegroundColor Yellow
docker-compose down --remove-orphans
docker rmi $AGENT_BASE_IMAGE -f 2>$null

# 2. Start Infrastructure
Write-Host "[-] Starting Infrastructure (Ollama, Site, MailHog)..." -ForegroundColor Cyan
docker-compose up -d

Write-Host "[-] Waiting for services..." -ForegroundColor Magenta
# Simple wait loop
Start-Sleep -Seconds 5
# Poll MailHog to verify readiness
$Retries = 30
while ($Retries -gt 0) {
    try {
        $resp = Invoke-WebRequest -Uri "http://localhost:8025/api/v2/messages" -UseBasicParsing -TimeoutSec 2
        if ($resp.StatusCode -eq 200) { break }
    } catch {
        Write-Host "." -NoNewline
        Start-Sleep -Seconds 2
        $Retries--
    }
}
Write-Host "`n[+] Infrastructure Ready!" -ForegroundColor Green
Write-Host "    - Malicious Site: http://localhost:8080/index.html"
Write-Host "    - MailHog UI:     http://localhost:8025"

# 3. Build Agents
Write-Host "[-] Building Agent Images..." -ForegroundColor Cyan
# Copy project root context is tricky from subdirectory? 
# We need to build from root context.
cd ../.. # Back to root
# Build Base
docker build -t $AGENT_BASE_IMAGE -f "$DEMO_DIR/agents/Dockerfile.base" .
# Build Vulnerable
docker build -t vulnerable-agent -f "$DEMO_DIR/agents/vulnerable/Dockerfile" "$DEMO_DIR/agents/vulnerable"
# Build Protected
docker build -t protected-agent -f "$DEMO_DIR/agents/protected/Dockerfile" "$DEMO_DIR/agents/protected"

# 4. Run Vulnerable Scenario
Write-Host "`n=== SCENARIO 1: Vulnerable Agent ===" -ForegroundColor Red
Write-Host "Expected Result: Agent reads site, gets hacked, sends email." -ForegroundColor Gray
# Run attached to same network as infrastructure (default bridge of compose)
# We need network name. Usually foldername_default.
$NET_NAME = "secure_agent_demo_default" 
docker run --rm --network $NET_NAME --name v-agent vulnerable-agent

# 5. Run Protected Scenario
Write-Host "`n=== SCENARIO 2: CapGuard Protected Agent ===" -ForegroundColor Green
Write-Host "Expected Result: Agent reads site, TRIES to hack, BLOCKED by CapGuard." -ForegroundColor Gray
docker run --rm --network $NET_NAME --name p-agent protected-agent

# 6. Conclusion
Write-Host "`n[+] Demo Verification:" -ForegroundColor Cyan
Write-Host "1. Check MailHog (http://localhost:8025) -> Should see ONE email from Vulnerable Agent."
Write-Host "2. Protected Agent logs above should show 'PERMISSION DENIED'."

# Cleanup?
# docker-compose -f $DEMO_DIR/docker-compose.yml down
