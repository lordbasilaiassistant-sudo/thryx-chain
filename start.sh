#!/bin/bash
# ============================================================
# THRYX: AI-Native Blockchain - Master Startup Script (Linux/Mac)
# ============================================================

set -e

echo ""
echo "========================================"
echo "  THRYX - AI-Native Blockchain"
echo "  The Home of Autonomous AI Agents"
echo "========================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Check Docker
echo -e "${YELLOW}[1/5] Checking Docker...${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${RED}ERROR: Docker not found. Install Docker first.${NC}"
    exit 1
fi
echo -e "${GREEN}  Docker: $(docker --version)${NC}"

# Check Docker Compose
echo -e "${YELLOW}[2/5] Checking Docker Compose...${NC}"
if ! docker compose version &> /dev/null; then
    echo -e "${RED}ERROR: Docker Compose not found.${NC}"
    exit 1
fi
echo -e "${GREEN}  $(docker compose version)${NC}"

# Check if Docker daemon is running
echo -e "${YELLOW}[3/5] Checking Docker daemon...${NC}"
if ! docker info &> /dev/null; then
    echo -e "${RED}ERROR: Docker daemon not running. Start Docker first.${NC}"
    exit 1
fi
echo -e "${GREEN}  Docker daemon running${NC}"

# Build
echo -e "${YELLOW}[4/5] Building Thryx ecosystem...${NC}"
echo "  This may take a few minutes on first run..."
docker compose build

# Start
echo -e "${YELLOW}[5/5] Starting Thryx ecosystem...${NC}"
docker compose up -d

# Wait
echo ""
echo "Waiting for services to initialize..."
sleep 10

# Status
echo ""
echo -e "${GREEN}========================================"
echo "  THRYX ECOSYSTEM LAUNCHED"
echo "========================================${NC}"
echo ""
echo -e "${CYAN}Services:${NC}"
echo "  Chain RPC:      http://localhost:8545"
echo "  Block Explorer: http://localhost:5100"
echo "  Frontend:       http://localhost:3000"
echo ""
echo -e "${CYAN}Agents Running:${NC}"
echo "  - Oracle Agent (price feeds)"
echo "  - Arbitrage Agent (trading)"
echo "  - Liquidity Agent (LP management)"
echo "  - Governance Agent (voting)"
echo "  - Monitor Agent (health checks)"
echo ""
echo -e "${CYAN}Commands:${NC}"
echo "  View logs:  docker compose logs -f"
echo "  Stop:       docker compose down"
echo "  Restart:    docker compose restart"
echo ""
echo -e "${YELLOW}Open http://localhost:3000 to access Thryx!${NC}"
echo ""
