"""
Thryx Base Agent
Common functionality for all autonomous agents
"""
import time
import logging
from abc import ABC, abstractmethod
from typing import Optional, Any
from web3 import Web3
from eth_account import Account

from config import RPC_URL, AGENT_PRIVATE_KEYS, CONTRACTS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(name)s] %(asctime)s - %(message)s',
    datefmt='%H:%M:%S'
)


class BaseAgent(ABC):
    """Base class for all Thryx autonomous agents"""
    
    def __init__(self, agent_type: str, loop_interval: float = 10.0):
        self.agent_type = agent_type
        self.loop_interval = loop_interval
        self.logger = logging.getLogger(agent_type.upper())
        
        # Initialize Web3
        self.w3 = Web3(Web3.HTTPProvider(RPC_URL))
        
        # Load account
        private_key = AGENT_PRIVATE_KEYS.get(agent_type)
        if not private_key:
            raise ValueError(f"No private key found for agent type: {agent_type}")
        
        self.account = Account.from_key(private_key)
        self.address = self.account.address
        
        # Stats
        self.tx_count = 0
        self.error_count = 0
        self.start_time = time.time()
        
        self.logger.info(f"Initialized at {self.address}")
    
    def connect(self) -> bool:
        """Check connection to RPC"""
        try:
            block = self.w3.eth.block_number
            self.logger.info(f"Connected to RPC at block {block}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to RPC: {e}")
            return False
    
    def wait_for_rpc(self, max_retries: int = 30, delay: float = 2.0):
        """Wait for RPC to become available"""
        for i in range(max_retries):
            if self.connect():
                return True
            self.logger.info(f"Waiting for RPC... ({i+1}/{max_retries})")
            time.sleep(delay)
        raise ConnectionError("RPC not available after max retries")
    
    def get_contract(self, name: str, abi: list) -> Any:
        """Get a contract instance"""
        address = CONTRACTS.get(name)
        if not address or address == "0x0000000000000000000000000000000000000000":
            raise ValueError(f"Contract {name} not found in deployment")
        return self.w3.eth.contract(address=address, abi=abi)
    
    def send_transaction(self, tx: dict, max_retries: int = 3) -> Optional[str]:
        """Send a signed transaction with retry logic"""
        for attempt in range(max_retries):
            try:
                # Add nonce and gas - use web3.py v6 compatible keys
                tx['nonce'] = self.w3.eth.get_transaction_count(self.address)
                tx['from'] = self.address
                
                if 'gas' not in tx:
                    tx['gas'] = self.w3.eth.estimate_gas(tx)
                
                # Use maxFeePerGas for EIP-1559 compatible transactions
                if 'maxFeePerGas' not in tx and 'gasPrice' not in tx:
                    base_fee = self.w3.eth.get_block('latest')['baseFeePerGas']
                    tx['maxFeePerGas'] = base_fee * 2
                    tx['maxPriorityFeePerGas'] = self.w3.to_wei(1, 'gwei')
                
                # Sign and send
                signed = self.account.sign_transaction(tx)
                tx_hash = self.w3.eth.send_raw_transaction(signed.rawTransaction)
                
                # Wait for receipt
                receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=30)
                
                if receipt['status'] == 1:
                    self.tx_count += 1
                    self.logger.info(f"TX successful: {tx_hash.hex()[:16]}...")
                    return tx_hash.hex()
                else:
                    self.logger.warning(f"TX reverted: {tx_hash.hex()[:16]}...")
                    return None
                    
            except Exception as e:
                self.error_count += 1
                self.logger.warning(f"TX attempt {attempt+1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)
        
        return None
    
    def call_contract(self, contract: Any, function_name: str, *args) -> Any:
        """Call a contract view function"""
        try:
            func = getattr(contract.functions, function_name)
            return func(*args).call()
        except Exception as e:
            self.logger.error(f"Contract call {function_name} failed: {e}")
            return None
    
    def build_contract_tx(self, contract: Any, function_name: str, *args) -> dict:
        """Build a transaction for a contract function"""
        func = getattr(contract.functions, function_name)
        return func(*args).build_transaction({
            'from': self.address,
            'chainId': self.w3.eth.chain_id,
        })
    
    @abstractmethod
    def execute(self):
        """Execute one iteration of the agent's main logic"""
        pass
    
    def run_forever(self):
        """Run the agent loop forever"""
        self.logger.info("Starting autonomous loop...")
        self.wait_for_rpc()
        
        while True:
            try:
                self.execute()
            except KeyboardInterrupt:
                self.logger.info("Shutting down...")
                break
            except Exception as e:
                self.error_count += 1
                self.logger.error(f"Error in main loop: {e}")
            
            time.sleep(self.loop_interval)
    
    def get_stats(self) -> dict:
        """Get agent statistics"""
        uptime = time.time() - self.start_time
        return {
            "agent_type": self.agent_type,
            "address": self.address,
            "tx_count": self.tx_count,
            "error_count": self.error_count,
            "uptime_seconds": uptime,
            "tx_per_minute": (self.tx_count / uptime) * 60 if uptime > 0 else 0
        }
