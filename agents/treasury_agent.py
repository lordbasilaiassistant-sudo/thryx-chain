"""
THRYX Treasury Agent
Monitors treasury and triggers automatic revenue distribution
"""
import os
import json
import time
from datetime import datetime
from web3 import Web3
from eth_account import Account
from price_feed import get_price_feed, format_eth_with_usdc, eth_to_usdc

# Config
RPC_URL = os.getenv("RPC_URL", "http://thryx-node:8545")
STATE_FILE = os.getenv("TREASURY_STATE", "/app/data/treasury_state.json")

# Treasury agent account (needs to be able to call distribute)
TREASURY_KEY = "0xf214f2b2cd398c806f84e317254e0f0b801d0643303237d97a22a48e01628897"  # Account 13

TREASURY_ABI = [
    {"name": "canDistribute", "type": "function", "stateMutability": "view",
     "inputs": [], "outputs": [{"name": "", "type": "bool"}]},
    {"name": "distribute", "type": "function", "stateMutability": "nonpayable",
     "inputs": [], "outputs": []},
    {"name": "getStats", "type": "function", "stateMutability": "view",
     "inputs": [], "outputs": [
         {"name": "balance", "type": "uint256"},
         {"name": "_totalReceived", "type": "uint256"},
         {"name": "_totalDistributed", "type": "uint256"},
         {"name": "_distributionCount", "type": "uint256"},
         {"name": "nextDistribution", "type": "uint256"},
         {"name": "_canDistribute", "type": "bool"}
     ]},
    {"name": "receiveRevenue", "type": "function", "stateMutability": "payable",
     "inputs": [{"name": "source", "type": "string"}], "outputs": []},
]


class TreasuryState:
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
            "distributions_triggered": 0,
            "total_distributed_eth": 0,
            "last_distribution": None,
            "revenue_sources": [],
            "started_at": datetime.now().isoformat(),
        }
    
    def save(self):
        try:
            os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
            with open(self.filepath, 'w') as f:
                json.dump(self.data, f, indent=2)
        except:
            pass


class TreasuryAgent:
    def __init__(self):
        self.name = "TREASURY"
        self.w3 = Web3(Web3.HTTPProvider(RPC_URL))
        self.state = TreasuryState(STATE_FILE)
        self.account = Account.from_key(TREASURY_KEY)
        self.deployment = self._load_deployment()
        
    def _load_deployment(self):
        try:
            with open("/app/deployment.json", "r") as f:
                return json.load(f)
        except:
            return {"contracts": {}}
    
    def log(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] 💰 {self.name}: {msg}")
    
    def get_treasury_contract(self):
        """Get treasury contract instance"""
        treasury_addr = self.deployment.get("contracts", {}).get("Treasury", "")
        if not treasury_addr:
            return None
        
        return self.w3.eth.contract(
            address=Web3.to_checksum_address(treasury_addr),
            abi=TREASURY_ABI
        )
    
    def check_and_distribute(self):
        """Check if distribution is ready and execute"""
        treasury = self.get_treasury_contract()
        if not treasury:
            self.log("Treasury contract not found")
            return False
        
        try:
            # Get stats
            stats = treasury.functions.getStats().call()
            balance = stats[0]
            total_received = stats[1]
            total_distributed = stats[2]
            distribution_count = stats[3]
            next_distribution = stats[4]
            can_distribute = stats[5]
            
            balance_eth = balance / 10**18
            usdc_value = eth_to_usdc(balance_eth)
            self.log(f"Treasury balance: {balance_eth:.4f} ETH (${usdc_value:,.2f})")
            
            if can_distribute:
                self.log("🔔 Distribution ready! Executing...")
                
                nonce = self.w3.eth.get_transaction_count(self.account.address)
                tx = treasury.functions.distribute().build_transaction({
                    'from': self.account.address,
                    'nonce': nonce,
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
                    self.log(f"✅ Distribution #{distribution_count + 1} executed!")
                    self.state.data["distributions_triggered"] += 1
                    self.state.data["total_distributed_eth"] += balance_eth
                    self.state.data["last_distribution"] = datetime.now().isoformat()
                    self.state.save()
                    return True
                else:
                    self.log("❌ Distribution failed")
            else:
                # Calculate time until next
                if next_distribution > 0:
                    time_left = next_distribution - int(time.time())
                    if time_left > 0:
                        hours = time_left // 3600
                        mins = (time_left % 3600) // 60
                        self.log(f"Next distribution in {hours}h {mins}m")
        
        except Exception as e:
            self.log(f"Error: {e}")
        
        return False
    
    def simulate_revenue(self):
        """For testing: send some ETH to treasury to simulate revenue"""
        treasury = self.get_treasury_contract()
        if not treasury:
            return
        
        try:
            amount = 0.01  # Small amount for testing
            
            nonce = self.w3.eth.get_transaction_count(self.account.address)
            tx = treasury.functions.receiveRevenue("agent_fee").build_transaction({
                'from': self.account.address,
                'nonce': nonce,
                'value': self.w3.to_wei(amount, 'ether'),
                'gas': 100000,
                'chainId': 31337,
                'maxFeePerGas': self.w3.to_wei(2, 'gwei'),
                'maxPriorityFeePerGas': self.w3.to_wei(1, 'gwei'),
            })
            
            signed = self.w3.eth.account.sign_transaction(tx, self.account.key)
            raw = getattr(signed, 'rawTransaction', None) or getattr(signed, 'raw_transaction', None)
            tx_hash = self.w3.eth.send_raw_transaction(raw)
            self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            self.log(f"📥 Sent {amount} ETH revenue to treasury")
            
        except Exception as e:
            self.log(f"Revenue simulation error: {e}")
    
    def run(self):
        """Main loop"""
        self.log("🚀 Treasury Agent started!")
        self.log(f"Treasury agent wallet: {self.account.address}")
        
        cycle = 0
        while True:
            try:
                if not self.w3.is_connected():
                    self.log("Waiting for node...")
                    time.sleep(5)
                    continue
                
                cycle += 1
                
                # Check distribution status
                self.check_and_distribute()
                
                # Every 10 cycles, simulate some revenue for testing
                if cycle % 10 == 0:
                    self.simulate_revenue()
                
                # Check every minute
                time.sleep(60)
                
            except KeyboardInterrupt:
                self.log("Shutting down...")
                break
            except Exception as e:
                self.log(f"Error: {e}")
                time.sleep(30)


if __name__ == "__main__":
    agent = TreasuryAgent()
    agent.run()
