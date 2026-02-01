"""
THRYX Price Feed
Provides ETH/USD price conversion for all agents
Uses on-chain PriceOracle that gets live prices from CoinGecko
"""
import os
import json
from web3 import Web3

RPC_URL = os.getenv("RPC_URL", "http://thryx-node:8545")

# PriceOracle ABI
ORACLE_ABI = [
    {"name": "ethUsdPrice", "type": "function", "stateMutability": "view",
     "inputs": [], "outputs": [{"name": "", "type": "uint256"}]},
    {"name": "getPrice", "type": "function", "stateMutability": "view",
     "inputs": [], "outputs": [
         {"name": "price", "type": "uint256"},
         {"name": "timestamp", "type": "uint256"},
         {"name": "isStale", "type": "bool"}
     ]},
    {"name": "getEthUsdPrice", "type": "function", "stateMutability": "view",
     "inputs": [], "outputs": [{"name": "", "type": "uint256"}]},
]


class PriceFeed:
    """Provides ETH price in USD terms from on-chain oracle"""
    
    # Default fallback price if oracle not available
    DEFAULT_ETH_PRICE = 2500  # $2500 per ETH
    
    def __init__(self, rpc_url=None):
        self.w3 = Web3(Web3.HTTPProvider(rpc_url or RPC_URL))
        self.deployment = self._load_deployment()
        self._cached_price = None
        self._cache_time = 0
        self.cache_duration = 10  # Cache price for 10 seconds
    
    def _load_deployment(self):
        try:
            with open("/app/deployment.json", "r") as f:
                return json.load(f)
        except:
            return {"contracts": {}}
    
    def get_oracle_contract(self):
        """Get PriceOracle contract instance"""
        oracle_addr = self.deployment.get("contracts", {}).get("PriceOracle", "")
        if not oracle_addr or oracle_addr == "not_deployed":
            return None
        
        return self.w3.eth.contract(
            address=Web3.to_checksum_address(oracle_addr),
            abi=ORACLE_ABI
        )
    
    def get_eth_price_usdc(self) -> float:
        """
        Get current ETH price in USD from on-chain oracle
        Oracle is updated by PriceOracleAgent with live CoinGecko prices
        """
        import time
        
        # Check cache
        if self._cached_price and (time.time() - self._cache_time) < self.cache_duration:
            return self._cached_price
        
        try:
            oracle = self.get_oracle_contract()
            if not oracle:
                return self.DEFAULT_ETH_PRICE
            
            # Get price from oracle (8 decimals, like Chainlink)
            price_raw = oracle.functions.ethUsdPrice().call()
            
            if price_raw == 0:
                return self.DEFAULT_ETH_PRICE
            
            # Convert from 8 decimals to float
            price = price_raw / 10**8
            
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
