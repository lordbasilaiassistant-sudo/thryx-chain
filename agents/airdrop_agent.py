"""
THRYX Airdrop Agent
Distributes tokens to active addresses to incentivize participation
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
STATE_FILE = os.getenv("AIRDROP_STATE", "/app/data/airdrop_state.json")

# Airdrop account (uses a dedicated account)
AIRDROP_KEY = "0x92db14e403b83dfe3df233f83dfa3a0d7096f21ca9b0d6d6b8d88b2b4ec1564e"  # Account 6

FACTORY_ABI = [
    {"name": "totalCoins", "type": "function", "stateMutability": "view",
     "inputs": [], "outputs": [{"name": "", "type": "uint256"}]},
    {"name": "allCoins", "type": "function", "stateMutability": "view",
     "inputs": [{"name": "index", "type": "uint256"}],
     "outputs": [{"name": "", "type": "address"}]},
]

COIN_ABI = [
    {"name": "symbol", "type": "function", "stateMutability": "view",
     "inputs": [], "outputs": [{"name": "", "type": "string"}]},
    {"name": "transfer", "type": "function", "stateMutability": "nonpayable",
     "inputs": [{"name": "to", "type": "address"}, {"name": "amount", "type": "uint256"}],
     "outputs": [{"name": "", "type": "bool"}]},
    {"name": "balanceOf", "type": "function", "stateMutability": "view",
     "inputs": [{"name": "account", "type": "address"}],
     "outputs": [{"name": "", "type": "uint256"}]},
    {"name": "buy", "type": "function", "stateMutability": "payable",
     "inputs": [{"name": "minTokensOut", "type": "uint256"}],
     "outputs": [{"name": "", "type": "uint256"}]},
]


class AirdropState:
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
            "airdrops_sent": 0,
            "total_tokens_distributed": 0,
            "recipients": [],
            "active_addresses": [],
            "last_scan_block": 0,
            "started_at": datetime.now().isoformat(),
        }
    
    def save(self):
        try:
            os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
            with open(self.filepath, 'w') as f:
                json.dump(self.data, f, indent=2)
        except:
            pass


class AirdropAgent:
    def __init__(self):
        self.name = "AIRDROP"
        self.w3 = Web3(Web3.HTTPProvider(RPC_URL))
        self.state = AirdropState(STATE_FILE)
        self.account = Account.from_key(AIRDROP_KEY)
        self.deployment = self._load_deployment()
        self.coin_balances = {}  # Cache of our token balances
        
    def _load_deployment(self):
        try:
            with open("/app/deployment.json", "r") as f:
                return json.load(f)
        except:
            return {"contracts": {}}
    
    def log(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] 🎁 {self.name}: {msg}")
    
    def scan_active_addresses(self):
        """Scan recent blocks for active addresses"""
        try:
            current_block = self.w3.eth.block_number
            start_block = max(self.state.data["last_scan_block"], current_block - 100)
            
            addresses = set(self.state.data["active_addresses"])
            
            for block_num in range(start_block, current_block + 1):
                try:
                    block = self.w3.eth.get_block(block_num, full_transactions=True)
                    for tx in block.transactions:
                        if tx.get('from'):
                            addresses.add(tx['from'])
                        if tx.get('to'):
                            addresses.add(tx['to'])
                except:
                    continue
            
            # Filter out contract addresses and our own
            filtered = []
            for addr in addresses:
                if addr and addr != self.account.address:
                    code = self.w3.eth.get_code(Web3.to_checksum_address(addr))
                    if len(code) <= 2:  # EOA
                        filtered.append(addr)
            
            self.state.data["active_addresses"] = filtered[:100]  # Keep top 100
            self.state.data["last_scan_block"] = current_block
            self.state.save()
            
            self.log(f"Found {len(filtered)} active addresses")
            return filtered
        except Exception as e:
            self.log(f"Scan error: {e}")
            return []
    
    def get_coins_with_balance(self):
        """Get coins where we have a balance"""
        factory_addr = self.deployment.get("contracts", {}).get("CreatorCoinFactory", "")
        if not factory_addr:
            return []
        
        coins_with_balance = []
        
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
                balance = coin.functions.balanceOf(self.account.address).call()
                if balance > 0:
                    symbol = coin.functions.symbol().call()
                    coins_with_balance.append({
                        "address": coin_addr,
                        "symbol": symbol,
                        "balance": balance
                    })
                    self.coin_balances[coin_addr] = balance
        except Exception as e:
            self.log(f"Error getting coins: {e}")
        
        return coins_with_balance
    
    def acquire_tokens(self, coin_addr):
        """Buy some tokens to airdrop"""
        try:
            coin = self.w3.eth.contract(
                address=Web3.to_checksum_address(coin_addr),
                abi=COIN_ABI
            )
            
            amount = 0.02  # Buy 0.02 ETH worth
            
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
            self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            symbol = coin.functions.symbol().call()
            self.log(f"Acquired ${symbol} tokens for airdrops")
            return True
        except Exception as e:
            self.log(f"Error acquiring tokens: {e}")
            return False
    
    def send_airdrop(self, coin_addr, recipient, amount):
        """Send tokens to a recipient"""
        try:
            coin = self.w3.eth.contract(
                address=Web3.to_checksum_address(coin_addr),
                abi=COIN_ABI
            )
            
            nonce = self.w3.eth.get_transaction_count(self.account.address)
            tx = coin.functions.transfer(
                Web3.to_checksum_address(recipient),
                amount
            ).build_transaction({
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
                symbol = coin.functions.symbol().call()
                self.log(f"🎁 Airdropped ${symbol} to {recipient[:10]}...")
                self.state.data["airdrops_sent"] += 1
                if recipient not in self.state.data["recipients"]:
                    self.state.data["recipients"].append(recipient)
                self.state.save()
                return True
        except Exception as e:
            self.log(f"Airdrop error: {e}")
        return False
    
    def run_cycle(self):
        """Run one airdrop cycle"""
        # Get coins we have
        coins = self.get_coins_with_balance()
        
        # If no coins, try to acquire some
        if not coins:
            factory_addr = self.deployment.get("contracts", {}).get("CreatorCoinFactory", "")
            if factory_addr:
                try:
                    factory = self.w3.eth.contract(
                        address=Web3.to_checksum_address(factory_addr),
                        abi=FACTORY_ABI
                    )
                    total = factory.functions.totalCoins().call()
                    if total > 0:
                        coin_addr = factory.functions.allCoins(random.randint(0, total-1)).call()
                        self.acquire_tokens(coin_addr)
                except:
                    pass
            return
        
        # Get active addresses
        addresses = self.state.data["active_addresses"]
        if not addresses or random.random() < 0.1:  # 10% chance to rescan
            addresses = self.scan_active_addresses()
        
        if not addresses:
            return
        
        # Pick a coin and recipient
        coin = random.choice(coins)
        recipient = random.choice(addresses)
        
        # Skip if already received
        if recipient in self.state.data["recipients"]:
            return
        
        # Airdrop 1-5% of our balance
        airdrop_amount = int(coin["balance"] * random.uniform(0.01, 0.05))
        if airdrop_amount > 0:
            self.send_airdrop(coin["address"], recipient, airdrop_amount)
    
    def run(self):
        """Main loop"""
        self.log("🚀 Airdrop Agent started!")
        self.log(f"Airdrop wallet: {self.account.address}")
        
        while True:
            try:
                if not self.w3.is_connected():
                    self.log("Waiting for node...")
                    time.sleep(5)
                    continue
                
                self.run_cycle()
                
                # Run every 60-180 seconds
                delay = random.randint(60, 180)
                time.sleep(delay)
                
            except KeyboardInterrupt:
                self.log("Shutting down...")
                break
            except Exception as e:
                self.log(f"Error: {e}")
                time.sleep(10)


if __name__ == "__main__":
    agent = AirdropAgent()
    agent.run()
