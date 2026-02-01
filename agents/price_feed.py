"""
THRYX Price Feed
Provides ETH/USDC price conversion for all agents
"""
import os
import json
from web3 import Web3

RPC_URL = os.getenv("RPC_URL", "http://thryx-node:8545")

# SimpleAMM ABI (just what we need for price)
AMM_ABI = [
    {"name": "getPrice", "type": "function", "stateMutability": "view",
     "inputs": [], "outputs": [{"name": "", "type": "uint256"}]},
    {"name": "reserveA", "type": "function", "stateMutability": "view",
     "inputs": [], "outputs": [{"name": "", "type": "uint256"}]},
    {"name": "reserveB", "type": "function", "stateMutability": "view",
     "inputs": [], "outputs": [{"name": "", "type": "uint256"}]},
]


class PriceFeed:
    """Provides ETH price in USDC terms"""
    
    # Default fallback price if AMM not available
    DEFAULT_ETH_PRICE = 2500  # $2500 per ETH
    
    def __init__(self, rpc_url=None):
        self.w3 = Web3(Web3.HTTPProvider(rpc_url or RPC_URL))
        self.deployment = self._load_deployment()
        self._cached_price = None
        self._cache_time = 0
        self.cache_duration = 30  # Cache price for 30 seconds
    
    def _load_deployment(self):
        try:
            with open("/app/deployment.json", "r") as f:
                return json.load(f)
        except:
            return {"contracts": {}}
    
    def get_amm_contract(self):
        """Get SimpleAMM contract instance"""
        amm_addr = self.deployment.get("contracts", {}).get("SimpleAMM", "")
        if not amm_addr or amm_addr == "not_deployed":
            return None
        
        return self.w3.eth.contract(
            address=Web3.to_checksum_address(amm_addr),
            abi=AMM_ABI
        )
    
    def get_eth_price_usdc(self) -> float:
        """
        Get current ETH price in USDC
        Returns price from AMM or fallback default
        """
        import time
        
        # Check cache
        if self._cached_price and (time.time() - self._cache_time) < self.cache_duration:
            return self._cached_price
        
        try:
            amm = self.get_amm_contract()
            if not amm:
                return self.DEFAULT_ETH_PRICE
            
            # getPrice returns USDC per ETH (scaled by 1e18)
            # USDC has 6 decimals, WETH has 18
            # reserveA = USDC (6 decimals)
            # reserveB = WETH (18 decimals)
            reserve_usdc = amm.functions.reserveA().call()  # 6 decimals
            reserve_weth = amm.functions.reserveB().call()  # 18 decimals
            
            if reserve_weth == 0:
                return self.DEFAULT_ETH_PRICE
            
            # Price = USDC / WETH, adjusted for decimals
            # (reserve_usdc / 1e6) / (reserve_weth / 1e18) = (reserve_usdc * 1e12) / reserve_weth
            price = (reserve_usdc * 10**12) / reserve_weth
            
            self._cached_price = price
            self._cache_time = time.time()
            
            return price
            
        except Exception as e:
            return self.DEFAULT_ETH_PRICE
    
    def eth_to_usdc(self, eth_amount: float) -> float:
        """Convert ETH amount to USDC value"""
        price = self.get_eth_price_usdc()
        return eth_amount * price
    
    def format_eth_with_usdc(self, eth_amount: float) -> str:
        """Format ETH amount with USDC equivalent"""
        usdc_value = self.eth_to_usdc(eth_amount)
        return f"{eth_amount:.4f} ETH (${usdc_value:,.2f})"
    
    def format_usdc(self, usdc_amount: float) -> str:
        """Format USDC amount"""
        return f"${usdc_amount:,.2f}"


# Global instance for easy import
_price_feed = None

def get_price_feed() -> PriceFeed:
    """Get global price feed instance"""
    global _price_feed
    if _price_feed is None:
        _price_feed = PriceFeed()
    return _price_feed


def eth_to_usdc(eth_amount: float) -> float:
    """Quick helper to convert ETH to USDC"""
    return get_price_feed().eth_to_usdc(eth_amount)


def format_eth_with_usdc(eth_amount: float) -> str:
    """Quick helper to format ETH with USDC value"""
    return get_price_feed().format_eth_with_usdc(eth_amount)
