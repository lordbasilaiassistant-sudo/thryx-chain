# ============================================================
# THRYX: AI-Native Blockchain - Master Startup Script (Windows)
# ============================================================

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  THRYX - AI-Native Blockchain" -ForegroundColor Cyan
Write-Host "  The Home of Autonomous AI Agents" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check Docker
Write-Host "[1/5] Checking Docker..." -ForegroundColor Yellow
$docker = docker --version 2>$null
if (-not $docker) {
    Write-Host "ERROR: Docker not found. Install Docker Desktop first." -ForegroundColor Red
    exit 1
}
Write-Host "  Docker: $docker" -ForegroundColor Green

# Check Docker Compose
Write-Host "[2/5] Checking Docker Compose..." -ForegroundColor Yellow
$compose = docker compose version 2>$null
if (-not $compose) {
    Write-Host "ERROR: Docker Compose not found." -ForegroundColor Red
    exit 1
}
Write-Host "  Docker Compose: $compose" -ForegroundColor Green

# Check if Docker is running
Write-Host "[3/5] Checking Docker daemon..." -ForegroundColor Yellow
$running = docker info 2>$null
if (-not $running) {
    Write-Host "ERROR: Docker daemon not running. Start Docker Desktop." -ForegroundColor Red
    exit 1
}
Write-Host "  Docker daemon running" -ForegroundColor Green

# Build and start
Write-Host "[4/5] Building Thryx ecosystem..." -ForegroundColor Yellow
Write-Host "  This may take a few minutes on first run..." -ForegroundColor Gray

docker compose build

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Build failed" -ForegroundColor Red
    exit 1
}

Write-Host "[5/5] Starting Thryx ecosystem..." -ForegroundColor Yellow
docker compose up -d

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to start containers" -ForegroundColor Red
    exit 1
}

# Wait for services
Write-Host ""
Write-Host "Waiting for services to initialize..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# Show status
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  THRYX ECOSYSTEM LAUNCHED" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Services:" -ForegroundColor Cyan
Write-Host "  Chain RPC:     http://localhost:8545" -ForegroundColor White
Write-Host "  Block Explorer: http://localhost:5100" -ForegroundColor White
Write-Host "  Frontend:       http://localhost:3000" -ForegroundColor White
Write-Host ""
Write-Host "Agents Running:" -ForegroundColor Cyan
Write-Host "  - Oracle Agent (price feeds)" -ForegroundColor White
Write-Host "  - Arbitrage Agent (trading)" -ForegroundColor White
Write-Host "  - Liquidity Agent (LP management)" -ForegroundColor White
Write-Host "  - Governance Agent (voting)" -ForegroundColor White
Write-Host "  - Monitor Agent (health checks)" -ForegroundColor White
Write-Host ""
Write-Host "Commands:" -ForegroundColor Cyan
Write-Host "  View logs:     docker compose logs -f" -ForegroundColor Gray
Write-Host "  Stop:          docker compose down" -ForegroundColor Gray
Write-Host "  Restart:       docker compose restart" -ForegroundColor Gray
Write-Host ""
Write-Host "Open http://localhost:3000 to access Thryx!" -ForegroundColor Yellow
Write-Host ""
