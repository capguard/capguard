$ErrorActionPreference = "Stop"

# --- Configuration ---
$AGENT_BASE_IMAGE = "base-agent"
$NET_NAME = "secure_agent_demo_default" # Default network created by compose

# --- Path Resolution ---
# Resolve paths relative to the script location to allow running from anywhere
$SCRIPT_PATH = $MyInvocation.MyCommand.Path
$SCRIPT_DIR = Split-Path $SCRIPT_PATH
$PROJECT_ROOT = Resolve-Path "$SCRIPT_DIR/../../"
$DEMO_DIR = $SCRIPT_DIR # The directory containing this script and docker-compose.yml

Write-Host "[-] Setting context to Project Root: $PROJECT_ROOT" -ForegroundColor Gray

# --- Helper Functions ---
function Remove-DockerImage {
    param([string]$ImageName)
    $img = docker images -q $ImageName
    if ($img) {
        Write-Host "Removing image: $ImageName" -ForegroundColor Yellow
        docker rmi $ImageName -f | Out-Null
    }
}

# --- Main Execution ---

Write-Host "`n=== CapGuard Secure Agent Demo ===" -ForegroundColor Cyan
Write-Host "Working Directory: $DEMO_DIR" -ForegroundColor Gray

# 1. Cleanup
Write-Host "`n[1/6] Cleaning up..." -ForegroundColor Yellow
Set-Location $DEMO_DIR
try {
    docker-compose down --remove-orphans
} catch {
    Write-Warning "Docker compose down failed or no containers running."
}

# Remove base image if it exists (safe)
Remove-DockerImage $AGENT_BASE_IMAGE
Remove-DockerImage "vulnerable-agent"
Remove-DockerImage "protected-agent"

# 2. Start Infrastructure
Write-Host "`n[2/6] Starting Infrastructure (Ollama, Archive, MailHog)..." -ForegroundColor Cyan
try {
    # Build and start infrastructure
    docker-compose up -d --build
} catch {
    Write-Error "Failed to start infrastructure. Is Docker Desktop running?"
    exit 1
}

Write-Host "[-] Waiting for services to be ready..." -ForegroundColor Magenta
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
if ($Retries -eq 0) {
    Write-Error "Timeout waiting for MailHog. infrastructure might be unhealthy."
    # Continue anyway, MailHog might be slow but Ollama is crucial
}

Write-Host "`n[+] Infrastructure Ready!" -ForegroundColor Green
Write-Host "    - Article Archive: http://localhost:8080/tomato.html"
Write-Host "    - MailHog UI:      http://localhost:8025"

# Ensure Model is Pulled
Write-Host "[-] checking Ollama model (llama3)..." -ForegroundColor Magenta
try {
    # Pulling model inside the container
    docker exec demo-ollama ollama pull llama3
} catch {
    Write-Error "Failed to pull llama3 model in ollama container."
    exit 1
}

# 3. Build Base Agent
Write-Host "`n[3/6] Building Base Agent Image..." -ForegroundColor Cyan
Set-Location $PROJECT_ROOT
# Build Base from root context to access 'capguard' package
docker build -t $AGENT_BASE_IMAGE -f "$DEMO_DIR/agents/Dockerfile.base" .
if ($LASTEXITCODE -ne 0) { Write-Error "Failed to build base-agent"; exit 1 }

# 4. Build Specific Agents
Write-Host "`n[4/6] Building Agent Implementations..." -ForegroundColor Cyan
# Vulnerable
docker build -t vulnerable-agent -f "$DEMO_DIR/agents/vulnerable/Dockerfile" "$DEMO_DIR/agents/vulnerable"
if ($LASTEXITCODE -ne 0) { Write-Error "Failed to build vulnerable-agent"; exit 1 }

# Protected
docker build -t protected-agent -f "$DEMO_DIR/agents/protected/Dockerfile" "$DEMO_DIR/agents/protected"
if ($LASTEXITCODE -ne 0) { Write-Error "Failed to build protected-agent"; exit 1 }

# 5. Run Vulnerable Scenario
Write-Host "`n[5/6] === SCENARIO 1: Vulnerable Agent ===" -BackgroundColor Red -ForegroundColor White
Write-Host "Expected Result: Agent reads site, gets hacked, sends email." -ForegroundColor Gray
Write-Host "Running container attached to network: $NET_NAME" -ForegroundColor Gray

# Check if network exists
if (!(docker network ls -q -f name=$NET_NAME)) {
    Write-Warning "Network $NET_NAME not found. Docker compose might have named it differently."
    Write-Host "Available networks:"
    docker network ls
    Write-Error "Cannot proceed without correct network."
    exit 1
}

docker run --rm --network $NET_NAME --name v-agent vulnerable-agent

# 6. Run Protected Scenario
Write-Host "`n[6/6] === SCENARIO 2: CapGuard Protected Agent ===" -BackgroundColor Green -ForegroundColor White
Write-Host "Expected Result: Agent reads site, TRIES to hack, BLOCKED by CapGuard." -ForegroundColor Gray
docker run --rm --network $NET_NAME --name p-agent protected-agent

# 7. Conclusion
Write-Host "`n[+] Demo Complete!" -ForegroundColor Green
Write-Host "1. Check MailHog (http://localhost:8025) -> Should see ONE email from Vulnerable Agent."
Write-Host "2. Protected Agent logs above should show 'PERMISSION DENIED'."
