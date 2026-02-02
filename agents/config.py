"""
Thryx Agent Configuration
Loads deployment addresses and private keys for agents

SECURITY: All private keys MUST be set via environment variables.
Never hardcode keys in this file!
"""
import os
import sys
import json
from pathlib import Path

# ==================== Environment Validation ====================
def require_env(key: str, description: str = "") -> str:
    """Require an environment variable to be set."""
    value = os.getenv(key)
    if not value:
        print(f"[CONFIG] ERROR: Required environment variable {key} is not set!")
        if description:
            print(f"[CONFIG] {description}")
        print(f"[CONFIG] Set this in your .env file or environment.")
        # In production, we should fail hard. In dev, we can use test keys.
        if os.getenv("THRYX_ENV", "development") == "production":
            sys.exit(1)
        return ""
    return value

def get_env_with_dev_fallback(key: str, dev_fallback: str) -> str:
    """Get env var, with fallback only in development mode."""
    value = os.getenv(key)
    if value:
        return value
    
    if os.getenv("THRYX_ENV", "development") != "production":
        print(f"[CONFIG] Warning: {key} not set, using development fallback")
        return dev_fallback
    
    print(f"[CONFIG] ERROR: {key} required in production!")
    sys.exit(1)

# ==================== Environment Mode ====================
THRYX_ENV = os.getenv("THRYX_ENV", "development")
IS_PRODUCTION = THRYX_ENV == "production"

if IS_PRODUCTION:
    print("[CONFIG] Running in PRODUCTION mode - all keys required")
else:
    print("[CONFIG] Running in DEVELOPMENT mode - using test fallbacks")

# ==================== RPC Configuration ====================
RPC_URL = os.getenv("RPC_URL", "http://127.0.0.1:8545")

# ==================== Agent Private Keys ====================
# In development, these fall back to Hardhat's default test accounts
# In production, they MUST be set via environment variables

# Hardhat default test keys (accounts 2-9) - ONLY for development!
DEV_KEYS = {
    "oracle": "0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a",
    "arbitrage": "0x7c852118294e51e653712a81e05800f419141751be58f605c371e15141b007a6",
    "liquidity": "0x47e179ec197488593b187f80a00eb0da91f1b9d0b13f8733639f19c30a34926a",
    "governance": "0x8b3a350cf5c34c9194ca85829a2df0ec3153be0318b5e2d3348e872092edffba",
    "monitor": "0x92db14e403b83dfe3df233f83dfa3a0d7096f21ca9b0d6d6b8d88b2b4ec1564e",
    "security": "0x4bbbf85ce3377467afe5d46f804f221813b2bb87f24d81f60f1fcdbf7cbf4356",
    "intent": "0xdbda1821b80551c9d65939329250298aa3472ba22feea921c0cf5d620ea67b97",
    "bridge": "0x2a871d0798f97d79848a013d4936a73bf4cc922c825d33c1cf7073dff6d409c6",
    "withdrawal": "0xf214f2b2cd398c806f84e317254e0f0b801d0643303237d97a22a48e01628897",
}

AGENT_PRIVATE_KEYS = {
    "oracle": get_env_with_dev_fallback("PRIVATE_KEY_ORACLE", DEV_KEYS["oracle"]),
    "arbitrage": get_env_with_dev_fallback("PRIVATE_KEY_ARBITRAGE", DEV_KEYS["arbitrage"]),
    "liquidity": get_env_with_dev_fallback("PRIVATE_KEY_LIQUIDITY", DEV_KEYS["liquidity"]),
    "governance": get_env_with_dev_fallback("PRIVATE_KEY_GOVERNANCE", DEV_KEYS["governance"]),
    "monitor": get_env_with_dev_fallback("PRIVATE_KEY_MONITOR", DEV_KEYS["monitor"]),
    "security": get_env_with_dev_fallback("PRIVATE_KEY_SECURITY", DEV_KEYS["security"]),
    "intent": get_env_with_dev_fallback("PRIVATE_KEY_INTENT", DEV_KEYS["intent"]),
    "bridge": get_env_with_dev_fallback("PRIVATE_KEY_BRIDGE", DEV_KEYS["bridge"]),
    "withdrawal": get_env_with_dev_fallback("PRIVATE_KEY_WITHDRAWAL", DEV_KEYS["withdrawal"]),
}

# ==================== Contract Addresses ====================
CONTRACTS = {}
AGENTS = {}

def load_deployment():
    """Load contract addresses from deployment.json"""
    global CONTRACTS, AGENTS
    
    # Try multiple locations
    possible_paths = [
        Path("/app/deployment.json"),  # Docker container
        Path(__file__).parent / "deployment.json",  # Same directory
        Path(__file__).parent.parent / "deployment.json",  # Parent directory
        Path("deployment.json"),  # Current working directory
    ]
    
    for deployment_path in possible_paths:
        if deployment_path.exists():
            with open(deployment_path) as f:
                data = json.load(f)
                CONTRACTS = data.get("contracts", {})
                AGENTS = data.get("agents", {})
                print(f"[CONFIG] Loaded deployment from {deployment_path}")
                print(f"[CONFIG] Contracts: {len(CONTRACTS)}, Agents: {len(AGENTS)}")
                return
    
    print(f"[CONFIG] Warning: deployment.json not found")
    print("[CONFIG] Using placeholder addresses - run deployment first")
    CONTRACTS = {
        "MockUSDC": "0x0000000000000000000000000000000000000000",
        "MockWETH": "0x0000000000000000000000000000000000000000",
        "AgentRegistry": "0x0000000000000000000000000000000000000000",
        "StablecoinGas": "0x0000000000000000000000000000000000000000",
        "SimpleAMM": "0x0000000000000000000000000000000000000000",
        "AgentOracle": "0x0000000000000000000000000000000000000000",
        "IntentMempool": "0x0000000000000000000000000000000000000000",
    }

# Load on import
load_deployment()

# ==================== ABI Fragments ====================
ERC20_ABI = [
    {"inputs": [{"name": "spender", "type": "address"}, {"name": "amount", "type": "uint256"}], "name": "approve", "outputs": [{"name": "", "type": "bool"}], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"name": "account", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"name": "to", "type": "address"}, {"name": "amount", "type": "uint256"}], "name": "transfer", "outputs": [{"name": "", "type": "bool"}], "stateMutability": "nonpayable", "type": "function"},
]

AGENT_REGISTRY_ABI = [
    {"inputs": [{"name": "agentAddress", "type": "address"}], "name": "validateAgent", "outputs": [{"name": "", "type": "bool"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"name": "agentAddress", "type": "address"}], "name": "getRemainingBudget", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "getAgentCount", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "getActiveAgents", "outputs": [{"name": "", "type": "address[]"}], "stateMutability": "view", "type": "function"},
]

AGENT_ORACLE_ABI = [
    {"inputs": [{"name": "pair", "type": "bytes32"}, {"name": "price", "type": "uint256"}], "name": "submitPrice", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"name": "pair", "type": "bytes32"}], "name": "getPrice", "outputs": [{"name": "price", "type": "uint256"}, {"name": "timestamp", "type": "uint256"}, {"name": "isStale", "type": "bool"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"name": "pair", "type": "bytes32"}], "name": "getSubmissionCount", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
]

SIMPLE_AMM_ABI = [
    {"inputs": [{"name": "tokenIn", "type": "address"}, {"name": "amountIn", "type": "uint256"}, {"name": "minAmountOut", "type": "uint256"}], "name": "swap", "outputs": [{"name": "amountOut", "type": "uint256"}], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"name": "amountA", "type": "uint256"}, {"name": "amountB", "type": "uint256"}], "name": "addLiquidity", "outputs": [{"name": "liquidity", "type": "uint256"}], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"name": "tokenIn", "type": "address"}, {"name": "amountIn", "type": "uint256"}], "name": "getAmountOut", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "getPrice", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "reserveA", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "reserveB", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
]

L2_WITHDRAWAL_ABI = [
    {"inputs": [{"name": "amount", "type": "uint256"}], "name": "initiateWithdrawal", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"name": "withdrawalId", "type": "uint256"}], "name": "getWithdrawal", "outputs": [{"name": "user", "type": "address"}, {"name": "amount", "type": "uint256"}, {"name": "timestamp", "type": "uint256"}, {"name": "processed", "type": "bool"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "getPendingWithdrawals", "outputs": [{"name": "", "type": "uint256[]"}], "stateMutability": "view", "type": "function"},
]

# ==================== Metrics Configuration ====================
METRICS_ENABLED = os.getenv("PROMETHEUS_ENABLED", "false").lower() == "true"
METRICS_PORT = int(os.getenv("METRICS_PORT", "9090"))

# ==================== Alert Configuration ====================
ALERT_WEBHOOK_URL = os.getenv("ALERT_WEBHOOK_URL", "")

def send_alert(message: str, severity: str = "info"):
    """Send alert to webhook if configured."""
    if not ALERT_WEBHOOK_URL:
        print(f"[ALERT][{severity.upper()}] {message}")
        return
    
    import requests
    try:
        requests.post(ALERT_WEBHOOK_URL, json={
            "content": f"**[{severity.upper()}]** {message}",
            "embeds": [{
                "title": f"THRYX Alert - {severity.upper()}",
                "description": message,
                "color": {"critical": 0xFF0000, "warning": 0xFFA500, "info": 0x00FF00}.get(severity, 0x808080)
            }]
        }, timeout=5)
    except Exception as e:
        print(f"[ALERT] Failed to send alert: {e}")
