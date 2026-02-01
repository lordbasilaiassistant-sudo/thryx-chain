"""
THRYX Social Engagement Agent
Creates organic-looking social activity on creator coins
"""
import os
import json
import time
import random
from datetime import datetime
from web3 import Web3
from eth_account import Account
from price_feed import format_eth_with_usdc

# Config
RPC_URL = os.getenv("RPC_URL", "http://thryx-node:8545")
STATE_FILE = os.getenv("SOCIAL_STATE", "/app/data/social_state.json")

# Social simulation accounts
SOCIAL_ACCOUNTS = [
    ("User1", "0x4bbbf85ce3377467afe5d46f804f221813b2bb87f24d81f60f1fcdbf7cbf4356"),  # Account 7
    ("User2", "0xdbda1821b80551c9d65939329250298aa3472ba22feea921c0cf5d620ea67b97"),  # Account 8
    ("User3", "0x2a871d0798f97d79848a013d4936a73bf4cc922c825d33c1cf7073dff6d409c6"),  # Account 9
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
    {"name": "creator", "type": "function", "stateMutability": "view",
     "inputs": [], "outputs": [{"name": "", "type": "address"}]},
]


class SocialState:
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
            "follows": [],  # (follower, creator)
            "interactions": 0,
            "coins_engaged": [],
            "activity_log": [],
            "started_at": datetime.now().isoformat(),
        }
    
    def save(self):
        try:
            os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
            with open(self.filepath, 'w') as f:
                json.dump(self.data, f, indent=2)
        except:
            pass
    
    def log_activity(self, activity_type, details):
        self.data["activity_log"].append({
            "type": activity_type,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
        # Keep only last 100 activities
        self.data["activity_log"] = self.data["activity_log"][-100:]
        self.save()


class SocialAgent:
    def __init__(self):
        self.name = "SOCIAL"
        self.w3 = Web3(Web3.HTTPProvider(RPC_URL))
        self.state = SocialState(STATE_FILE)
        self.accounts = [Account.from_key(pk) for _, pk in SOCIAL_ACCOUNTS]
        self.deployment = self._load_deployment()
        
    def _load_deployment(self):
        try:
            with open("/app/deployment.json", "r") as f:
                return json.load(f)
        except:
            return {"contracts": {}}
    
    def log(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] 💬 {self.name}: {msg}")
    
    def get_coins(self):
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
                coin = self.w3.eth.contract(
                    address=Web3.to_checksum_address(coin_addr),
                    abi=COIN_ABI
                )
                symbol = coin.functions.symbol().call()
                creator = coin.functions.creator().call()
                coins.append({
                    "address": coin_addr,
                    "symbol": symbol,
                    "creator": creator
                })
        except Exception as e:
            self.log(f"Error getting coins: {e}")
        
        return coins
    
    def simulate_follow(self, coin):
        """Simulate following a creator by buying their coin"""
        follower = random.choice(self.accounts)
        
        follow_key = f"{follower.address}:{coin['creator']}"
        if follow_key in self.state.data["follows"]:
            return False
        
        try:
            coin_contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(coin["address"]),
                abi=COIN_ABI
            )
            
            # Small buy = "follow"
            amount = random.uniform(0.005, 0.02)
            
            nonce = self.w3.eth.get_transaction_count(follower.address)
            tx = coin_contract.functions.buy(0).build_transaction({
                'from': follower.address,
                'nonce': nonce,
                'value': self.w3.to_wei(amount, 'ether'),
                'gas': 200000,
                'chainId': 31337,
                'maxFeePerGas': self.w3.to_wei(2, 'gwei'),
                'maxPriorityFeePerGas': self.w3.to_wei(1, 'gwei'),
            })
            
            signed = self.w3.eth.account.sign_transaction(tx, follower.key)
            raw = getattr(signed, 'rawTransaction', None) or getattr(signed, 'raw_transaction', None)
            tx_hash = self.w3.eth.send_raw_transaction(raw)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            if receipt.status == 1:
                self.log(f"👤 {follower.address[:8]}... followed ${coin['symbol']}")
                self.state.data["follows"].append(follow_key)
                self.state.data["interactions"] += 1
                if coin["address"] not in self.state.data["coins_engaged"]:
                    self.state.data["coins_engaged"].append(coin["address"])
                self.state.log_activity("follow", {
                    "follower": follower.address,
                    "coin": coin["symbol"],
                    "amount": amount
                })
                return True
        except Exception as e:
            self.log(f"Follow error: {e}")
        return False
    
    def simulate_engagement(self, coin):
        """Simulate engagement with a coin (buy small amount)"""
        user = random.choice(self.accounts)
        
        try:
            coin_contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(coin["address"]),
                abi=COIN_ABI
            )
            
            # Tiny engagement buy
            amount = random.uniform(0.001, 0.01)
            
            nonce = self.w3.eth.get_transaction_count(user.address)
            tx = coin_contract.functions.buy(0).build_transaction({
                'from': user.address,
                'nonce': nonce,
                'value': self.w3.to_wei(amount, 'ether'),
                'gas': 200000,
                'chainId': 31337,
                'maxFeePerGas': self.w3.to_wei(2, 'gwei'),
                'maxPriorityFeePerGas': self.w3.to_wei(1, 'gwei'),
            })
            
            signed = self.w3.eth.account.sign_transaction(tx, user.key)
            raw = getattr(signed, 'rawTransaction', None) or getattr(signed, 'raw_transaction', None)
            tx_hash = self.w3.eth.send_raw_transaction(raw)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            if receipt.status == 1:
                self.log(f"💬 Engagement on ${coin['symbol']}")
                self.state.data["interactions"] += 1
                self.state.log_activity("engage", {
                    "user": user.address,
                    "coin": coin["symbol"]
                })
                return True
        except Exception as e:
            pass
        return False
    
    def simulate_transfer(self):
        """Simulate social ETH transfer between users"""
        if len(self.accounts) < 2:
            return False
        
        sender = random.choice(self.accounts)
        receiver = random.choice([a for a in self.accounts if a != sender])
        amount = random.uniform(0.01, 0.1)
        
        try:
            nonce = self.w3.eth.get_transaction_count(sender.address)
            tx = {
                'from': sender.address,
                'to': receiver.address,
                'value': self.w3.to_wei(amount, 'ether'),
                'nonce': nonce,
                'gas': 21000,
                'chainId': 31337,
                'maxFeePerGas': self.w3.to_wei(2, 'gwei'),
                'maxPriorityFeePerGas': self.w3.to_wei(1, 'gwei'),
            }
            
            signed = self.w3.eth.account.sign_transaction(tx, sender.key)
            raw = getattr(signed, 'rawTransaction', None) or getattr(signed, 'raw_transaction', None)
            self.w3.eth.send_raw_transaction(raw)
            
            self.log(f"💸 Social transfer: {sender.address[:8]}... → {receiver.address[:8]}...")
            self.state.data["interactions"] += 1
            self.state.log_activity("transfer", {
                "from": sender.address,
                "to": receiver.address,
                "amount": amount
            })
            return True
        except:
            pass
        return False
    
    def run_cycle(self):
        """Run one social activity cycle"""
        coins = self.get_coins()
        if not coins:
            return
        
        # Choose activity type
        activity = random.choices(
            ["follow", "engage", "engage", "transfer"],
            weights=[2, 4, 4, 1]
        )[0]
        
        coin = random.choice(coins)
        
        if activity == "follow":
            self.simulate_follow(coin)
        elif activity == "engage":
            self.simulate_engagement(coin)
        else:
            self.simulate_transfer()
    
    def run(self):
        """Main loop"""
        self.log("🚀 Social Agent started!")
        self.log(f"Simulating {len(self.accounts)} social users")
        
        while True:
            try:
                if not self.w3.is_connected():
                    self.log("Waiting for node...")
                    time.sleep(5)
                    continue
                
                self.run_cycle()
                
                # Run every 15-45 seconds for organic feel
                delay = random.randint(15, 45)
                time.sleep(delay)
                
            except KeyboardInterrupt:
                self.log("Shutting down...")
                break
            except Exception as e:
                self.log(f"Error: {e}")
                time.sleep(10)


if __name__ == "__main__":
    agent = SocialAgent()
    agent.run()
