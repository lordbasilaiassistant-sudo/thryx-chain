#!/bin/bash
# THRYX Auto-Start Script for Codespaces
# This runs on codespace start to ensure THRYX is always running

set -e

echo "========================================"
echo "  THRYX AUTO-START"
echo "========================================"

# Wait for Docker to be ready
echo "Waiting for Docker..."
for i in {1..30}; do
  if docker info &>/dev/null; then
    echo "Docker is ready!"
    break
  fi
  sleep 2
done

# Check if THRYX is already running
if docker compose ps 2>/dev/null | grep -q "thryx-node.*running"; then
  echo "THRYX is already running"
  docker compose ps
else
  echo "Starting THRYX..."
  docker compose up -d --build
  
  # Wait for services to be healthy
  echo "Waiting for services to be healthy..."
  sleep 30
  
  docker compose ps
fi

# Start keep-alive loop in background
echo "Starting keep-alive loop..."
nohup bash -c '
while true; do
  # Ping the RPC to keep codespace active
  curl -s http://localhost:8545 -X POST \
    -H "Content-Type: application/json" \
    -d "{\"jsonrpc\":\"2.0\",\"method\":\"eth_blockNumber\",\"params\":[],\"id\":1}" \
    > /dev/null 2>&1 || true
  
  # Check if services are healthy
  if ! docker compose ps | grep -q "thryx-node.*running"; then
    echo "[$(date)] THRYX not running, restarting..."
    docker compose up -d
  fi
  
  # Sleep for 5 minutes
  sleep 300
done
' > /tmp/thryx-keepalive.log 2>&1 &

echo ""
echo "THRYX is running!"
echo "RPC: http://localhost:8545"
echo "Explorer: http://localhost:5100"
echo ""
