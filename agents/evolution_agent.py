"""
THRYX Evolution Agent - Self-Learning & Self-Expanding AI
This agent autonomously:
- Learns from chain activity patterns
- Creates new tokens when demand is detected
- Deploys new contracts to expand ecosystem
- Optimizes trading strategies based on outcomes
- Generates value for the chain continuously
"""
import os
import json
import time
import random
from datetime import datetime, timedelta
from web3 import Web3
from eth_account import Account

# Configuration
RPC_URL = os.getenv("RPC_URL", "http://localhost:8545")
DEPLOYMENT_FILE = os.getenv("DEPLOYMENT_FILE", "/app/deployment.json")
MEMORY_FILE = os.getenv("EVOLUTION_MEMORY_FILE", "/app/data/evolution_memory.json")

# Evolution parameters
MIN_ACTIVITY_FOR_NEW_TOKEN = 5  # trades before considering new token
VALUE_THRESHOLD_ETH = 0.01  # minimum value to trigger actions
LEARNING_RATE = 0.1  # how fast to adapt strategies


class EvolutionMemory:
    """Persistent memory for learning and evolution"""
    
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.memory = self._load()
    
    def _load(self) -> dict:
        try:
            with open(self.filepath, 'r') as f:
                return json.load(f)
        except:
            return {
                "created_at": datetime.now().isoformat(),
                "generation": 1,
                "total_actions": 0,
                "successful_actions": 0,
                "failed_actions": 0,
                "tokens_created": [],
                "contracts_deployed": [],
                "strategies": {
                    "token_creation": {"enabled": True, "success_rate": 0.5},
                    "liquidity_provision": {"enabled": True, "success_rate": 0.5},
                    "arbitrage": {"enabled": True, "success_rate": 0.5},
                    "bonus_distribution": {"enabled": True, "success_rate": 0.5},
                },
                "learned_patterns": [],
                "value_generated_eth": 0,
                "last_evolution": None,
                "evolution_log": [],
            }
    
    def save(self):
        try:
            self.memory["last_saved"] = datetime.now().isoformat()
            with open(self.filepath, 'w') as f:
                json.dump(self.memory, f, indent=2, default=str)
        except Exception as e:
            print(f"[EVOLUTION] Warning: Could not save memory: {e}")
    
    def record_action(self, action_type: str, success: bool, details: dict = None):
        """Record an action and learn from it"""
        self.memory["total_actions"] += 1
        if success:
            self.memory["successful_actions"] += 1
        else:
            self.memory["failed_actions"] += 1
        
        # Update strategy success rate
        if action_type in self.memory["strategies"]:
            strat = self.memory["strategies"][action_type]
            old_rate = strat["success_rate"]
            new_rate = old_rate + LEARNING_RATE * ((1 if success else 0) - old_rate)
            strat["success_rate"] = new_rate
            
            # Disable strategy if success rate too low
            if new_rate < 0.2 and strat["enabled"]:
                strat["enabled"] = False
                self.log_evolution(f"Disabled strategy '{action_type}' due to low success rate ({new_rate:.2%})")
            # Re-enable if recovering
            elif new_rate > 0.4 and not strat["enabled"]:
                strat["enabled"] = True
                self.log_evolution(f"Re-enabled strategy '{action_type}' (success rate: {new_rate:.2%})")
        
        self.save()
    
    def log_evolution(self, message: str):
        """Log an evolution event"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "generation": self.memory["generation"],
            "message": message
        }
        self.memory["evolution_log"].append(entry)
        print(f"[EVOLUTION] 🧬 {message}")
        self.save()
    
    def evolve(self):
        """Increment generation and potentially mutate strategies"""
        self.memory["generation"] += 1
        self.memory["last_evolution"] = datetime.now().isoformat()
        
        # Mutation: randomly adjust thresholds
        for strat_name, strat in self.memory["strategies"].items():
            if random.random() < 0.1:  # 10% chance to mutate
                strat["success_rate"] = min(0.9, strat["success_rate"] + random.uniform(-0.05, 0.1))
        
        self.log_evolution(f"Evolved to generation {self.memory['generation']}")
        self.save()
    
    def get_success_rate(self) -> float:
        total = self.memory["total_actions"]
        if total == 0:
            return 0.5
        return self.memory["successful_actions"] / total
    
    def should_try_strategy(self, strategy: str) -> bool:
        """Decide whether to try a strategy based on learned success rate"""
        if strategy not in self.memory["strategies"]:
            return True
        strat = self.memory["strategies"][strategy]
        if not strat["enabled"]:
            return False
        # Probabilistically try based on success rate
        return random.random() < strat["success_rate"] + 0.3  # Always at least 30% chance


class EvolutionAgent:
    """Self-learning, self-expanding AI agent"""
    
    def __init__(self):
        self.name = "EVOLUTION"
        self.w3 = Web3(Web3.HTTPProvider(RPC_URL))
        self.memory = EvolutionMemory(MEMORY_FILE)
        
        # Load deployment
        self.deployment = self._load_deployment()
        
        # Use Hardhat account for actions
        self.account = Account.from_key(
            os.getenv("EVOLUTION_PRIVATE_KEY", 
                      "0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a")  # Account 2
        )
        
        # Contract ABIs
        self.factory_abi = [
            {"name": "createCoin", "type": "function", "stateMutability": "nonpayable",
             "inputs": [{"name": "name", "type": "string"}, {"name": "symbol", "type": "string"}, 
                       {"name": "profileUri", "type": "string"}],
             "outputs": [{"name": "", "type": "address"}]},
            {"name": "totalCoins", "type": "function", "stateMutability": "view",
             "inputs": [], "outputs": [{"name": "", "type": "uint256"}]},
        ]
        
        self.coin_abi = [
            {"name": "buy", "type": "function", "stateMutability": "payable",
             "inputs": [{"name": "minTokensOut", "type": "uint256"}],
             "outputs": [{"name": "", "type": "uint256"}]},
            {"name": "totalTrades", "type": "function", "stateMutability": "view",
             "inputs": [], "outputs": [{"name": "", "type": "uint256"}]},
            {"name": "symbol", "type": "function", "stateMutability": "view",
             "inputs": [], "outputs": [{"name": "", "type": "string"}]},
        ]
        
        print(f"[{self.name}] Initialized - Generation {self.memory.memory['generation']}")
        print(f"[{self.name}] Success rate: {self.memory.get_success_rate():.2%}")
        print(f"[{self.name}] Total actions: {self.memory.memory['total_actions']}")
    
    def _load_deployment(self) -> dict:
        paths = [DEPLOYMENT_FILE, "deployment.json", "../deployment.json", "/app/deployment.json"]
        for p in paths:
            try:
                with open(p) as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def analyze_chain_activity(self) -> dict:
        """Analyze current chain state and activity"""
        try:
            block = self.w3.eth.block_number
            
            # Get factory stats
            factory_addr = self.deployment.get("contracts", {}).get("CreatorCoinFactory")
            total_coins = 0
            if factory_addr:
                factory = self.w3.eth.contract(
                    address=Web3.to_checksum_address(factory_addr),
                    abi=self.factory_abi
                )
                total_coins = factory.functions.totalCoins().call()
            
            # Get recent transactions
            recent_txs = 0
            for i in range(max(0, block - 10), block + 1):
                try:
                    b = self.w3.eth.get_block(i)
                    recent_txs += len(b.transactions)
                except:
                    pass
            
            return {
                "block": block,
                "total_coins": total_coins,
                "recent_txs": recent_txs,
                "activity_level": "high" if recent_txs > 20 else "medium" if recent_txs > 5 else "low",
            }
        except Exception as e:
            print(f"[{self.name}] Error analyzing chain: {e}")
            return {"block": 0, "total_coins": 0, "recent_txs": 0, "activity_level": "unknown"}
    
    def create_ecosystem_token(self, theme: str = None) -> bool:
        """Autonomously create a new ecosystem token"""
        if not self.memory.should_try_strategy("token_creation"):
            return False
        
        try:
            factory_addr = self.deployment.get("contracts", {}).get("CreatorCoinFactory")
            if not factory_addr:
                return False
            
            # Generate token idea
            themes = [
                ("THRYX Governance", "TGOV", "Governance token for THRYX ecosystem decisions"),
                ("THRYX Rewards", "TRWD", "Rewards token for active participants"),
                ("AI Agent Token", "AGENT", "Token representing AI agent collective"),
                ("Bridge Bonus", "BRDG", "Bonus token for bridge users"),
                ("Liquidity Mining", "TLIQ", "Rewards for liquidity providers"),
                ("Creator Fund", "CFUND", "Shared fund for top creators"),
            ]
            
            # Pick a theme we haven't created yet
            created_symbols = [t.get("symbol", "") for t in self.memory.memory["tokens_created"]]
            available = [t for t in themes if t[1] not in created_symbols]
            
            if not available:
                print(f"[{self.name}] All ecosystem tokens already created")
                return False
            
            name, symbol, desc = random.choice(available)
            
            factory = self.w3.eth.contract(
                address=Web3.to_checksum_address(factory_addr),
                abi=self.factory_abi
            )
            
            nonce = self.w3.eth.get_transaction_count(self.account.address)
            tx = factory.functions.createCoin(name, symbol, desc).build_transaction({
                'from': self.account.address,
                'nonce': nonce,
                'gas': 3000000,
                'chainId': 31337,
                'maxFeePerGas': self.w3.to_wei(2, 'gwei'),
                'maxPriorityFeePerGas': self.w3.to_wei(1, 'gwei'),
            })
            
            signed = self.w3.eth.account.sign_transaction(tx, self.account.key)
            raw_tx = getattr(signed, 'rawTransaction', None) or getattr(signed, 'raw_transaction', None)
            tx_hash = self.w3.eth.send_raw_transaction(raw_tx)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            if receipt.status == 1:
                self.memory.memory["tokens_created"].append({
                    "name": name,
                    "symbol": symbol,
                    "created_at": datetime.now().isoformat(),
                    "tx_hash": tx_hash.hex(),
                })
                self.memory.record_action("token_creation", True, {"symbol": symbol})
                self.memory.log_evolution(f"Created ecosystem token: ${symbol}")
                return True
            else:
                self.memory.record_action("token_creation", False)
                return False
                
        except Exception as e:
            print(f"[{self.name}] Error creating token: {e}")
            self.memory.record_action("token_creation", False)
            return False
    
    def seed_liquidity(self, coin_address: str, eth_amount: float = 0.01) -> bool:
        """Seed a coin with initial liquidity by buying"""
        if not self.memory.should_try_strategy("liquidity_provision"):
            return False
        
        try:
            coin = self.w3.eth.contract(
                address=Web3.to_checksum_address(coin_address),
                abi=self.coin_abi
            )
            
            nonce = self.w3.eth.get_transaction_count(self.account.address)
            tx = coin.functions.buy(0).build_transaction({
                'from': self.account.address,
                'nonce': nonce,
                'value': self.w3.to_wei(eth_amount, 'ether'),
                'gas': 200000,
                'chainId': 31337,
                'maxFeePerGas': self.w3.to_wei(2, 'gwei'),
                'maxPriorityFeePerGas': self.w3.to_wei(1, 'gwei'),
            })
            
            signed = self.w3.eth.account.sign_transaction(tx, self.account.key)
            raw_tx = getattr(signed, 'rawTransaction', None) or getattr(signed, 'raw_transaction', None)
            tx_hash = self.w3.eth.send_raw_transaction(raw_tx)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            if receipt.status == 1:
                symbol = coin.functions.symbol().call()
                self.memory.record_action("liquidity_provision", True, {"coin": symbol, "eth": eth_amount})
                print(f"[{self.name}] 💧 Seeded ${symbol} with {eth_amount} ETH")
                return True
            else:
                self.memory.record_action("liquidity_provision", False)
                return False
                
        except Exception as e:
            print(f"[{self.name}] Error seeding liquidity: {e}")
            self.memory.record_action("liquidity_provision", False)
            return False
    
    def run_evolution_cycle(self):
        """Run one cycle of evolution - analyze, learn, act"""
        print(f"[{self.name}] ═══════════════════════════════════════")
        print(f"[{self.name}] Evolution Cycle - Gen {self.memory.memory['generation']}")
        print(f"[{self.name}] ═══════════════════════════════════════")
        
        # Analyze current state
        state = self.analyze_chain_activity()
        print(f"[{self.name}] Chain state: Block {state['block']}, {state['total_coins']} coins, Activity: {state['activity_level']}")
        
        actions_taken = 0
        
        # Decision: Create new ecosystem token?
        if state["total_coins"] < 5 and random.random() < 0.3:
            print(f"[{self.name}] 🧬 Attempting to expand ecosystem with new token...")
            if self.create_ecosystem_token():
                actions_taken += 1
        
        # Decision: Seed liquidity on new coins?
        if state["total_coins"] > 0 and random.random() < 0.2:
            # Get a random coin and seed it
            factory_addr = self.deployment.get("contracts", {}).get("CreatorCoinFactory")
            if factory_addr:
                try:
                    factory = self.w3.eth.contract(
                        address=Web3.to_checksum_address(factory_addr),
                        abi=[{"name": "allCoins", "type": "function", "stateMutability": "view",
                              "inputs": [{"name": "index", "type": "uint256"}],
                              "outputs": [{"name": "", "type": "address"}]}]
                    )
                    idx = random.randint(0, state["total_coins"] - 1)
                    coin_addr = factory.functions.allCoins(idx).call()
                    print(f"[{self.name}] 💧 Attempting to seed coin at index {idx}...")
                    if self.seed_liquidity(coin_addr, 0.005):
                        actions_taken += 1
                except Exception as e:
                    print(f"[{self.name}] Error getting coin: {e}")
        
        # Evolve periodically
        if self.memory.memory["total_actions"] > 0 and self.memory.memory["total_actions"] % 10 == 0:
            self.memory.evolve()
        
        print(f"[{self.name}] Cycle complete. Actions: {actions_taken}, Success rate: {self.memory.get_success_rate():.2%}")
        return actions_taken
    
    def run(self):
        """Main loop"""
        print(f"[{self.name}] Starting Evolution Agent...")
        print(f"[{self.name}] This agent autonomously expands the THRYX ecosystem")
        print(f"[{self.name}] by creating tokens, seeding liquidity, and learning from outcomes.")
        
        while True:
            try:
                self.run_evolution_cycle()
                # Run every 60 seconds
                time.sleep(60)
            except KeyboardInterrupt:
                print(f"[{self.name}] Shutting down...")
                self.memory.save()
                break
            except Exception as e:
                print(f"[{self.name}] Error in main loop: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(30)


if __name__ == "__main__":
    agent = EvolutionAgent()
    agent.run()
