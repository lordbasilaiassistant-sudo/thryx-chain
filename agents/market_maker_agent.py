"""
THRYX Market Maker Agent
Maintains healthy markets across all creator coins by providing liquidity
"""
import os
import json
import time
import random
from datetime import datetime
from web3 import Web3
from eth_account import Account

# Config
RPC_URL = os.getenv("RPC_URL", "http://thryx-node:8545")
STATE_FILE = os.getenv("MM_STATE", "/app/data/market_maker_state.json")

# Market maker accounts (use high-index Hardhat accounts)
MM_ACCOUNTS = [
    ("MM1", "0x47e179ec197488593b187f80a00eb0da91f1b9d0b13f8733639f19c30a34926a"),  # Account 4
    ("MM2", "0x8b3a350cf5c34c9194ca85829a2df0ec3153be0318b5e2d3348e872092edffba"),  # Account 5
]

FACTORY_ABI = [
    {"name": "totalCoins", "type": "function", "stateMutability": "view",
     "inputs": [], "outputs": [{"name": "", "type": "uint256"}]},
    {"name": "allCoins", "type": "function", "stateMutability": "view",
     "inputs": [{"name": "index", "type": "uint256"}],
     "outputs": [{"name": "", "type": "address"}]},
]

COIN_ABI = [
    {"name": "buy", "type": "function", "stateMutability": "payable",
     "inputs": [{"name": "minTokensOut", "type": "uint256"}],
     "outputs": [{"name": "", "type": "uint256"}]},
    {"name": "sell", "type": "function", "stateMutability": "nonpayable",
     "inputs": [{"name": "tokenAmount", "type": "uint256"}, {"name": "minEthOut", "type": "uint256"}],
     "outputs": [{"name": "", "type": "uint256"}]},
    {"name": "symbol", "type": "function", "stateMutability": "view",
     "inputs": [], "outputs": [{"name": "", "type": "string"}]},
    {"name": "balanceOf", "type": "function", "stateMutability": "view",
     "inputs": [{"name": "account", "type": "address"}],
     "outputs": [{"name": "", "type": "uint256"}]},
    {"name": "totalTrades", "type": "function", "stateMutability": "view",
     "inputs": [], "outputs": [{"name": "", "type": "uint256"}]},
    {"name": "totalEthLocked", "type": "function", "stateMutability": "view",
     "inputs": [], "outputs": [{"name": "", "type": "uint256"}]},
    {"name": "getCurrentPrice", "type": "function", "stateMutability": "view",
     "inputs": [], "outputs": [{"name": "", "type": "uint256"}]},
]


class MarketMakerState:
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
            "buys": 0,
            "sells": 0,
            "volume_eth": 0,
            "coins_supported": [],
            "last_activity": {},
            "started_at": datetime.now().isoformat(),
        }
    
    def save(self):
        try:
            os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
            with open(self.filepath, 'w') as f:
                json.dump(self.data, f, indent=2)
        except:
            pass


class MarketMakerAgent:
    def __init__(self):
        self.name = "MARKET_MAKER"
        self.w3 = Web3(Web3.HTTPProvider(RPC_URL))
        self.state = MarketMakerState(STATE_FILE)
        self.accounts = [Account.from_key(pk) for _, pk in MM_ACCOUNTS]
        self.deployment = self._load_deployment()
        
    def _load_deployment(self):
        try:
            with open("/app/deployment.json", "r") as f:
                return json.load(f)
        except:
            return {"contracts": {}}
    
    def log(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] 📈 {self.name}: {msg}")
    
    def get_all_coins(self):
        """Get all creator coins from factory"""
        factory_addr = self.deployment.get("contracts", {}).get("CreatorCoinFactory", "")
        if not factory_addr:
            return []
        
        try:
            factory = self.w3.eth.contract(
                address=Web3.to_checksum_address(factory_addr),
                abi=FACTORY_ABI
            )
            total = factory.functions.totalCoins().call()
            coins = []
            for i in range(total):
                addr = factory.functions.allCoins(i).call()
                coins.append(addr)
            return coins
        except Exception as e:
            self.log(f"Error getting coins: {e}")
            return []
    
    def get_coin_stats(self, coin_addr):
        """Get stats for a coin"""
        try:
            coin = self.w3.eth.contract(
                address=Web3.to_checksum_address(coin_addr),
                abi=COIN_ABI
            )
            return {
                "symbol": coin.functions.symbol().call(),
                "trades": coin.functions.totalTrades().call(),
                "tvl": coin.functions.totalEthLocked().call(),
                "price": coin.functions.getCurrentPrice().call(),
            }
        except:
            return None
    
    def needs_liquidity(self, coin_addr):
        """Check if a coin needs market making"""
        stats = self.get_coin_stats(coin_addr)
        if not stats:
            return False
        
        # Check last activity
        last = self.state.data["last_activity"].get(coin_addr, 0)
        if time.time() - last < 300:  # 5 min cooldown
            return False
        
        # Low TVL or low trade count = needs support
        tvl_eth = stats["tvl"] / 10**18
        return tvl_eth < 0.5 or stats["trades"] < 10
    
    def provide_liquidity(self, coin_addr):
        """Buy a small amount to provide liquidity"""
        try:
            coin = self.w3.eth.contract(
                address=Web3.to_checksum_address(coin_addr),
                abi=COIN_ABI
            )
            symbol = coin.functions.symbol().call()
            
            # Pick random MM account
            mm = random.choice(self.accounts)
            amount = random.uniform(0.01, 0.05)  # 0.01-0.05 ETH
            
            nonce = self.w3.eth.get_transaction_count(mm.address)
            tx = coin.functions.buy(0).build_transaction({
                'from': mm.address,
                'nonce': nonce,
                'value': self.w3.to_wei(amount, 'ether'),
                'gas': 200000,
                'chainId': 31337,
                'maxFeePerGas': self.w3.to_wei(2, 'gwei'),
                'maxPriorityFeePerGas': self.w3.to_wei(1, 'gwei'),
            })
            
            signed = self.w3.eth.account.sign_transaction(tx, mm.key)
            raw = getattr(signed, 'rawTransaction', None) or getattr(signed, 'raw_transaction', None)
            tx_hash = self.w3.eth.send_raw_transaction(raw)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            if receipt.status == 1:
                self.log(f"📈 Provided {amount:.4f} ETH liquidity to ${symbol}")
                self.state.data["buys"] += 1
                self.state.data["volume_eth"] += amount
                self.state.data["last_activity"][coin_addr] = time.time()
                if coin_addr not in self.state.data["coins_supported"]:
                    self.state.data["coins_supported"].append(coin_addr)
                self.state.save()
                return True
        except Exception as e:
            self.log(f"Error providing liquidity: {e}")
        return False
    
    def run_cycle(self):
        """Run one market making cycle"""
        coins = self.get_all_coins()
        if not coins:
            self.log("No coins found")
            return
        
        # Check each coin
        for coin_addr in coins:
            if self.needs_liquidity(coin_addr):
                self.provide_liquidity(coin_addr)
                time.sleep(2)  # Small delay between operations
    
    def run(self):
        """Main loop"""
        self.log("🚀 Market Maker Agent started!")
        self.log(f"Managing {len(self.accounts)} MM accounts")
        
        while True:
            try:
                if not self.w3.is_connected():
                    self.log("Waiting for node...")
                    time.sleep(5)
                    continue
                
                self.run_cycle()
                
                # Run every 30-90 seconds
                delay = random.randint(30, 90)
                time.sleep(delay)
                
            except KeyboardInterrupt:
                self.log("Shutting down...")
                break
            except Exception as e:
                self.log(f"Error: {e}")
                time.sleep(10)


if __name__ == "__main__":
    agent = MarketMakerAgent()
    agent.run()
