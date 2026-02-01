"""
Thryx Contract Helpers
High-level wrappers for Thryx smart contracts
"""
from typing import Optional, Tuple, List
from web3 import Web3


class AgentRegistry:
    """Helper for interacting with AgentRegistry contract"""
    
    ABI = [
        {"inputs": [{"name": "agentAddress", "type": "address"}], "name": "validateAgent", "outputs": [{"name": "", "type": "bool"}], "stateMutability": "view", "type": "function"},
        {"inputs": [{"name": "agentAddress", "type": "address"}], "name": "getRemainingBudget", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
        {"inputs": [], "name": "getAgentCount", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
        {"inputs": [], "name": "getActiveAgents", "outputs": [{"name": "", "type": "address[]"}], "stateMutability": "view", "type": "function"},
        {"inputs": [{"name": "agentAddress", "type": "address"}, {"name": "dailyBudget", "type": "uint256"}, {"name": "permissions", "type": "bytes32"}, {"name": "metadata", "type": "string"}], "name": "registerAgent", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    ]
    
    def __init__(self, chain):
        self.chain = chain
        self.contract = chain.get_contract("AgentRegistry", self.ABI)
    
    def is_valid(self, address: str = None) -> bool:
        """Check if agent is valid and active"""
        addr = address or self.chain.address
        return self.chain.call_contract(self.contract, "validateAgent", addr)
    
    def get_remaining_budget(self, address: str = None) -> int:
        """Get remaining daily budget in USDC (6 decimals)"""
        addr = address or self.chain.address
        return self.chain.call_contract(self.contract, "getRemainingBudget", addr)
    
    def get_agent_count(self) -> int:
        """Get total number of registered agents"""
        return self.chain.call_contract(self.contract, "getAgentCount")
    
    def get_active_agents(self) -> List[str]:
        """Get list of active agent addresses"""
        return self.chain.call_contract(self.contract, "getActiveAgents")
    
    def register(self, daily_budget: int, permissions: str, metadata: str) -> Optional[str]:
        """Register self as an agent"""
        perm_hash = Web3.keccak(text=permissions)
        tx = self.chain.build_tx(self.contract, "registerAgent", 
                                  self.chain.address, daily_budget, perm_hash, metadata)
        return self.chain.send_transaction(tx)


class SimpleAMM:
    """Helper for interacting with SimpleAMM contract"""
    
    ABI = [
        {"inputs": [{"name": "tokenIn", "type": "address"}, {"name": "amountIn", "type": "uint256"}, {"name": "minAmountOut", "type": "uint256"}], "name": "swap", "outputs": [{"name": "amountOut", "type": "uint256"}], "stateMutability": "nonpayable", "type": "function"},
        {"inputs": [{"name": "amountA", "type": "uint256"}, {"name": "amountB", "type": "uint256"}], "name": "addLiquidity", "outputs": [{"name": "liquidity", "type": "uint256"}], "stateMutability": "nonpayable", "type": "function"},
        {"inputs": [{"name": "tokenIn", "type": "address"}, {"name": "amountIn", "type": "uint256"}], "name": "getAmountOut", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
        {"inputs": [], "name": "getPrice", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
        {"inputs": [], "name": "reserveA", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
        {"inputs": [], "name": "reserveB", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
    ]
    
    def __init__(self, chain):
        self.chain = chain
        self.contract = chain.get_contract("SimpleAMM", self.ABI)
    
    def get_price(self) -> float:
        """Get current pool price (WETH in terms of USDC)"""
        price_raw = self.chain.call_contract(self.contract, "getPrice")
        return price_raw / 1e18
    
    def get_reserves(self) -> Tuple[int, int]:
        """Get pool reserves (USDC, WETH)"""
        reserve_a = self.chain.call_contract(self.contract, "reserveA")
        reserve_b = self.chain.call_contract(self.contract, "reserveB")
        return (reserve_a, reserve_b)
    
    def get_amount_out(self, token_in: str, amount_in: int) -> int:
        """Calculate expected output for a swap"""
        return self.chain.call_contract(self.contract, "getAmountOut", token_in, amount_in)
    
    def swap(self, token_in: str, amount_in: int, min_out: int = 0, slippage: float = 0.01) -> Optional[str]:
        """
        Execute a swap.
        
        Args:
            token_in: Address of input token
            amount_in: Amount to swap (in token's smallest unit)
            min_out: Minimum output (0 = calculate with slippage)
            slippage: Slippage tolerance (default 1%)
        """
        if min_out == 0:
            expected = self.get_amount_out(token_in, amount_in)
            min_out = int(expected * (1 - slippage))
        
        tx = self.chain.build_tx(self.contract, "swap", token_in, amount_in, min_out)
        return self.chain.send_transaction(tx)


class AgentOracle:
    """Helper for interacting with AgentOracle contract"""
    
    ABI = [
        {"inputs": [{"name": "pair", "type": "bytes32"}, {"name": "price", "type": "uint256"}], "name": "submitPrice", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
        {"inputs": [{"name": "pair", "type": "bytes32"}], "name": "getPrice", "outputs": [{"name": "price", "type": "uint256"}, {"name": "timestamp", "type": "uint256"}, {"name": "isStale", "type": "bool"}], "stateMutability": "view", "type": "function"},
        {"inputs": [{"name": "pair", "type": "bytes32"}], "name": "getSubmissionCount", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
    ]
    
    def __init__(self, chain):
        self.chain = chain
        self.contract = chain.get_contract("AgentOracle", self.ABI)
    
    @staticmethod
    def pair_hash(pair: str) -> bytes:
        """Convert pair string to bytes32 hash"""
        return Web3.keccak(text=pair)
    
    def get_price(self, pair: str) -> Tuple[float, int, bool]:
        """
        Get price for a pair.
        
        Args:
            pair: Pair string like "ETH/USD"
            
        Returns:
            (price, timestamp, is_stale)
        """
        pair_hash = self.pair_hash(pair)
        result = self.chain.call_contract(self.contract, "getPrice", pair_hash)
        return (result[0] / 1e8, result[1], result[2])
    
    def submit_price(self, pair: str, price: float) -> Optional[str]:
        """
        Submit a price to the oracle.
        
        Args:
            pair: Pair string like "ETH/USD"
            price: Price value (will be scaled to 8 decimals)
        """
        pair_hash = self.pair_hash(pair)
        price_scaled = int(price * 1e8)
        tx = self.chain.build_tx(self.contract, "submitPrice", pair_hash, price_scaled)
        return self.chain.send_transaction(tx)
    
    def get_submission_count(self, pair: str) -> int:
        """Get number of price submissions for a pair"""
        pair_hash = self.pair_hash(pair)
        return self.chain.call_contract(self.contract, "getSubmissionCount", pair_hash)


class IntentMempool:
    """Helper for interacting with IntentMempool contract"""
    
    ABI = [
        {"inputs": [{"name": "goal", "type": "bytes32"}, {"name": "constraints", "type": "bytes"}, {"name": "maxCost", "type": "uint256"}, {"name": "deadlineSeconds", "type": "uint256"}], "name": "submitIntent", "outputs": [{"name": "intentId", "type": "uint256"}], "stateMutability": "nonpayable", "type": "function"},
        {"inputs": [{"name": "intentId", "type": "uint256"}, {"name": "solution", "type": "bytes"}, {"name": "actualCost", "type": "uint256"}], "name": "fulfillIntent", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
        {"inputs": [], "name": "getPendingIntents", "outputs": [{"name": "", "type": "uint256[]"}], "stateMutability": "view", "type": "function"},
    ]
    
    def __init__(self, chain):
        self.chain = chain
        self.contract = chain.get_contract("IntentMempool", self.ABI)
    
    def get_pending_intents(self) -> List[int]:
        """Get list of pending intent IDs"""
        return self.chain.call_contract(self.contract, "getPendingIntents")
    
    def submit_intent(self, goal: str, constraints: str, max_cost: int, deadline_seconds: int) -> Optional[int]:
        """Submit a new intent"""
        goal_hash = Web3.keccak(text=goal)
        constraints_bytes = constraints.encode()
        tx = self.chain.build_tx(self.contract, "submitIntent", 
                                  goal_hash, constraints_bytes, max_cost, deadline_seconds)
        result = self.chain.send_transaction(tx)
        # Would parse intent ID from receipt
        return result
    
    def fulfill_intent(self, intent_id: int, solution: str, actual_cost: int) -> Optional[str]:
        """Fulfill a pending intent"""
        solution_bytes = solution.encode()
        tx = self.chain.build_tx(self.contract, "fulfillIntent",
                                  intent_id, solution_bytes, actual_cost)
        return self.chain.send_transaction(tx)
