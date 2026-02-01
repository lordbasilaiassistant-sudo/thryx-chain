"""
Thryx Oracle Agent
Fetches prices from external APIs and submits to AgentOracle contract
"""
import time
import requests
from web3 import Web3

from base_agent import BaseAgent
from config import CONTRACTS, AGENT_ORACLE_ABI


class OracleAgent(BaseAgent):
    """Autonomous price oracle agent - fetches and submits prices every 10 seconds"""
    
    def __init__(self):
        super().__init__(agent_type="oracle", loop_interval=10.0)
        
        # Price pairs to track
        self.pairs = {
            "ETH/USD": Web3.keccak(text="ETH/USD"),
            "BTC/USD": Web3.keccak(text="BTC/USD"),
        }
        
        # Price sources (free APIs)
        self.sources = [
            self._fetch_coingecko,
            self._fetch_coincap,
        ]
        
        self.oracle_contract = None
    
    def _init_contracts(self):
        """Initialize contract instances"""
        if self.oracle_contract is None:
            self.oracle_contract = self.get_contract("AgentOracle", AGENT_ORACLE_ABI)
    
    def _fetch_coingecko(self) -> dict:
        """Fetch prices from CoinGecko (free, no API key)"""
        try:
            url = "https://api.coingecko.com/api/v3/simple/price"
            params = {
                "ids": "ethereum,bitcoin",
                "vs_currencies": "usd"
            }
            resp = requests.get(url, params=params, timeout=5)
            data = resp.json()
            
            return {
                "ETH/USD": int(data.get("ethereum", {}).get("usd", 0) * 1e8),
                "BTC/USD": int(data.get("bitcoin", {}).get("usd", 0) * 1e8),
            }
        except Exception as e:
            self.logger.warning(f"CoinGecko fetch failed: {e}")
            return {}
    
    def _fetch_coincap(self) -> dict:
        """Fetch prices from CoinCap (free, no API key)"""
        try:
            prices = {}
            
            # ETH
            resp = requests.get("https://api.coincap.io/v2/assets/ethereum", timeout=5)
            data = resp.json()
            eth_price = float(data.get("data", {}).get("priceUsd", 0))
            prices["ETH/USD"] = int(eth_price * 1e8)
            
            # BTC
            resp = requests.get("https://api.coincap.io/v2/assets/bitcoin", timeout=5)
            data = resp.json()
            btc_price = float(data.get("data", {}).get("priceUsd", 0))
            prices["BTC/USD"] = int(btc_price * 1e8)
            
            return prices
        except Exception as e:
            self.logger.warning(f"CoinCap fetch failed: {e}")
            return {}
    
    def _get_simulated_prices(self) -> dict:
        """Generate simulated prices for local testing (adds small variance)"""
        import random
        base_eth = 2500
        base_btc = 80000
        
        # Add small random variance (+/- 1%)
        eth_price = base_eth * (1 + (random.random() - 0.5) * 0.02)
        btc_price = base_btc * (1 + (random.random() - 0.5) * 0.02)
        
        return {
            "ETH/USD": int(eth_price * 1e8),
            "BTC/USD": int(btc_price * 1e8),
        }
    
    def _aggregate_prices(self) -> dict:
        """Aggregate prices from multiple sources"""
        all_prices = {}
        
        for source in self.sources:
            prices = source()
            for pair, price in prices.items():
                if price > 0:
                    if pair not in all_prices:
                        all_prices[pair] = []
                    all_prices[pair].append(price)
        
        # Calculate median for each pair
        result = {}
        for pair, prices in all_prices.items():
            if prices:
                prices.sort()
                mid = len(prices) // 2
                result[pair] = prices[mid]
        
        # Fallback to simulated prices if no external data
        if not result:
            self.logger.info("Using simulated prices (external APIs unavailable)")
            result = self._get_simulated_prices()
        
        return result
    
    def execute(self):
        """Submit prices to oracle contract"""
        self._init_contracts()
        
        prices = self._aggregate_prices()
        
        if not prices:
            self.logger.warning("No prices fetched from any source")
            return
        
        for pair_name, price in prices.items():
            pair_hash = self.pairs.get(pair_name)
            if not pair_hash:
                continue
            
            # Format price for logging
            price_formatted = price / 1e8
            self.logger.info(f"Submitting {pair_name}: ${price_formatted:,.2f}")
            
            # Build and send transaction
            tx = self.build_contract_tx(
                self.oracle_contract,
                "submitPrice",
                pair_hash,
                price
            )
            
            result = self.send_transaction(tx)
            if result:
                self.logger.info(f"Price submitted for {pair_name}")


if __name__ == "__main__":
    agent = OracleAgent()
    agent.run_forever()
