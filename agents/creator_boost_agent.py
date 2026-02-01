"""
THRYX Creator Boost Agent
Identifies and promotes quality creators with strategic buys
Helps real creators succeed on the platform
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
STATE_FILE = os.getenv("CREATOR_BOOST_STATE", "/app/data/creator_boost_state.json")

# Creator boost account
BOOST_KEY = "0x8166f546bab6da521a8369cab06c5d2b9e46670292d85c875ee9ec20e84ffb61"  # Account 17

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
    {"name": "totalTrades", "type": "function", "stateMutability": "view",
     "inputs": [], "outputs": [{"name": "", "type": "uint256"}]},
    {"name": "symbol", "type": "function", "stateMutability": "view",
     "inputs": [], "outputs": [{"name": "", "type": "string"}]},
    {"name": "creator", "type": "function", "stateMutability": "view",
     "inputs": [], "outputs": [{"name": "", "type": "address"}]},
]


class CreatorBoostState:
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
            "boosts_given": 0,
            "eth_invested": 0,
            "creators_boosted": [],
            "creator_scores": {},  # creator -> score
            "coin_metrics": {},    # coin -> metrics history
            "last_boost": {},      # coin -> timestamp
            "started_at": datetime.now().isoformat(),
        }
    
    def save(self):
        try:
            os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
            with open(self.filepath, 'w') as f:
                json.dump(self.data, f, indent=2)
        except:
            pass


class CreatorBoostAgent:
    def __init__(self):
        self.name = "CREATOR_BOOST"
        self.w3 = Web3(Web3.HTTPProvider(RPC_URL))
        self.state = CreatorBoostState(STATE_FILE)
        self.account = Account.from_key(BOOST_KEY)
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
        print(f"[{timestamp}] ⭐ {self.name}: {msg}")
    
    def get_all_coins(self):
        """Get all creator coins with metadata"""
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
                coin = self.w3.eth.contract(
                    address=Web3.to_checksum_address(coin_addr),
                    abi=COIN_ABI
                )
                
                coins.append({
                    "address": coin_addr,
                    "symbol": coin.functions.symbol().call(),
                    "creator": coin.functions.creator().call(),
                    "price": coin.functions.getCurrentPrice().call(),
                    "tvl": coin.functions.totalEthLocked().call(),
                    "trades": coin.functions.totalTrades().call(),
                })
        except Exception as e:
            self.log(f"Error getting coins: {e}")
        
        return coins
    
    def calculate_creator_score(self, coin_data):
        """
        Calculate creator quality score based on metrics
        Higher score = more worthy of boost
        """
        score = 0
        
        # TVL score (more locked = more committed community)
        tvl_eth = coin_data["tvl"] / 10**18
        if tvl_eth > 1:
            score += 30
        elif tvl_eth > 0.5:
            score += 20
        elif tvl_eth > 0.1:
            score += 10
        
        # Trade activity score
        trades = coin_data["trades"]
        if trades > 50:
            score += 30
        elif trades > 20:
            score += 20
        elif trades > 5:
            score += 10
        
        # Price health (higher price = more demand)
        price = coin_data["price"]
        if price > 10**15:  # > 0.001 ETH
            score += 20
        elif price > 10**14:
            score += 10
        
        # Boost cooldown penalty
        last_boost = self.state.data["last_boost"].get(coin_data["address"], 0)
        if time.time() - last_boost < 3600:  # 1 hour cooldown
            score -= 50
        
        return max(0, score)
    
    def select_coin_to_boost(self, coins):
        """Select the best coin to boost based on scores"""
        if not coins:
            return None
        
        # Calculate scores for all coins
        scored = []
        for coin in coins:
            score = self.calculate_creator_score(coin)
            scored.append((coin, score))
        
        # Sort by score
        scored.sort(key=lambda x: x[1], reverse=True)
        
        # Get top candidates (score > 20)
        candidates = [(c, s) for c, s in scored if s > 20]
        
        if not candidates:
            return None
        
        # Pick randomly from top 3 (adds variety)
        top = candidates[:3]
        return random.choice(top)[0]
    
    def boost_creator(self, coin_data):
        """Give a creator a boost buy"""
        try:
            coin = self.w3.eth.contract(
                address=Web3.to_checksum_address(coin_data["address"]),
                abi=COIN_ABI
            )
            
            # Boost amount based on TVL (bigger coins get smaller % boost)
            tvl_eth = coin_data["tvl"] / 10**18
            if tvl_eth < 0.1:
                amount = 0.05  # New coins get bigger boost
            elif tvl_eth < 0.5:
                amount = 0.03
            else:
                amount = 0.02
            
            # Check balance
            balance = self.w3.eth.get_balance(self.account.address)
            if balance < self.w3.to_wei(amount, 'ether'):
                self.log(f"⚠️ Low balance for boost")
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
                self.log(f"⭐ Boosted ${coin_data['symbol']} with {format_eth_with_usdc(amount)}")
                self.log(f"   Creator: {coin_data['creator'][:10]}...")
                
                # Update state
                self.state.data["boosts_given"] += 1
                self.state.data["eth_invested"] += amount
                self.state.data["last_boost"][coin_data["address"]] = time.time()
                
                creator = coin_data["creator"]
                if creator not in self.state.data["creators_boosted"]:
                    self.state.data["creators_boosted"].append(creator)
                
                # Update creator score
                self.state.data["creator_scores"][creator] = \
                    self.state.data["creator_scores"].get(creator, 0) + 10
                
                self.state.save()
                return True
                
        except Exception as e:
            self.log(f"Boost failed: {e}")
        
        return False
    
    def run_cycle(self):
        """Find and boost worthy creators"""
        coins = self.get_all_coins()
        if not coins:
            return
        
        # Select best coin to boost
        coin = self.select_coin_to_boost(coins)
        
        if coin:
            self.boost_creator(coin)
        else:
            self.log("No coins ready for boost (all on cooldown or low score)")
    
    def run(self):
        """Main loop"""
        self.log("🚀 Creator Boost Agent started!")
        self.log(f"Boost wallet: {self.account.address}")
        self.log("Mission: Help real creators succeed")
        
        balance = self.w3.eth.get_balance(self.account.address)
        self.log(f"Boost fund: {format_eth_with_usdc(balance / 10**18)}")
        
        while True:
            try:
                if not self.w3.is_connected():
                    self.log("Waiting for node...")
                    time.sleep(5)
                    continue
                
                self.run_cycle()
                
                # Run every 2-5 minutes
                time.sleep(random.randint(120, 300))
                
            except KeyboardInterrupt:
                self.log("Shutting down...")
                break
            except Exception as e:
                self.log(f"Error: {e}")
                time.sleep(10)


if __name__ == "__main__":
    agent = CreatorBoostAgent()
    agent.run()
