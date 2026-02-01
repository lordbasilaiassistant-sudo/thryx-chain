"""
THRYX Intent Processor Agent
Processes intents from the IntentMempool contract.

Features:
- Monitors pending intents
- Matches intents with solvers
- Executes fulfillment transactions
- Tracks intent outcomes for learning
"""
import os
import time
import json
from datetime import datetime
from web3 import Web3
from typing import Dict, List, Optional

from base_agent import BaseAgent
from config import CONTRACTS
from agent_memory import AgentMemory, ActionRecord


# IntentMempool ABI (relevant functions)
INTENT_MEMPOOL_ABI = [
    {
        "inputs": [],
        "name": "getActiveIntents",
        "outputs": [{"internalType": "uint256[]", "name": "", "type": "uint256[]"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "uint256", "name": "intentId", "type": "uint256"}],
        "name": "intents",
        "outputs": [
            {"internalType": "address", "name": "agent", "type": "address"},
            {"internalType": "string", "name": "goal", "type": "string"},
            {"internalType": "string", "name": "constraints", "type": "string"},
            {"internalType": "uint256", "name": "maxCost", "type": "uint256"},
            {"internalType": "uint256", "name": "deadline", "type": "uint256"},
            {"internalType": "bool", "name": "fulfilled", "type": "bool"},
            {"internalType": "address", "name": "solver", "type": "address"},
            {"internalType": "uint256", "name": "actualCost", "type": "uint256"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "intentId", "type": "uint256"},
            {"internalType": "uint256", "name": "actualCost", "type": "uint256"}
        ],
        "name": "fulfillIntent",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]

# Solver strategies for different intent types
SOLVER_STRATEGIES = {
    "swap": "execute_swap",
    "transfer": "execute_transfer",
    "stake": "execute_stake",
    "provide_liquidity": "execute_liquidity",
    "default": "execute_generic"
}


class IntentAgent(BaseAgent):
    """
    Intent processor agent that monitors and fulfills intents.
    """
    
    def __init__(self):
        super().__init__(agent_type="intent", loop_interval=10.0)
        self.name = "INTENT"
        
        # Initialize learning
        self.memory = AgentMemory("IntentAgent")
        
        # Track processed intents
        self.processed_intents: set = set()
        self.pending_fulfillments: Dict[int, dict] = {}
        
        # Statistics
        self.stats = {
            "intents_processed": 0,
            "intents_fulfilled": 0,
            "total_rewards": 0.0
        }
        
        # Contract reference
        self.intent_contract = None
    
    def _init_contracts(self):
        """Initialize contract instances"""
        if self.intent_contract is None:
            try:
                intent_address = CONTRACTS.get("IntentMempool")
                if intent_address:
                    self.intent_contract = self.w3.eth.contract(
                        address=Web3.to_checksum_address(intent_address),
                        abi=INTENT_MEMPOOL_ABI
                    )
                    print(f"[{self.name}] IntentMempool contract loaded")
            except Exception as e:
                print(f"[{self.name}] Could not load IntentMempool: {e}")
    
    def get_active_intents(self) -> List[int]:
        """Get list of active intent IDs"""
        self._init_contracts()
        
        if not self.intent_contract:
            return []
        
        try:
            intent_ids = self.intent_contract.functions.getActiveIntents().call()
            return list(intent_ids)
        except Exception as e:
            print(f"[{self.name}] Error getting active intents: {e}")
            return []
    
    def get_intent_details(self, intent_id: int) -> Optional[dict]:
        """Get details of a specific intent"""
        if not self.intent_contract:
            return None
        
        try:
            result = self.intent_contract.functions.intents(intent_id).call()
            return {
                "id": intent_id,
                "agent": result[0],
                "goal": result[1],
                "constraints": result[2],
                "max_cost": result[3],
                "deadline": result[4],
                "fulfilled": result[5],
                "solver": result[6],
                "actual_cost": result[7]
            }
        except Exception as e:
            print(f"[{self.name}] Error getting intent {intent_id}: {e}")
            return None
    
    def can_solve(self, intent: dict) -> tuple:
        """
        Determine if we can solve this intent.
        Returns (can_solve, estimated_cost, strategy)
        """
        goal = intent.get("goal", "").lower()
        max_cost = intent.get("max_cost", 0)
        deadline = intent.get("deadline", 0)
        
        # Check deadline
        if deadline > 0 and deadline < time.time():
            return False, 0, None
        
        # Determine strategy based on goal keywords
        strategy = None
        for keyword, strat in SOLVER_STRATEGIES.items():
            if keyword in goal:
                strategy = strat
                break
        
        if not strategy:
            strategy = SOLVER_STRATEGIES["default"]
        
        # Estimate cost (80% of max to ensure profit)
        estimated_cost = int(max_cost * 0.8)
        
        # Check if we should proceed based on learning
        should_proceed, reason = self.memory.should_execute("fulfill_intent")
        if not should_proceed:
            print(f"[{self.name}] Skipping intent due to learning: {reason}")
            return False, 0, None
        
        return True, estimated_cost, strategy
    
    def execute_fulfillment(self, intent: dict, estimated_cost: int, strategy: str) -> dict:
        """Execute intent fulfillment"""
        intent_id = intent["id"]
        
        start_time = time.time()
        
        try:
            # Build fulfillment transaction
            nonce = self.w3.eth.get_transaction_count(self.account.address)
            
            tx = self.intent_contract.functions.fulfillIntent(
                intent_id,
                estimated_cost
            ).build_transaction({
                'from': self.account.address,
                'nonce': nonce,
                'gas': 200000,
                'chainId': 31337,
                'maxFeePerGas': self.w3.to_wei(2, 'gwei'),
                'maxPriorityFeePerGas': self.w3.to_wei(1, 'gwei'),
            })
            
            signed = self.account.sign_transaction(tx)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            
            # Wait for receipt
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=30)
            
            execution_time = int((time.time() - start_time) * 1000)
            gas_used = receipt.gasUsed
            
            if receipt.status == 1:
                # Calculate reward (solver gets 80% of actual cost)
                reward = estimated_cost * 0.8 / 1e6  # USDC
                
                # Record success
                self.memory.record_action(ActionRecord(
                    agent_name=self.name,
                    action_type="fulfill_intent",
                    parameters={"intent_id": intent_id, "strategy": strategy},
                    timestamp=time.time(),
                    outcome="success",
                    result_value=reward,
                    gas_used=gas_used,
                    execution_time_ms=execution_time,
                    context={"goal": intent.get("goal", "")}
                ))
                
                self.stats["intents_fulfilled"] += 1
                self.stats["total_rewards"] += reward
                
                return {
                    "success": True,
                    "tx_hash": tx_hash.hex(),
                    "reward": reward,
                    "gas_used": gas_used
                }
            else:
                # Record failure
                self.memory.record_action(ActionRecord(
                    agent_name=self.name,
                    action_type="fulfill_intent",
                    parameters={"intent_id": intent_id, "strategy": strategy},
                    timestamp=time.time(),
                    outcome="failure",
                    result_value=0,
                    gas_used=gas_used,
                    execution_time_ms=execution_time,
                    context={"goal": intent.get("goal", ""), "error": "tx_reverted"}
                ))
                
                return {"success": False, "error": "Transaction reverted"}
                
        except Exception as e:
            self.memory.record_action(ActionRecord(
                agent_name=self.name,
                action_type="fulfill_intent",
                parameters={"intent_id": intent_id, "strategy": strategy},
                timestamp=time.time(),
                outcome="failure",
                result_value=0,
                gas_used=0,
                execution_time_ms=int((time.time() - start_time) * 1000),
                context={"goal": intent.get("goal", ""), "error": str(e)}
            ))
            
            return {"success": False, "error": str(e)}
    
    def process_intents(self):
        """Process all active intents"""
        intent_ids = self.get_active_intents()
        
        for intent_id in intent_ids:
            if intent_id in self.processed_intents:
                continue
            
            intent = self.get_intent_details(intent_id)
            if not intent or intent["fulfilled"]:
                self.processed_intents.add(intent_id)
                continue
            
            self.stats["intents_processed"] += 1
            
            print(f"[{self.name}] Processing intent #{intent_id}")
            print(f"[{self.name}]   Goal: {intent['goal'][:50]}...")
            print(f"[{self.name}]   Max Cost: {intent['max_cost'] / 1e6} USDC")
            
            # Check if we can solve it
            can_solve, estimated_cost, strategy = self.can_solve(intent)
            
            if not can_solve:
                print(f"[{self.name}]   Cannot solve - skipping")
                continue
            
            print(f"[{self.name}]   Strategy: {strategy}")
            print(f"[{self.name}]   Estimated Cost: {estimated_cost / 1e6} USDC")
            
            # Execute fulfillment
            result = self.execute_fulfillment(intent, estimated_cost, strategy)
            
            if result["success"]:
                print(f"[{self.name}]   SUCCESS! Reward: ${result['reward']:.2f}")
                self.processed_intents.add(intent_id)
            else:
                print(f"[{self.name}]   FAILED: {result['error']}")
    
    def execute(self):
        """Main processing loop"""
        self._init_contracts()
        
        if not self.intent_contract:
            return
        
        self.process_intents()
        
        # Print stats periodically
        if not hasattr(self, '_loop_count'):
            self._loop_count = 0
        self._loop_count += 1
        
        if self._loop_count % 6 == 0:  # Every minute
            print(f"[{self.name}] Stats: {self.stats['intents_fulfilled']}/{self.stats['intents_processed']} fulfilled | "
                  f"Total rewards: ${self.stats['total_rewards']:.2f}")


if __name__ == "__main__":
    agent = IntentAgent()
    agent.run_forever()
