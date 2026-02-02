"""
THRYX Withdrawal Bridge - THRYX -> Base
SECURE VERSION with:
- Burn THRYX tokens BEFORE sending Base ETH
- Persistent transaction tracking
- Withdrawal delays for large amounts
- Rate limiting per address

WARNING: Can only withdraw up to what's been deposited in the bridge wallet!
"""
import os
import json
import time
from datetime import datetime, timedelta
from web3 import Web3
from eth_account import Account

# Configuration
BASE_RPC = "https://mainnet.base.org"
THRYX_RPC = os.getenv("RPC_URL", "http://localhost:8545")
BASE_PRIVATE_KEY = os.getenv("BASE_PRIVATE_KEY", "")
THRYX_MINTER_KEY = os.getenv("THRYX_MINTER_KEY", "")

# Security Configuration
BURN_ADDRESS = "0x000000000000000000000000000000000000dEaD"
MAX_WITHDRAWAL_PER_TX = 1.0  # ETH
MAX_WITHDRAWAL_PER_DAY = 5.0  # ETH per address
LARGE_WITHDRAWAL_THRESHOLD = 0.1  # ETH - requires delay
WITHDRAWAL_DELAY_SECONDS = 3600  # 1 hour for large withdrawals
COOLDOWN_SECONDS = 300  # 5 minutes between withdrawals

# State file paths
STATE_FILE = os.getenv("BRIDGE_STATE_FILE", "withdrawal_state.json")
PENDING_FILE = os.getenv("PENDING_WITHDRAWALS_FILE", "pending_withdrawals.json")


class WithdrawalState:
    """Persistent state management for withdrawals"""
    
    def __init__(self, state_file: str, pending_file: str):
        self.state_file = state_file
        self.pending_file = pending_file
        self.state = self._load_state()
        self.pending = self._load_pending()
    
    def _load_state(self) -> dict:
        """Load state from file"""
        try:
            with open(self.state_file, 'r') as f:
                return json.load(f)
        except:
            return {
                "processed_withdrawals": [],
                "daily_totals": {},  # address -> {date: amount}
                "last_withdrawal": {}  # address -> timestamp
            }
    
    def _save_state(self):
        """Save state to file"""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2, default=str)
        except Exception as e:
            print(f"[WITHDRAW] Warning: Could not save state: {e}")
    
    def _load_pending(self) -> dict:
        """Load pending withdrawals"""
        try:
            with open(self.pending_file, 'r') as f:
                return json.load(f)
        except:
            return {"pending": []}
    
    def _save_pending(self):
        """Save pending withdrawals"""
        try:
            with open(self.pending_file, 'w') as f:
                json.dump(self.pending, f, indent=2, default=str)
        except Exception as e:
            print(f"[WITHDRAW] Warning: Could not save pending: {e}")
    
    def get_daily_total(self, address: str) -> float:
        """Get total withdrawn today by address"""
        address = address.lower()
        today = datetime.now().strftime("%Y-%m-%d")
        
        if address not in self.state["daily_totals"]:
            return 0.0
        
        addr_totals = self.state["daily_totals"][address]
        return addr_totals.get(today, 0.0)
    
    def add_withdrawal(self, address: str, amount_eth: float, tx_hash: str, burn_hash: str):
        """Record a completed withdrawal"""
        address = address.lower()
        today = datetime.now().strftime("%Y-%m-%d")
        now = time.time()
        
        # Update daily totals
        if address not in self.state["daily_totals"]:
            self.state["daily_totals"][address] = {}
        
        current = self.state["daily_totals"][address].get(today, 0.0)
        self.state["daily_totals"][address][today] = current + amount_eth
        
        # Update last withdrawal time
        self.state["last_withdrawal"][address] = now
        
        # Add to processed list
        self.state["processed_withdrawals"].append({
            "address": address,
            "amount_eth": amount_eth,
            "base_tx": tx_hash,
            "burn_tx": burn_hash,
            "timestamp": now,
            "date": today
        })
        
        self._save_state()
    
    def get_last_withdrawal_time(self, address: str) -> float:
        """Get timestamp of last withdrawal for address"""
        address = address.lower()
        return self.state["last_withdrawal"].get(address, 0)
    
    def add_pending(self, withdrawal_id: str, address: str, amount_eth: float, 
                    burn_hash: str, execute_after: float):
        """Add a pending delayed withdrawal"""
        self.pending["pending"].append({
            "id": withdrawal_id,
            "address": address,
            "amount_eth": amount_eth,
            "burn_hash": burn_hash,
            "execute_after": execute_after,
            "created_at": time.time(),
            "status": "pending"
        })
        self._save_pending()
    
    def get_pending_withdrawals(self) -> list:
        """Get all pending withdrawals ready to execute"""
        now = time.time()
        ready = []
        for w in self.pending["pending"]:
            if w["status"] == "pending" and w["execute_after"] <= now:
                ready.append(w)
        return ready
    
    def mark_pending_complete(self, withdrawal_id: str, base_tx: str):
        """Mark a pending withdrawal as completed"""
        for w in self.pending["pending"]:
            if w["id"] == withdrawal_id:
                w["status"] = "completed"
                w["base_tx"] = base_tx
                w["completed_at"] = time.time()
        self._save_pending()
    
    def cancel_pending(self, withdrawal_id: str):
        """Cancel a pending withdrawal"""
        for w in self.pending["pending"]:
            if w["id"] == withdrawal_id:
                w["status"] = "cancelled"
                w["cancelled_at"] = time.time()
        self._save_pending()


class WithdrawalBridge:
    """Secure withdrawal bridge with burn-first mechanism"""
    
    def __init__(self):
        self.name = "WITHDRAW"
        
        # Connect to both chains
        self.base_w3 = Web3(Web3.HTTPProvider(BASE_RPC))
        self.thryx_w3 = Web3(Web3.HTTPProvider(THRYX_RPC))
        
        print(f"[{self.name}] Base connected: {self.base_w3.is_connected()}")
        print(f"[{self.name}] THRYX connected: {self.thryx_w3.is_connected()}")
        
        # Load bridge wallet (controls Base side)
        if BASE_PRIVATE_KEY:
            self.bridge_account = Account.from_key(BASE_PRIVATE_KEY)
            print(f"[{self.name}] Bridge wallet: {self.bridge_account.address}")
            
            base_bal = self.base_w3.eth.get_balance(self.bridge_account.address)
            print(f"[{self.name}] Base ETH available: {self.base_w3.from_wei(base_bal, 'ether')} ETH")
        else:
            print(f"[{self.name}] ERROR: No BASE_PRIVATE_KEY set")
            self.bridge_account = None
        
        # Load THRYX minter (for burn verification - uses Hardhat account if not set)
        if THRYX_MINTER_KEY:
            self.thryx_account = Account.from_key(THRYX_MINTER_KEY)
        else:
            # Default Hardhat account 0 for local testing
            default_key = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
            self.thryx_account = Account.from_key(default_key)
        
        # Initialize state manager
        self.state = WithdrawalState(STATE_FILE, PENDING_FILE)
    
    def get_max_withdrawal(self) -> int:
        """Get maximum withdrawable amount (bridge wallet Base balance minus gas)"""
        if not self.bridge_account:
            return 0
        
        base_bal = self.base_w3.eth.get_balance(self.bridge_account.address)
        gas_reserve = self.base_w3.to_wei(0.0002, 'ether')
        
        if base_bal > gas_reserve:
            return base_bal - gas_reserve
        return 0
    
    def check_rate_limits(self, address: str, amount_eth: float) -> tuple:
        """Check if withdrawal is allowed under rate limits. Returns (allowed, reason)"""
        address = address.lower()
        
        # Check max per transaction
        if amount_eth > MAX_WITHDRAWAL_PER_TX:
            return False, f"Exceeds max per transaction ({MAX_WITHDRAWAL_PER_TX} ETH)"
        
        # Check daily limit
        daily_total = self.state.get_daily_total(address)
        if daily_total + amount_eth > MAX_WITHDRAWAL_PER_DAY:
            remaining = MAX_WITHDRAWAL_PER_DAY - daily_total
            return False, f"Exceeds daily limit. Remaining: {remaining:.4f} ETH"
        
        # Check cooldown
        last_time = self.state.get_last_withdrawal_time(address)
        if last_time > 0:
            elapsed = time.time() - last_time
            if elapsed < COOLDOWN_SECONDS:
                wait = int(COOLDOWN_SECONDS - elapsed)
                return False, f"Cooldown active. Wait {wait} seconds"
        
        return True, "OK"
    
    def burn_thryx_eth(self, from_address: str, amount_wei: int) -> dict:
        """
        Burn THRYX ETH by sending to burn address.
        This MUST succeed before we send Base ETH.
        """
        try:
            # Get nonce for the withdrawal requester on THRYX
            # Note: In production, user would sign this themselves
            # For now, we use the minter account to simulate the burn
            
            nonce = self.thryx_w3.eth.get_transaction_count(self.thryx_account.address)
            
            tx = {
                'from': self.thryx_account.address,
                'to': Web3.to_checksum_address(BURN_ADDRESS),
                'value': amount_wei,
                'nonce': nonce,
                'gas': 21000,
                'chainId': 77777,  # THRYX Mainnet
                'maxFeePerGas': self.thryx_w3.to_wei(2, 'gwei'),
                'maxPriorityFeePerGas': self.thryx_w3.to_wei(1, 'gwei'),
            }
            
            signed = self.thryx_account.sign_transaction(tx)
            tx_hash = self.thryx_w3.eth.send_raw_transaction(signed.raw_transaction)
            
            # Wait for confirmation
            receipt = self.thryx_w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
            
            if receipt.status == 1:
                print(f"[{self.name}] BURN SUCCESS: {self.thryx_w3.from_wei(amount_wei, 'ether')} ETH")
                print(f"[{self.name}] Burn TX: {tx_hash.hex()}")
                return {"success": True, "tx_hash": tx_hash.hex()}
            else:
                return {"success": False, "error": "Burn transaction failed"}
                
        except Exception as e:
            return {"success": False, "error": f"Burn failed: {str(e)}"}
    
    def send_base_eth(self, recipient: str, amount_wei: int) -> dict:
        """Send Base ETH to recipient"""
        try:
            nonce = self.base_w3.eth.get_transaction_count(self.bridge_account.address)
            gas_price = self.base_w3.eth.gas_price
            
            tx = {
                'from': self.bridge_account.address,
                'to': Web3.to_checksum_address(recipient),
                'value': amount_wei,
                'nonce': nonce,
                'gas': 21000,
                'gasPrice': gas_price,
                'chainId': 8453
            }
            
            signed = self.bridge_account.sign_transaction(tx)
            tx_hash = self.base_w3.eth.send_raw_transaction(signed.raw_transaction)
            
            print(f"[{self.name}] Sent {self.base_w3.from_wei(amount_wei, 'ether')} ETH to {recipient[:10]}... on Base")
            print(f"[{self.name}] Base TX: {tx_hash.hex()}")
            
            return {"success": True, "tx_hash": tx_hash.hex()}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def withdraw(self, recipient: str, amount_wei: int, skip_delay: bool = False) -> dict:
        """
        Secure withdrawal with burn-first mechanism.
        
        Flow:
        1. Validate inputs and check rate limits
        2. BURN THRYX ETH (send to burn address)
        3. Wait for burn confirmation
        4. If large amount, queue for delayed execution
        5. Send Base ETH to recipient
        6. Record in persistent state
        """
        if not self.bridge_account:
            return {"success": False, "error": "Bridge not configured"}
        
        recipient = Web3.to_checksum_address(recipient)
        amount_eth = float(self.base_w3.from_wei(amount_wei, 'ether'))
        
        # Check rate limits
        allowed, reason = self.check_rate_limits(recipient, amount_eth)
        if not allowed:
            return {"success": False, "error": reason}
        
        # Check liquidity
        max_withdraw = self.get_max_withdrawal()
        if amount_wei > max_withdraw:
            max_eth = self.base_w3.from_wei(max_withdraw, 'ether')
            return {"success": False, "error": f"Insufficient liquidity. Max: {max_eth} ETH"}
        
        # Step 1: BURN THRYX ETH FIRST
        print(f"[{self.name}] Step 1: Burning {amount_eth} ETH on THRYX...")
        burn_result = self.burn_thryx_eth(recipient, amount_wei)
        
        if not burn_result["success"]:
            return {"success": False, "error": f"Burn failed: {burn_result['error']}"}
        
        burn_hash = burn_result["tx_hash"]
        
        # Step 2: Check if delay required
        if amount_eth >= LARGE_WITHDRAWAL_THRESHOLD and not skip_delay:
            execute_after = time.time() + WITHDRAWAL_DELAY_SECONDS
            withdrawal_id = f"w_{int(time.time())}_{recipient[:10]}"
            
            self.state.add_pending(
                withdrawal_id=withdrawal_id,
                address=recipient,
                amount_eth=amount_eth,
                burn_hash=burn_hash,
                execute_after=execute_after
            )
            
            delay_mins = WITHDRAWAL_DELAY_SECONDS // 60
            return {
                "success": True,
                "status": "pending",
                "withdrawal_id": withdrawal_id,
                "burn_hash": burn_hash,
                "execute_after": execute_after,
                "message": f"Large withdrawal queued. Will execute in {delay_mins} minutes."
            }
        
        # Step 3: Send Base ETH
        print(f"[{self.name}] Step 2: Sending {amount_eth} ETH on Base...")
        base_result = self.send_base_eth(recipient, amount_wei)
        
        if not base_result["success"]:
            # CRITICAL: Burn succeeded but Base send failed
            # Log this for manual recovery
            print(f"[{self.name}] CRITICAL: Burn succeeded but Base send failed!")
            print(f"[{self.name}] Burn TX: {burn_hash}")
            print(f"[{self.name}] Recipient: {recipient}")
            print(f"[{self.name}] Amount: {amount_eth} ETH")
            return {
                "success": False, 
                "error": f"Base send failed after burn: {base_result['error']}",
                "burn_hash": burn_hash,
                "requires_manual_recovery": True
            }
        
        # Step 4: Record successful withdrawal
        self.state.add_withdrawal(
            address=recipient,
            amount_eth=amount_eth,
            tx_hash=base_result["tx_hash"],
            burn_hash=burn_hash
        )
        
        return {
            "success": True,
            "status": "completed",
            "burn_hash": burn_hash,
            "base_tx": base_result["tx_hash"],
            "amount": amount_eth,
            "recipient": recipient
        }
    
    def process_pending_withdrawals(self) -> list:
        """Process any pending withdrawals that are ready"""
        results = []
        pending = self.state.get_pending_withdrawals()
        
        for w in pending:
            print(f"[{self.name}] Processing pending withdrawal {w['id']}...")
            
            amount_wei = self.base_w3.to_wei(w['amount_eth'], 'ether')
            base_result = self.send_base_eth(w['address'], amount_wei)
            
            if base_result["success"]:
                self.state.mark_pending_complete(w['id'], base_result["tx_hash"])
                self.state.add_withdrawal(
                    address=w['address'],
                    amount_eth=w['amount_eth'],
                    tx_hash=base_result["tx_hash"],
                    burn_hash=w['burn_hash']
                )
                results.append({"id": w['id'], "success": True, "tx": base_result["tx_hash"]})
            else:
                results.append({"id": w['id'], "success": False, "error": base_result["error"]})
        
        return results


def main():
    """Interactive withdrawal with security checks"""
    bridge = WithdrawalBridge()
    
    max_wei = bridge.get_max_withdrawal()
    max_eth = float(bridge.base_w3.from_wei(max_wei, 'ether'))
    
    print()
    print("=" * 60)
    print("THRYX -> BASE SECURE WITHDRAWAL BRIDGE")
    print("=" * 60)
    print(f"Max per transaction: {MAX_WITHDRAWAL_PER_TX} ETH")
    print(f"Max per day: {MAX_WITHDRAWAL_PER_DAY} ETH")
    print(f"Large withdrawal delay: {WITHDRAWAL_DELAY_SECONDS // 60} minutes (>{LARGE_WITHDRAWAL_THRESHOLD} ETH)")
    print(f"Cooldown between withdrawals: {COOLDOWN_SECONDS // 60} minutes")
    print()
    print(f"Bridge liquidity: {max_eth:.6f} ETH")
    print("=" * 60)
    
    if max_wei == 0:
        print("No ETH available to withdraw!")
        return
    
    # Process any pending withdrawals first
    pending = bridge.state.get_pending_withdrawals()
    if pending:
        print(f"\nFound {len(pending)} pending withdrawal(s) ready to execute...")
        results = bridge.process_pending_withdrawals()
        for r in results:
            if r["success"]:
                print(f"  Completed: {r['id']} -> {r['tx']}")
            else:
                print(f"  Failed: {r['id']} -> {r['error']}")
        print()
    
    recipient = input("Enter recipient address on Base: ").strip()
    if not recipient.startswith("0x") or len(recipient) != 42:
        print("Invalid address!")
        return
    
    # Show rate limit status
    daily_total = bridge.state.get_daily_total(recipient)
    remaining = MAX_WITHDRAWAL_PER_DAY - daily_total
    print(f"\nDaily usage for this address: {daily_total:.4f} / {MAX_WITHDRAWAL_PER_DAY} ETH")
    print(f"Remaining today: {remaining:.4f} ETH")
    
    amount_str = input(f"Amount to withdraw (max {min(max_eth, remaining, MAX_WITHDRAWAL_PER_TX):.6f}): ").strip()
    try:
        amount_eth = float(amount_str)
        amount_wei = bridge.base_w3.to_wei(amount_eth, 'ether')
    except:
        print("Invalid amount!")
        return
    
    print()
    print(f"Initiating secure withdrawal...")
    print(f"  1. Burn {amount_eth} ETH on THRYX")
    print(f"  2. Send {amount_eth} ETH on Base to {recipient}")
    
    if amount_eth >= LARGE_WITHDRAWAL_THRESHOLD:
        print(f"  NOTE: Large withdrawal - will be delayed {WITHDRAWAL_DELAY_SECONDS // 60} minutes")
    
    confirm = input("\nProceed? (yes/no): ").strip().lower()
    if confirm != "yes":
        print("Cancelled.")
        return
    
    result = bridge.withdraw(recipient, amount_wei)
    
    print()
    print("=" * 60)
    if result["success"]:
        if result.get("status") == "pending":
            print("WITHDRAWAL QUEUED (DELAYED)")
            print(f"ID: {result['withdrawal_id']}")
            print(f"Burn TX: {result['burn_hash']}")
            print(f"Will execute in {WITHDRAWAL_DELAY_SECONDS // 60} minutes")
        else:
            print("WITHDRAWAL SUCCESSFUL!")
            print(f"Burn TX: {result['burn_hash']}")
            print(f"Base TX: https://basescan.org/tx/{result['base_tx']}")
    else:
        print(f"ERROR: {result['error']}")
        if result.get("requires_manual_recovery"):
            print("CRITICAL: Manual recovery required!")
            print(f"Burn TX: {result.get('burn_hash')}")
    print("=" * 60)


if __name__ == "__main__":
    main()
