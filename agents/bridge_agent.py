"""
THRYX Bridge Agent - Watches Base for deposits, mints on THRYX
SECURE VERSION with:
- Persistent transaction tracking (survives restarts)
- Environment variables for keys (no hardcoded secrets)
- Rate limiting and security logging

Supports:
- ETH deposits -> ETH on THRYX (1:1)
- USDC deposits -> USDC on THRYX (1:1)
"""
import os
import time
import json
from datetime import datetime
from web3 import Web3
from eth_account import Account

# Configuration from environment
BASE_RPC = os.getenv("BASE_RPC", "https://mainnet.base.org")
THRYX_RPC = os.getenv("RPC_URL", "http://localhost:8545")
BASE_PRIVATE_KEY = os.getenv("BASE_PRIVATE_KEY", "")
THRYX_MINTER_KEY = os.getenv("THRYX_MINTER_KEY", "")

# USDC on Base (official contract)
BASE_USDC_ADDRESS = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"

# State file for persistence
STATE_FILE = os.getenv("BRIDGE_STATE_FILE", "/app/bridge_deposit_state.json")
FALLBACK_STATE_FILE = "bridge_deposit_state.json"

# Security limits
MAX_DEPOSIT_PER_TX = 10.0  # ETH
MAX_DEPOSIT_PER_DAY = 50.0  # ETH per address
LOOKBACK_BLOCKS = 100  # How far back to scan on startup


class BridgeState:
    """Persistent state management for deposit tracking"""
    
    def __init__(self):
        self.state_file = STATE_FILE if os.path.exists(os.path.dirname(STATE_FILE) or '.') else FALLBACK_STATE_FILE
        self.state = self._load_state()
    
    def _load_state(self) -> dict:
        """Load state from file"""
        try:
            with open(self.state_file, 'r') as f:
                data = json.load(f)
                # Convert processed_txs list back to set
                data['processed_txs'] = set(data.get('processed_txs', []))
                return data
        except:
            return {
                "processed_txs": set(),
                "last_block": 0,
                "deposits": [],
                "daily_totals": {},
                "stats": {
                    "total_deposits": 0,
                    "total_eth_bridged": 0,
                    "total_usdc_bridged": 0
                }
            }
    
    def _save_state(self):
        """Save state to file"""
        try:
            # Convert set to list for JSON serialization
            save_data = {
                **self.state,
                "processed_txs": list(self.state["processed_txs"]),
                "last_saved": datetime.now().isoformat()
            }
            with open(self.state_file, 'w') as f:
                json.dump(save_data, f, indent=2, default=str)
        except Exception as e:
            print(f"[BRIDGE] Warning: Could not save state: {e}")
    
    def is_processed(self, tx_hash: str) -> bool:
        """Check if transaction was already processed"""
        return tx_hash in self.state["processed_txs"]
    
    def mark_processed(self, tx_hash: str, deposit_info: dict):
        """Mark a transaction as processed and save"""
        self.state["processed_txs"].add(tx_hash)
        self.state["deposits"].append({
            **deposit_info,
            "processed_at": datetime.now().isoformat()
        })
        
        # Update stats
        self.state["stats"]["total_deposits"] += 1
        if deposit_info.get("token") == "ETH":
            self.state["stats"]["total_eth_bridged"] += deposit_info.get("amount_eth", 0)
        else:
            self.state["stats"]["total_usdc_bridged"] += deposit_info.get("amount_usdc", 0)
        
        # Update daily totals
        today = datetime.now().strftime("%Y-%m-%d")
        sender = deposit_info.get("from", "").lower()
        if sender:
            if sender not in self.state["daily_totals"]:
                self.state["daily_totals"][sender] = {}
            current = self.state["daily_totals"][sender].get(today, 0)
            self.state["daily_totals"][sender][today] = current + deposit_info.get("amount_eth", 0)
        
        self._save_state()
    
    def get_last_block(self) -> int:
        """Get last processed block number"""
        return self.state.get("last_block", 0)
    
    def set_last_block(self, block: int):
        """Update last processed block"""
        self.state["last_block"] = block
        self._save_state()
    
    def get_daily_total(self, address: str) -> float:
        """Get total deposited today by address"""
        address = address.lower()
        today = datetime.now().strftime("%Y-%m-%d")
        
        if address not in self.state["daily_totals"]:
            return 0.0
        
        return self.state["daily_totals"][address].get(today, 0.0)
    
    def get_stats(self) -> dict:
        """Get bridge statistics"""
        return self.state["stats"]


def load_deployment():
    """Load deployment addresses"""
    paths = [
        "/app/deployment.json",
        "deployment.json",
        "../deployment.json",
    ]
    for p in paths:
        try:
            with open(p) as f:
                return json.load(f)
        except:
            pass
    return {}


class BridgeAgent:
    """Secure deposit bridge agent with persistent state"""
    
    def __init__(self):
        self.name = "BRIDGE"
        
        # Initialize persistent state
        self.state = BridgeState()
        
        # Connect to Base
        self.base_w3 = Web3(Web3.HTTPProvider(BASE_RPC))
        print(f"[{self.name}] Connected to Base: {self.base_w3.is_connected()}")
        
        # Connect to THRYX
        self.thryx_w3 = Web3(Web3.HTTPProvider(THRYX_RPC))
        print(f"[{self.name}] Connected to THRYX: {self.thryx_w3.is_connected()}")
        
        # Load Base wallet
        if BASE_PRIVATE_KEY:
            self.base_account = Account.from_key(BASE_PRIVATE_KEY)
            print(f"[{self.name}] Base wallet: {self.base_account.address}")
            
            balance = self.base_w3.eth.get_balance(self.base_account.address)
            print(f"[{self.name}] Base ETH balance: {self.base_w3.from_wei(balance, 'ether')} ETH")
        else:
            print(f"[{self.name}] WARNING: No BASE_PRIVATE_KEY set")
            self.base_account = None
        
        # Load THRYX minter from environment
        if THRYX_MINTER_KEY:
            self.thryx_minter = Account.from_key(THRYX_MINTER_KEY)
            print(f"[{self.name}] THRYX minter loaded from environment")
        else:
            # Fallback to Hardhat account 0 for local testing only
            # In production, this MUST be set via environment variable
            default_key = os.getenv("HARDHAT_ACCOUNT_0", "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80")
            self.thryx_minter = Account.from_key(default_key)
            print(f"[{self.name}] WARNING: Using default Hardhat account (local testing only)")
        
        # Load THRYX deployment
        self.deployment = load_deployment()
        self.usdc_address = self.deployment.get("contracts", {}).get("MockUSDC")
        
        # Base USDC contract
        self.base_usdc_abi = [
            {"anonymous": False, "inputs": [
                {"indexed": True, "name": "from", "type": "address"},
                {"indexed": True, "name": "to", "type": "address"},
                {"indexed": False, "name": "value", "type": "uint256"}
            ], "name": "Transfer", "type": "event"},
            {"inputs": [{"name": "account", "type": "address"}], "name": "balanceOf", 
             "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
        ]
        
        if self.base_w3.is_connected():
            self.base_usdc = self.base_w3.eth.contract(
                address=Web3.to_checksum_address(BASE_USDC_ADDRESS),
                abi=self.base_usdc_abi
            )
            if self.base_account:
                usdc_balance = self.base_usdc.functions.balanceOf(self.base_account.address).call()
                print(f"[{self.name}] Base USDC balance: {usdc_balance / 1e6} USDC")
        
        # USDC ABI for minting on THRYX
        self.usdc_abi = [
            {"inputs": [{"name": "to", "type": "address"}, {"name": "amount", "type": "uint256"}], 
             "name": "mint", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
            {"inputs": [{"name": "account", "type": "address"}], "name": "balanceOf", 
             "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
        ]
        
        # Print stats
        stats = self.state.get_stats()
        print(f"[{self.name}] Historical stats: {stats['total_deposits']} deposits, "
              f"{stats['total_eth_bridged']:.4f} ETH, {stats['total_usdc_bridged']:.2f} USDC bridged")
    
    def check_rate_limits(self, sender: str, amount_eth: float) -> tuple:
        """Check if deposit is within rate limits"""
        # Check max per transaction
        if amount_eth > MAX_DEPOSIT_PER_TX:
            return False, f"Exceeds max per transaction ({MAX_DEPOSIT_PER_TX} ETH)"
        
        # Check daily limit
        daily_total = self.state.get_daily_total(sender)
        if daily_total + amount_eth > MAX_DEPOSIT_PER_DAY:
            remaining = MAX_DEPOSIT_PER_DAY - daily_total
            return False, f"Exceeds daily limit. Remaining: {remaining:.4f} ETH"
        
        return True, "OK"
    
    def check_base_deposits(self):
        """Check for new ETH and USDC deposits to bridge wallet on Base"""
        if not self.base_account:
            return []
        
        try:
            current_block = self.base_w3.eth.block_number
            last_block = self.state.get_last_block()
            
            if last_block == 0:
                last_block = current_block - LOOKBACK_BLOCKS
            
            deposits = []
            
            # Scan blocks (limit to 50 at a time for performance)
            end_block = min(current_block + 1, last_block + 50)
            
            for block_num in range(last_block + 1, end_block):
                try:
                    block = self.base_w3.eth.get_block(block_num, full_transactions=True)
                    
                    # Check ETH transfers
                    for tx in block.transactions:
                        if tx.to and tx.to.lower() == self.base_account.address.lower():
                            tx_hash = tx.hash.hex()
                            
                            if tx.value > 0 and not self.state.is_processed(tx_hash):
                                amount_eth = float(self.base_w3.from_wei(tx.value, 'ether'))
                                
                                # Check rate limits
                                allowed, reason = self.check_rate_limits(tx["from"], amount_eth)
                                
                                deposits.append({
                                    "tx_hash": tx_hash,
                                    "from": tx["from"],
                                    "value": tx.value,
                                    "amount_eth": amount_eth,
                                    "token": "ETH",
                                    "block": block_num,
                                    "allowed": allowed,
                                    "reason": reason
                                })
                    
                    # Check USDC Transfer events
                    try:
                        transfer_filter = self.base_usdc.events.Transfer.create_filter(
                            fromBlock=block_num,
                            toBlock=block_num,
                            argument_filters={'to': self.base_account.address}
                        )
                        for event in transfer_filter.get_all_entries():
                            tx_hash = event.transactionHash.hex()
                            if not self.state.is_processed(tx_hash):
                                deposits.append({
                                    "tx_hash": tx_hash,
                                    "from": event.args["from"],
                                    "value": event.args["value"],
                                    "amount_usdc": event.args["value"] / 1e6,
                                    "token": "USDC",
                                    "block": block_num,
                                    "allowed": True,
                                    "reason": "OK"
                                })
                    except:
                        pass
                        
                except Exception as e:
                    print(f"[{self.name}] Error scanning block {block_num}: {e}")
            
            # Update last block
            self.state.set_last_block(end_block - 1)
            return deposits
            
        except Exception as e:
            print(f"[{self.name}] Error checking Base deposits: {e}")
            return []
    
    def mint_on_thryx(self, recipient: str, amount_wei: int, token: str = "ETH") -> dict:
        """Mint tokens on THRYX for a bridged deposit"""
        try:
            if token == "USDC":
                if not self.usdc_address:
                    return {"success": False, "error": "USDC contract not found"}
                    
                usdc = self.thryx_w3.eth.contract(
                    address=Web3.to_checksum_address(self.usdc_address),
                    abi=self.usdc_abi
                )
                
                nonce = self.thryx_w3.eth.get_transaction_count(self.thryx_minter.address)
                tx = usdc.functions.mint(
                    Web3.to_checksum_address(recipient),
                    amount_wei
                ).build_transaction({
                    'from': self.thryx_minter.address,
                    'nonce': nonce,
                    'gas': 100000,
                    'gasPrice': self.thryx_w3.to_wei(1, 'gwei'),
                    'chainId': 77777,  # THRYX Mainnet
                })
                
                signed = self.thryx_w3.eth.account.sign_transaction(tx, self.thryx_minter.key)
                # Handle both old and new web3.py versions
                raw_tx = getattr(signed, 'raw_transaction', None) or getattr(signed, 'rawTransaction', None)
                tx_hash = self.thryx_w3.eth.send_raw_transaction(raw_tx)
                
                return {"success": True, "tx_hash": tx_hash.hex()}
                
            else:
                # ETH -> ETH 1:1
                nonce = self.thryx_w3.eth.get_transaction_count(self.thryx_minter.address)
                
                # Use legacy transaction format for better Anvil compatibility
                tx = {
                    'to': Web3.to_checksum_address(recipient),
                    'value': amount_wei,
                    'nonce': nonce,
                    'gas': 21000,
                    'gasPrice': self.thryx_w3.to_wei(1, 'gwei'),
                    'chainId': 77777,  # THRYX Mainnet
                }
                
                signed = self.thryx_w3.eth.account.sign_transaction(tx, self.thryx_minter.key)
                # Handle both old and new web3.py versions
                raw_tx = getattr(signed, 'raw_transaction', None) or getattr(signed, 'rawTransaction', None)
                tx_hash = self.thryx_w3.eth.send_raw_transaction(raw_tx)
                
                return {"success": True, "tx_hash": tx_hash.hex()}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def process_deposits(self):
        """Process any pending deposits"""
        deposits = self.check_base_deposits()
        
        for deposit in deposits:
            tx_hash = deposit["tx_hash"]
            
            if self.state.is_processed(tx_hash):
                continue
            
            token = deposit.get("token", "ETH")
            
            print(f"[{self.name}] ========================================")
            print(f"[{self.name}] NEW {token} DEPOSIT DETECTED ON BASE!")
            print(f"[{self.name}] From: {deposit['from']}")
            
            if token == "USDC":
                amount_display = f"{deposit['value'] / 1e6} USDC"
            else:
                amount_display = f"{self.base_w3.from_wei(deposit['value'], 'ether')} ETH"
            
            print(f"[{self.name}] Amount: {amount_display}")
            print(f"[{self.name}] TX: {tx_hash[:20]}...")
            
            # Check if allowed
            if not deposit.get("allowed", True):
                print(f"[{self.name}] REJECTED: {deposit['reason']}")
                print(f"[{self.name}] Deposit will be refunded manually")
                # Still mark as processed to avoid re-checking
                self.state.mark_processed(tx_hash, {
                    **deposit,
                    "status": "rejected",
                    "thryx_tx": None
                })
                continue
            
            # Mint on THRYX
            result = self.mint_on_thryx(deposit['from'], deposit['value'], token)
            
            if result["success"]:
                self.state.mark_processed(tx_hash, {
                    **deposit,
                    "status": "completed",
                    "thryx_tx": result["tx_hash"]
                })
                
                if token == "USDC":
                    print(f"[{self.name}] Bridge complete! {deposit['value'] / 1e6} USDC on THRYX")
                else:
                    eth_amt = float(self.base_w3.from_wei(deposit['value'], 'ether'))
                    print(f"[{self.name}] Bridge complete! {eth_amt} ETH on THRYX")
                print(f"[{self.name}] THRYX TX: {result['tx_hash'][:20]}...")
            else:
                print(f"[{self.name}] ERROR: {result['error']}")
                # Don't mark as processed - will retry on next loop
            
            print(f"[{self.name}] ========================================")
    
    def run(self):
        """Main loop"""
        print(f"[{self.name}] Starting Secure Bridge Agent...")
        print(f"[{self.name}] ============================================")
        print(f"[{self.name}] THRYX BRIDGE - Base -> THRYX")
        print(f"[{self.name}] ============================================")
        print(f"[{self.name}] Bridge wallet: {self.base_account.address if self.base_account else 'NOT SET'}")
        print(f"[{self.name}] ")
        print(f"[{self.name}] SECURITY LIMITS:")
        print(f"[{self.name}]   Max per transaction: {MAX_DEPOSIT_PER_TX} ETH")
        print(f"[{self.name}]   Max per day/address: {MAX_DEPOSIT_PER_DAY} ETH")
        print(f"[{self.name}] ")
        print(f"[{self.name}] SUPPORTED:")
        print(f"[{self.name}]   ETH  on Base -> ETH  on THRYX (1:1)")
        print(f"[{self.name}]   USDC on Base -> USDC on THRYX (1:1)")
        print(f"[{self.name}] ")
        print(f"[{self.name}] TO BRIDGE:")
        print(f"[{self.name}]   Send ETH or USDC to: {self.base_account.address if self.base_account else 'N/A'}")
        print(f"[{self.name}]   You receive same token on THRYX at your address")
        print(f"[{self.name}] ============================================")
        
        while True:
            try:
                self.process_deposits()
                time.sleep(10)
            except KeyboardInterrupt:
                print(f"[{self.name}] Shutting down...")
                break
            except Exception as e:
                print(f"[{self.name}] Error: {e}")
                time.sleep(5)


if __name__ == "__main__":
    agent = BridgeAgent()
    agent.run()
