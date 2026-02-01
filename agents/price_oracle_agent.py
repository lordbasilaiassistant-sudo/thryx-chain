"""
THRYX Price Oracle Agent
Fetches live ETH/USD prices from CoinGecko and updates on-chain oracle
"""
import os
import json
import time
import requests
from datetime import datetime
from web3 import Web3
from eth_account import Account

# Config
RPC_URL = os.getenv("RPC_URL", "http://thryx-node:8545")
STATE_FILE = os.getenv("PRICE_ORACLE_STATE", "/app/data/price_oracle_state.json")
UPDATE_INTERVAL = int(os.getenv("PRICE_UPDATE_INTERVAL", "120"))  # 2 minutes

# Oracle account (Hardhat account 13 - 0xcd3B766CCDd6AE721141F452C550Ca635964ce71)
ORACLE_KEY = "0xea6c44ac03bff858b476bba40716402b03e41b8e97e276d1baec7c37d42484a0"

# CoinGecko API (free, no key needed)
COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price"

ORACLE_ABI = [
    {"name": "updatePrice", "type": "function", "stateMutability": "nonpayable",
     "inputs": [{"name": "newPrice", "type": "uint256"}], "outputs": []},
    {"name": "ethUsdPrice", "type": "function", "stateMutability": "view",
     "inputs": [], "outputs": [{"name": "", "type": "uint256"}]},
    {"name": "lastUpdate", "type": "function", "stateMutability": "view",
     "inputs": [], "outputs": [{"name": "", "type": "uint256"}]},
    {"name": "getPrice", "type": "function", "stateMutability": "view",
     "inputs": [], "outputs": [
         {"name": "price", "type": "uint256"},
         {"name": "timestamp", "type": "uint256"},
         {"name": "isStale", "type": "bool"}
     ]},
]


class PriceOracleState:
    def __init__(self, filepath):
        self.filepath = filepath
        self.data = self._load()
    
    def _load(self):
        try:
            if os.path.exists(self.filepath):
                with open(self.filepath, 'r') as f:
                    return json.load(f)
        except:
            pass
        return {
            "updates": 0,
            "last_price": 0,
            "price_history": [],
            "errors": 0,
            "started_at": datetime.now().isoformat(),
        }
    
    def save(self):
        try:
            os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
            with open(self.filepath, 'w') as f:
                json.dump(self.data, f, indent=2)
        except:
            pass


class PriceOracleAgent:
    def __init__(self):
        self.name = "PRICE_ORACLE"
        self.w3 = Web3(Web3.HTTPProvider(RPC_URL))
        self.state = PriceOracleState(STATE_FILE)
        self.account = Account.from_key(ORACLE_KEY)
        self.deployment = self._load_deployment()
        self.last_fetched_price = None
        
    def _load_deployment(self):
        try:
            with open("/app/deployment.json", "r") as f:
                return json.load(f)
        except:
            return {"contracts": {}}
    
    def log(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] 📊 {self.name}: {msg}")
    
    def get_oracle_contract(self):
        """Get PriceOracle contract instance"""
        oracle_addr = self.deployment.get("contracts", {}).get("PriceOracle", "")
        if not oracle_addr or oracle_addr == "not_deployed":
            return None
        
        return self.w3.eth.contract(
            address=Web3.to_checksum_address(oracle_addr),
            abi=ORACLE_ABI
        )
    
    def fetch_live_price(self):
        """Fetch live ETH/USD price from CoinGecko"""
        try:
            response = requests.get(
                COINGECKO_URL,
                params={
                    "ids": "ethereum",
                    "vs_currencies": "usd"
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                price = data.get("ethereum", {}).get("usd", 0)
                if price > 0:
                    self.last_fetched_price = price
                    return price
            
            self.log(f"CoinGecko returned status {response.status_code}")
            
        except requests.exceptions.Timeout:
            self.log("CoinGecko request timed out")
        except requests.exceptions.RequestException as e:
            self.log(f"CoinGecko request failed: {e}")
        except Exception as e:
            self.log(f"Error fetching price: {e}")
        
        return None
    
    def get_current_onchain_price(self):
        """Get current price from on-chain oracle"""
        oracle = self.get_oracle_contract()
        if not oracle:
            return None
        
        try:
            price_raw = oracle.functions.ethUsdPrice().call()
            return price_raw / 10**8  # Convert from 8 decimals
        except:
            return None
    
    def update_onchain_price(self, price_usd):
        """Update the on-chain oracle with new price"""
        oracle = self.get_oracle_contract()
        if not oracle:
            self.log("PriceOracle contract not found")
            return False
        
        try:
            # Convert to 8 decimals (like Chainlink)
            price_scaled = int(price_usd * 10**8)
            
            nonce = self.w3.eth.get_transaction_count(self.account.address)
            tx = oracle.functions.updatePrice(price_scaled).build_transaction({
                'from': self.account.address,
                'nonce': nonce,
                'gas': 100000,
                'chainId': 31337,
                'maxFeePerGas': self.w3.to_wei(2, 'gwei'),
                'maxPriorityFeePerGas': self.w3.to_wei(1, 'gwei'),
            })
            
            signed = self.w3.eth.account.sign_transaction(tx, self.account.key)
            raw = getattr(signed, 'rawTransaction', None) or getattr(signed, 'raw_transaction', None)
            tx_hash = self.w3.eth.send_raw_transaction(raw)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            if receipt.status == 1:
                self.log(f"✅ Updated on-chain price to ${price_usd:,.2f}")
                self.state.data["updates"] += 1
                self.state.data["last_price"] = price_usd
                self.state.data["price_history"].append({
                    "price": price_usd,
                    "timestamp": datetime.now().isoformat()
                })
                # Keep only last 100 prices
                self.state.data["price_history"] = self.state.data["price_history"][-100:]
                self.state.save()
                return True
            else:
                self.log("❌ Transaction failed")
                
        except Exception as e:
            error_msg = str(e)
            if "Update too frequent" in error_msg:
                self.log("Skipping update - too frequent")
            elif "Price change too large" in error_msg:
                self.log(f"Skipping update - price change too large")
            elif "Not authorized" in error_msg:
                self.log("Not authorized - need to authorize oracle first")
            else:
                self.log(f"Error updating price: {e}")
                self.state.data["errors"] += 1
                self.state.save()
        
        return False
    
    def run_cycle(self):
        """Fetch live price and update on-chain"""
        # Fetch from CoinGecko
        live_price = self.fetch_live_price()
        
        if live_price:
            current_onchain = self.get_current_onchain_price()
            
            if current_onchain:
                change_pct = abs(live_price - current_onchain) / current_onchain * 100
                self.log(f"Live: ${live_price:,.2f} | On-chain: ${current_onchain:,.2f} | Δ {change_pct:.2f}%")
                
                # Only update if price changed by more than 0.5%
                if change_pct >= 0.5:
                    self.update_onchain_price(live_price)
                else:
                    self.log("Price stable, no update needed")
            else:
                # First update or contract not ready
                self.log(f"Fetched live price: ${live_price:,.2f}")
                self.update_onchain_price(live_price)
        else:
            self.log("Failed to fetch live price")
    
    def run(self):
        """Main loop"""
        self.log("🚀 Price Oracle Agent started!")
        self.log(f"Oracle wallet: {self.account.address}")
        self.log(f"Update interval: {UPDATE_INTERVAL}s")
        
        while True:
            try:
                if not self.w3.is_connected():
                    self.log("Waiting for node...")
                    time.sleep(5)
                    continue
                
                self.run_cycle()
                time.sleep(UPDATE_INTERVAL)
                
            except KeyboardInterrupt:
                self.log("Shutting down...")
                break
            except Exception as e:
                self.log(f"Error: {e}")
                time.sleep(30)


if __name__ == "__main__":
    agent = PriceOracleAgent()
    agent.run()
