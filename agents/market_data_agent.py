"""
THRYX Market Data Agent
Collects and stores price/volume data for all coins (for charts on MySocial)
"""
import os
import json
import time
from datetime import datetime
from web3 import Web3
from eth_account import Account
from price_feed import get_price_feed, eth_to_usdc

# Config
RPC_URL = os.getenv("RPC_URL", "http://thryx-node:8545")
STATE_FILE = os.getenv("MARKET_DATA_STATE", "/app/data/market_data_state.json")
UPDATE_INTERVAL = int(os.getenv("MARKET_UPDATE_INTERVAL", "60"))  # 1 minute

# Market data agent account
MARKET_DATA_KEY = "0xc526ee95bf44d8fc405a158bb884d9d1238d99f0612e9f33d006bb0789009aaa"  # Account 16

FACTORY_ABI = [
    {"name": "totalCoins", "type": "function", "stateMutability": "view",
     "inputs": [], "outputs": [{"name": "", "type": "uint256"}]},
    {"name": "allCoins", "type": "function", "stateMutability": "view",
     "inputs": [{"name": "index", "type": "uint256"}],
     "outputs": [{"name": "", "type": "address"}]},
]

COIN_ABI = [
    {"name": "getCurrentPrice", "type": "function", "stateMutability": "view",
     "inputs": [], "outputs": [{"name": "", "type": "uint256"}]},
    {"name": "totalEthLocked", "type": "function", "stateMutability": "view",
     "inputs": [], "outputs": [{"name": "", "type": "uint256"}]},
    {"name": "totalSupply", "type": "function", "stateMutability": "view",
     "inputs": [], "outputs": [{"name": "", "type": "uint256"}]},
    {"name": "totalTrades", "type": "function", "stateMutability": "view",
     "inputs": [], "outputs": [{"name": "", "type": "uint256"}]},
    {"name": "symbol", "type": "function", "stateMutability": "view",
     "inputs": [], "outputs": [{"name": "", "type": "string"}]},
    {"name": "name", "type": "function", "stateMutability": "view",
     "inputs": [], "outputs": [{"name": "", "type": "string"}]},
    {"name": "creator", "type": "function", "stateMutability": "view",
     "inputs": [], "outputs": [{"name": "", "type": "address"}]},
]

MARKET_DATA_ABI = [
    {"name": "recordPrice", "type": "function", "stateMutability": "nonpayable",
     "inputs": [
         {"name": "coin", "type": "address"},
         {"name": "price", "type": "uint256"},
         {"name": "volume", "type": "uint256"}
     ], "outputs": []},
    {"name": "updateStats", "type": "function", "stateMutability": "nonpayable",
     "inputs": [
         {"name": "coin", "type": "address"},
         {"name": "currentPrice", "type": "uint256"},
         {"name": "high24h", "type": "uint256"},
         {"name": "low24h", "type": "uint256"},
         {"name": "volume24h", "type": "uint256"},
         {"name": "marketCap", "type": "uint256"},
         {"name": "totalTrades", "type": "uint256"},
         {"name": "holders", "type": "uint256"},
         {"name": "priceChange24h", "type": "int256"}
     ], "outputs": []},
]


class MarketDataState:
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
            "snapshots": 0,
            "coins_tracked": [],
            "price_data": {},  # coin -> list of {price, timestamp}
            "started_at": datetime.now().isoformat(),
        }
    
    def save(self):
        try:
            os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
            with open(self.filepath, 'w') as f:
                json.dump(self.data, f, indent=2)
        except:
            pass
    
    def add_price(self, coin_addr, price, volume):
        if coin_addr not in self.data["price_data"]:
            self.data["price_data"][coin_addr] = []
            self.data["coins_tracked"].append(coin_addr)
        
        self.data["price_data"][coin_addr].append({
            "price": price,
            "volume": volume,
            "timestamp": time.time()
        })
        
        # Keep last 1440 points (24 hours at 1 min intervals)
        self.data["price_data"][coin_addr] = self.data["price_data"][coin_addr][-1440:]
    
    def get_24h_stats(self, coin_addr):
        history = self.data["price_data"].get(coin_addr, [])
        if not history:
            return None
        
        now = time.time()
        day_ago = now - 86400
        
        # Filter to last 24h
        recent = [h for h in history if h["timestamp"] > day_ago]
        if not recent:
            recent = history[-10:]  # Fallback to last 10 if no 24h data
        
        prices = [h["price"] for h in recent]
        volumes = [h.get("volume", 0) for h in recent]
        
        return {
            "high": max(prices),
            "low": min(prices),
            "volume": sum(volumes),
            "price_start": recent[0]["price"] if recent else 0,
            "price_end": recent[-1]["price"] if recent else 0,
        }


class MarketDataAgent:
    def __init__(self):
        self.name = "MARKET_DATA"
        self.w3 = Web3(Web3.HTTPProvider(RPC_URL))
        self.state = MarketDataState(STATE_FILE)
        self.account = Account.from_key(MARKET_DATA_KEY)
        self.deployment = self._load_deployment()
        self.price_feed = get_price_feed()
        
    def _load_deployment(self):
        try:
            with open("/app/deployment.json", "r") as f:
                return json.load(f)
        except:
            return {"contracts": {}}
    
    def log(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] 📊 {self.name}: {msg}")
    
    def get_all_coins(self):
        """Get all creator coins"""
        factory_addr = self.deployment.get("contracts", {}).get("CreatorCoinFactory", "")
        if not factory_addr:
            return []
        
        coins = []
        try:
            factory = self.w3.eth.contract(
                address=Web3.to_checksum_address(factory_addr),
                abi=FACTORY_ABI
            )
            total = factory.functions.totalCoins().call()
            
            for i in range(total):
                coin_addr = factory.functions.allCoins(i).call()
                coins.append(coin_addr)
        except Exception as e:
            self.log(f"Error getting coins: {e}")
        
        return coins
    
    def collect_coin_data(self, coin_addr):
        """Collect all metrics for a coin"""
        try:
            coin = self.w3.eth.contract(
                address=Web3.to_checksum_address(coin_addr),
                abi=COIN_ABI
            )
            
            price = coin.functions.getCurrentPrice().call()
            tvl = coin.functions.totalEthLocked().call()
            supply = coin.functions.totalSupply().call()
            trades = coin.functions.totalTrades().call()
            symbol = coin.functions.symbol().call()
            name = coin.functions.name().call()
            creator = coin.functions.creator().call()
            
            # Calculate market cap (price * supply)
            market_cap = (price * supply) // 10**18 if supply > 0 else 0
            
            # Get last known trades for volume estimation
            last_trades = self.state.data.get("last_trades", {}).get(coin_addr, 0)
            volume = (trades - last_trades) if trades > last_trades else 0
            
            # Store last trades
            if "last_trades" not in self.state.data:
                self.state.data["last_trades"] = {}
            self.state.data["last_trades"][coin_addr] = trades
            
            return {
                "address": coin_addr,
                "symbol": symbol,
                "name": name,
                "creator": creator,
                "price": price,
                "tvl": tvl,
                "supply": supply,
                "trades": trades,
                "market_cap": market_cap,
                "volume": volume,
            }
        except Exception as e:
            return None
    
    def record_snapshot(self, coin_data):
        """Store price snapshot"""
        coin_addr = coin_data["address"]
        price = coin_data["price"]
        volume = coin_data["volume"]
        
        # Add to local state
        self.state.add_price(coin_addr, price, volume)
        
        # Get 24h stats
        stats = self.state.get_24h_stats(coin_addr)
        if stats:
            change_pct = 0
            if stats["price_start"] > 0:
                change_pct = int((stats["price_end"] - stats["price_start"]) * 10000 / stats["price_start"])
            
            # Log summary
            eth_price = self.price_feed.get_eth_price_usdc()
            price_usd = (price / 10**18) * eth_price
            
            self.log(f"${coin_data['symbol']}: ${price_usd:.6f} | 24h: {change_pct/100:+.2f}%")
    
    def run_cycle(self):
        """Collect data for all coins"""
        coins = self.get_all_coins()
        if not coins:
            self.log("No coins found")
            return
        
        for coin_addr in coins:
            data = self.collect_coin_data(coin_addr)
            if data:
                self.record_snapshot(data)
        
        self.state.data["snapshots"] += 1
        self.state.save()
        
        self.log(f"📸 Snapshot #{self.state.data['snapshots']} - {len(coins)} coins tracked")
    
    def run(self):
        """Main loop"""
        self.log("🚀 Market Data Agent started!")
        self.log(f"Update interval: {UPDATE_INTERVAL}s")
        self.log("Collecting price data for MySocial charts")
        
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
                time.sleep(10)


if __name__ == "__main__":
    agent = MarketDataAgent()
    agent.run()
