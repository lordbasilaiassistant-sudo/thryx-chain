"""
Thryx Agent Configuration
Loads deployment addresses and private keys for agents
"""
import os
import json
from pathlib import Path

# RPC URL - Docker internal or localhost
RPC_URL = os.getenv("RPC_URL", "http://127.0.0.1:8545")

# Hardhat default private keys (DO NOT USE IN PRODUCTION)
# These correspond to accounts 2-9 in Hardhat's default accounts
AGENT_PRIVATE_KEYS = {
    "oracle": os.getenv("PRIVATE_KEY_ORACLE", "0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a"),
    "arbitrage": os.getenv("PRIVATE_KEY_ARB", "0x7c852118294e51e653712a81e05800f419141751be58f605c371e15141b007a6"),
    "liquidity": os.getenv("PRIVATE_KEY_LIQ", "0x47e179ec197488593b187f80a00eb0da91f1b9d0b13f8733639f19c30a34926a"),
    "governance": os.getenv("PRIVATE_KEY_GOV", "0x8b3a350cf5c34c9194ca85829a2df0ec3153be0318b5e2d3348e872092edffba"),
    "monitor": os.getenv("PRIVATE_KEY_MON", "0x92db14e403b83dfe3df233f83dfa3a0d7096f21ca9b0d6d6b8d88b2b4ec1564e"),
    "security": os.getenv("PRIVATE_KEY_SEC", "0x4bbbf85ce3377467afe5d46f804f221813b2bb87f24d81f60f1fcdbf7cbf4356"),
    "intent": os.getenv("PRIVATE_KEY_INT", "0xdbda1821b80551c9d65939329250298aa3472ba22feea921c0cf5d620ea67b97"),
}

# Contract addresses - loaded from deployment.json
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
                return
    
    print(f"[CONFIG] Warning: deployment.json not found")
    print("[CONFIG] Using placeholder addresses - run deployment first")
    # Placeholder addresses for testing
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

# ABI fragments for common functions
ERC20_ABI = [
    {"inputs": [{"name": "spender", "type": "address"}, {"name": "amount", "type": "uint256"}], "name": "approve", "outputs": [{"name": "", "type": "bool"}], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"name": "account", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "stateMutability": "view", "type": "function"},
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
