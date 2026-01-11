# CapGuard Demo - Quick Start

## ⚠️ Important
**If you see "error during connect", RESTART DOCKER DESKTOP.**

## Running the Demo

1. **Open PowerShell** in this directory.
2. Run the orchestration script:
    ```powershell
    .\run_scenario.ps1
    ```
3. **Monitor Output:**
    - The script will start Ollama, MailHog, and the Malicious Site.
    - It will wait for health checks.
    - It will run the demo automatically.

## Verification
- **MailHog UI:** [http://localhost:8025](http://localhost:8025) (See seeded emails and stolen data).
- **Malicious Site:** [http://localhost:8080/index.html](http://localhost:8080/index.html).

## Troubleshooting
- **Recipe Site Resolution Failed:**
  - We use the default docker network and internal port 8080.
  - If it fails, ensure no other service is using port 8080 on your host.
- **Docker Daemon Error:**
  - Restart Docker Desktop completely.
