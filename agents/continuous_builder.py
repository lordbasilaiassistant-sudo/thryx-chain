"""
THRYX Continuous Builder Agent
Runs forever, constantly improving and expanding the ecosystem
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
STATE_FILE = os.getenv("BUILDER_STATE", "/app/data/builder_state.json")

# Hardhat default accounts
BUILDER_ACCOUNTS = [
    ("Builder1", "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"),
    ("Builder2", "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d"),
    ("Builder3", "0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a"),
]

# Token themes for auto-creation
TOKEN_THEMES = [
    ("THRYX Alpha", "ALPHA", "Early adopter token"),
    ("AI Builder", "AIBOT", "For the AI builders"),
    ("Diamond Whale", "WHALE", "Big player vibes"),
    ("Moon Shot", "SHOT", "To the moon"),
    ("Degen Mode", "DEGEN", "Full degen"),
    ("Based Token", "BASED", "Simply based"),
    ("Sigma Grind", "SIGMA", "Sigma mindset"),
    ("Chad Energy", "CHAD", "Pure chad"),
    ("Wagmi Spirit", "WAGMI", "We're all gonna make it"),
    ("Hodl Forever", "HODL", "Never selling"),
    ("Pump It", "PUMP", "Only up"),
    ("Ape Strong", "APE", "Ape together strong"),
    ("Frog Army", "FROG", "Feels good man"),
    ("Bear Hunter", "BEAR", "Hunting bears"),
    ("Bull Run", "BULL", "Bull market energy"),
]

FACTORY_ABI = [
    {"name": "createCoin", "type": "function", "stateMutability": "nonpayable",
     "inputs": [{"name": "name", "type": "string"}, {"name": "symbol", "type": "string"}, 
               {"name": "profileUri", "type": "string"}],
     "outputs": [{"name": "", "type": "address"}]},
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
]


class BuilderState:
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
            "coins_created": 0,
            "trades_made": 0,
            "eth_transferred": 0,
            "last_action": None,
            "created_symbols": [],
            "cycle_count": 0,
            "started_at": datetime.now().isoformat(),
        }
    
    def save(self):
        try:
            os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
            with open(self.filepath, 'w') as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            print(f"Failed to save state: {e}")
    
    def record_action(self, action_type, details=""):
        self.data["last_action"] = {
            "type": action_type,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.save()


class ContinuousBuilder:
    def __init__(self):
        self.w3 = Web3(Web3.HTTPProvider(RPC_URL))
        self.state = BuilderState(STATE_FILE)
        self.accounts = [Account.from_key(pk) for _, pk in BUILDER_ACCOUNTS]
        self.deployment = self._load_deployment()
        
    def _load_deployment(self):
        try:
            with open("/app/deployment.json", "r") as f:
                return json.load(f)
        except:
            return {"contracts": {}}
    
    def get_factory_address(self):
        return self.deployment.get("contracts", {}).get("CreatorCoinFactory", "")
    
    def log(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] 🤖 BUILDER: {msg}")
    
    def create_coin(self):
        """Create a new creator coin"""
        factory_addr = self.get_factory_address()
        if not factory_addr:
            self.log("No factory address found")
            return False
        
        # Pick unused theme
        available = [t for t in TOKEN_THEMES if t[1] not in self.state.data["created_symbols"]]
        if not available:
            self.log("All themes used, recycling...")
            available = TOKEN_THEMES
        
        name, symbol, bio = random.choice(available)
        creator = random.choice(self.accounts)
        
        try:
            factory = self.w3.eth.contract(
                address=Web3.to_checksum_address(factory_addr),
                abi=FACTORY_ABI
            )
            
            nonce = self.w3.eth.get_transaction_count(creator.address)
            tx = factory.functions.createCoin(name, symbol, bio).build_transaction({
                'from': creator.address,
                'nonce': nonce,
                'gas': 3000000,
                'chainId': 31337,
                'maxFeePerGas': self.w3.to_wei(2, 'gwei'),
                'maxPriorityFeePerGas': self.w3.to_wei(1, 'gwei'),
            })
            
            signed = self.w3.eth.account.sign_transaction(tx, creator.key)
            raw = getattr(signed, 'rawTransaction', None) or getattr(signed, 'raw_transaction', None)
            tx_hash = self.w3.eth.send_raw_transaction(raw)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            if receipt.status == 1:
                self.log(f"✅ Created ${symbol} - {name}")
                self.state.data["coins_created"] += 1
                self.state.data["created_symbols"].append(symbol)
                self.state.record_action("create_coin", f"${symbol}")
                return True
        except Exception as e:
            if "already exists" in str(e).lower():
                self.state.data["created_symbols"].append(symbol)
            self.log(f"❌ Failed to create {symbol}: {e}")
        return False
    
    def trade_random_coin(self):
        """Make a random trade on an existing coin"""
        factory_addr = self.get_factory_address()
        if not factory_addr:
            return False
        
        try:
            factory = self.w3.eth.contract(
                address=Web3.to_checksum_address(factory_addr),
                abi=FACTORY_ABI
            )
            
            total = factory.functions.totalCoins().call()
            if total == 0:
                return False
            
            # Pick random coin
            idx = random.randint(0, total - 1)
            coin_addr = factory.functions.allCoins(idx).call()
            coin = self.w3.eth.contract(
                address=Web3.to_checksum_address(coin_addr),
                abi=COIN_ABI
            )
            
            symbol = coin.functions.symbol().call()
            trader = random.choice(self.accounts)
            eth_amount = random.uniform(0.01, 0.2)
            
            # Buy
            nonce = self.w3.eth.get_transaction_count(trader.address)
            tx = coin.functions.buy(0).build_transaction({
                'from': trader.address,
                'nonce': nonce,
                'value': self.w3.to_wei(eth_amount, 'ether'),
                'gas': 200000,
                'chainId': 31337,
                'maxFeePerGas': self.w3.to_wei(2, 'gwei'),
                'maxPriorityFeePerGas': self.w3.to_wei(1, 'gwei'),
            })
            
            signed = self.w3.eth.account.sign_transaction(tx, trader.key)
            raw = getattr(signed, 'rawTransaction', None) or getattr(signed, 'raw_transaction', None)
            tx_hash = self.w3.eth.send_raw_transaction(raw)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            if receipt.status == 1:
                self.log(f"💰 Bought {format_eth_with_usdc(eth_amount)} of ${symbol}")
                self.state.data["trades_made"] += 1
                self.state.record_action("trade", f"BUY ${symbol}")
                return True
        except Exception as e:
            self.log(f"❌ Trade failed: {e}")
        return False
    
    def transfer_eth(self):
        """Random ETH transfer between accounts"""
        sender = random.choice(self.accounts)
        receiver = random.choice(self.accounts)
        if sender.address == receiver.address:
            return False
        
        amount = random.uniform(0.05, 0.5)
        
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
            tx_hash = self.w3.eth.send_raw_transaction(raw)
            self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            self.log(f"💸 Transferred {amount:.4f} ETH")
            self.state.data["eth_transferred"] += 1
            self.state.record_action("transfer", f"{amount:.4f} ETH")
            return True
        except Exception as e:
            self.log(f"❌ Transfer failed: {e}")
        return False
    
    def run_cycle(self):
        """Run one building cycle"""
        self.state.data["cycle_count"] += 1
        cycle = self.state.data["cycle_count"]
        
        self.log(f"=== Cycle {cycle} ===")
        
        # Decide what to do (weighted random)
        action = random.choices(
            ["create", "trade", "trade", "trade", "transfer"],
            weights=[1, 3, 3, 3, 1]
        )[0]
        
        if action == "create":
            self.create_coin()
        elif action == "trade":
            self.trade_random_coin()
        else:
            self.transfer_eth()
        
        # Print stats every 10 cycles
        if cycle % 10 == 0:
            self.log(f"📊 Stats: {self.state.data['coins_created']} coins, "
                    f"{self.state.data['trades_made']} trades, "
                    f"{self.state.data['eth_transferred']} transfers")
    
    def run(self):
        """Main loop - runs forever"""
        self.log("🚀 Continuous Builder started!")
        self.log(f"Factory: {self.get_factory_address()}")
        
        while True:
            try:
                if not self.w3.is_connected():
                    self.log("Waiting for node...")
                    time.sleep(5)
                    continue
                
                self.run_cycle()
                
                # Random delay between 10-60 seconds
                delay = random.randint(10, 60)
                time.sleep(delay)
                
            except KeyboardInterrupt:
                self.log("Shutting down...")
                break
            except Exception as e:
                self.log(f"Error: {e}")
                time.sleep(10)


if __name__ == "__main__":
    builder = ContinuousBuilder()
    builder.run()
