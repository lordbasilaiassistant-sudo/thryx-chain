"""
THRYX Stabilizer Agent
Protects ecosystem value by buying dips and maintaining price floors
Core mission: Value only goes UP on THRYX
"""
import os
import json
import time
import random
from datetime import datetime
from web3 import Web3
from eth_account import Account
from price_feed import get_price_feed, format_eth_with_usdc

# Config
RPC_URL = os.getenv("RPC_URL", "http://thryx-node:8545")
STATE_FILE = os.getenv("STABILIZER_STATE", "/app/data/stabilizer_state.json")

# Stabilizer account (dedicated for value protection)
STABILIZER_KEY = "0x47c99abed3324a2707c28affff1267e45918ec8c3f20b8aa892e8b065d2942dd"  # Account 15

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
    {"name": "getCurrentPrice", "type": "function", "stateMutability": "view",
     "inputs": [], "outputs": [{"name": "", "type": "uint256"}]},
    {"name": "totalEthLocked", "type": "function", "stateMutability": "view",
     "inputs": [], "outputs": [{"name": "", "type": "uint256"}]},
    {"name": "symbol", "type": "function", "stateMutability": "view",
     "inputs": [], "outputs": [{"name": "", "type": "string"}]},
    {"name": "totalTrades", "type": "function", "stateMutability": "view",
     "inputs": [], "outputs": [{"name": "", "type": "uint256"}]},
]


class StabilizerState:
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
            "interventions": 0,
            "eth_deployed": 0,
            "coins_protected": [],
            "price_floors": {},
            "price_history": {},
            "started_at": datetime.now().isoformat(),
        }
    
    def save(self):
        try:
            os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
            with open(self.filepath, 'w') as f:
                json.dump(self.data, f, indent=2)
        except:
            pass


class StabilizerAgent:
    def __init__(self):
        self.name = "STABILIZER"
        self.w3 = Web3(Web3.HTTPProvider(RPC_URL))
        self.state = StabilizerState(STATE_FILE)
        self.account = Account.from_key(STABILIZER_KEY)
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
        print(f"[{timestamp}] 🛡️ {self.name}: {msg}")
    
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
        except:
            pass
        
        return coins
    
    def get_coin_data(self, coin_addr):
        """Get current coin metrics"""
        try:
            coin = self.w3.eth.contract(
                address=Web3.to_checksum_address(coin_addr),
                abi=COIN_ABI
            )
            return {
                "address": coin_addr,
                "symbol": coin.functions.symbol().call(),
                "price": coin.functions.getCurrentPrice().call(),
                "tvl": coin.functions.totalEthLocked().call(),
                "trades": coin.functions.totalTrades().call(),
            }
        except:
            return None
    
    def track_price(self, coin_addr, price):
        """Track price history for floor calculation"""
        if coin_addr not in self.state.data["price_history"]:
            self.state.data["price_history"][coin_addr] = []
        
        history = self.state.data["price_history"][coin_addr]
        history.append({
            "price": price,
            "timestamp": time.time()
        })
        
        # Keep last 100 price points
        self.state.data["price_history"][coin_addr] = history[-100:]
        
        # Calculate floor as 80% of average price
        if len(history) >= 5:
            avg = sum(h["price"] for h in history) / len(history)
            floor = int(avg * 0.8)
            self.state.data["price_floors"][coin_addr] = floor
    
    def needs_protection(self, coin_data):
        """Check if coin needs value protection"""
        coin_addr = coin_data["address"]
        current_price = coin_data["price"]
        
        # Get price floor
        floor = self.state.data["price_floors"].get(coin_addr, 0)
        
        if floor == 0:
            # No floor yet, track and skip
            return False, "No floor established"
        
        if current_price < floor:
            return True, f"Price ${current_price} below floor ${floor}"
        
        # Check for rapid drops (compare to recent history)
        history = self.state.data["price_history"].get(coin_addr, [])
        if len(history) >= 3:
            recent_avg = sum(h["price"] for h in history[-3:]) / 3
            if current_price < recent_avg * 0.9:  # 10% drop
                return True, "Rapid price drop detected"
        
        return False, "Price healthy"
    
    def protect_coin(self, coin_data, reason):
        """Buy to protect coin value"""
        try:
            coin = self.w3.eth.contract(
                address=Web3.to_checksum_address(coin_data["address"]),
                abi=COIN_ABI
            )
            
            # Calculate buy amount (0.02-0.1 ETH based on TVL)
            tvl_eth = coin_data["tvl"] / 10**18
            if tvl_eth < 0.1:
                amount = 0.05
            elif tvl_eth < 0.5:
                amount = 0.03
            else:
                amount = 0.02
            
            # Check balance
            balance = self.w3.eth.get_balance(self.account.address)
            if balance < self.w3.to_wei(amount, 'ether'):
                self.log(f"⚠️ Low balance, can't protect ${coin_data['symbol']}")
                return False
            
            nonce = self.w3.eth.get_transaction_count(self.account.address)
            tx = coin.functions.buy(0).build_transaction({
                'from': self.account.address,
                'nonce': nonce,
                'value': self.w3.to_wei(amount, 'ether'),
                'gas': 200000,
                'chainId': 31337,
                'maxFeePerGas': self.w3.to_wei(2, 'gwei'),
                'maxPriorityFeePerGas': self.w3.to_wei(1, 'gwei'),
            })
            
            signed = self.w3.eth.account.sign_transaction(tx, self.account.key)
            raw = getattr(signed, 'rawTransaction', None) or getattr(signed, 'raw_transaction', None)
            tx_hash = self.w3.eth.send_raw_transaction(raw)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            if receipt.status == 1:
                self.log(f"🛡️ Protected ${coin_data['symbol']} with {format_eth_with_usdc(amount)}")
                self.log(f"   Reason: {reason}")
                
                self.state.data["interventions"] += 1
                self.state.data["eth_deployed"] += amount
                if coin_data["address"] not in self.state.data["coins_protected"]:
                    self.state.data["coins_protected"].append(coin_data["address"])
                self.state.save()
                return True
                
        except Exception as e:
            self.log(f"Protection failed: {e}")
        
        return False
    
    def run_cycle(self):
        """Monitor all coins and protect as needed"""
        coins = self.get_all_coins()
        if not coins:
            return
        
        protected = 0
        for coin_addr in coins:
            coin_data = self.get_coin_data(coin_addr)
            if not coin_data:
                continue
            
            # Track price
            self.track_price(coin_addr, coin_data["price"])
            
            # Check if needs protection
            needs, reason = self.needs_protection(coin_data)
            
            if needs:
                if self.protect_coin(coin_data, reason):
                    protected += 1
                    time.sleep(2)  # Cooldown between protections
        
        if protected > 0:
            self.log(f"Protected {protected} coins this cycle")
        
        self.state.save()
    
    def run(self):
        """Main loop"""
        self.log("🚀 Stabilizer Agent started!")
        self.log(f"Protector wallet: {self.account.address}")
        self.log("Mission: Ensure value ONLY goes UP")
        
        balance = self.w3.eth.get_balance(self.account.address)
        self.log(f"Protection fund: {format_eth_with_usdc(balance / 10**18)}")
        
        while True:
            try:
                if not self.w3.is_connected():
                    self.log("Waiting for node...")
                    time.sleep(5)
                    continue
                
                self.run_cycle()
                
                # Run every 30-60 seconds
                time.sleep(random.randint(30, 60))
                
            except KeyboardInterrupt:
                self.log("Shutting down...")
                break
            except Exception as e:
                self.log(f"Error: {e}")
                time.sleep(10)


if __name__ == "__main__":
    agent = StabilizerAgent()
    agent.run()
