"""
THRYX Withdrawal Agent
Processes L2 withdrawals and sends ETH on Base (L1)

Flow:
1. Monitor L2WithdrawalContract for pending withdrawals
2. Once challenge period passes, process withdrawal
3. Send ETH on Base to user
4. Mark withdrawal as processed on L2
"""
import os
import sys
import time
import json
from web3 import Web3
from eth_account import Account

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents.config import (
    RPC_URL, 
    AGENT_PRIVATE_KEYS, 
    CONTRACTS, 
    L2_WITHDRAWAL_ABI,
    send_alert,
    IS_PRODUCTION
)

# ==================== Configuration ====================

# L2 (THRYX) configuration
L2_RPC_URL = RPC_URL
WITHDRAWAL_CONTRACT = CONTRACTS.get("L2WithdrawalContract", "")

# L1 (Base) configuration
BASE_RPC_URL = os.getenv("BASE_RPC_URL", "https://mainnet.base.org")
BASE_PRIVATE_KEY = os.getenv("BASE_PRIVATE_KEY", "")

# Agent configuration
WITHDRAWAL_PRIVATE_KEY = AGENT_PRIVATE_KEYS.get("withdrawal", "")
POLL_INTERVAL = 30  # seconds
MAX_GAS_PRICE_GWEI = 50  # Maximum gas price for L1 transactions
MIN_BALANCE_ETH = 0.1  # Minimum balance to keep for gas

# ==================== Initialize Web3 ====================

print(f"[WITHDRAWAL] Connecting to L2: {L2_RPC_URL}")
print(f"[WITHDRAWAL] Connecting to L1: {BASE_RPC_URL}")

w3_l2 = Web3(Web3.HTTPProvider(L2_RPC_URL))
w3_l1 = Web3(Web3.HTTPProvider(BASE_RPC_URL))

# Validate connections
if not w3_l2.is_connected():
    print("[WITHDRAWAL] ERROR: Cannot connect to L2!")
    sys.exit(1)

if not w3_l1.is_connected():
    print("[WITHDRAWAL] ERROR: Cannot connect to L1 (Base)!")
    if IS_PRODUCTION:
        sys.exit(1)
    else:
        print("[WITHDRAWAL] Running in L2-only mode for development")

# Load accounts
if WITHDRAWAL_PRIVATE_KEY:
    l2_account = Account.from_key(WITHDRAWAL_PRIVATE_KEY)
    print(f"[WITHDRAWAL] L2 account: {l2_account.address}")
else:
    print("[WITHDRAWAL] ERROR: No L2 withdrawal key!")
    sys.exit(1)

if BASE_PRIVATE_KEY:
    l1_account = Account.from_key(BASE_PRIVATE_KEY)
    print(f"[WITHDRAWAL] L1 account: {l1_account.address}")
else:
    print("[WITHDRAWAL] WARNING: No L1 key - running in monitor-only mode")
    l1_account = None

# Load contract
if not WITHDRAWAL_CONTRACT or WITHDRAWAL_CONTRACT == "0x0000000000000000000000000000000000000000":
    print("[WITHDRAWAL] ERROR: L2WithdrawalContract not deployed!")
    print("[WITHDRAWAL] Run deployment first.")
    sys.exit(1)

# Extended ABI for withdrawal contract
WITHDRAWAL_ABI_FULL = [
    {"inputs": [], "name": "getPendingWithdrawals", "outputs": [{"name": "", "type": "uint256[]"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"name": "withdrawalId", "type": "uint256"}], "name": "getWithdrawal", "outputs": [
        {"name": "user", "type": "address"},
        {"name": "amount", "type": "uint256"},
        {"name": "timestamp", "type": "uint256"},
        {"name": "processed", "type": "bool"},
        {"name": "l1TxHash", "type": "bytes32"},
        {"name": "canProcess", "type": "bool"}
    ], "stateMutability": "view", "type": "function"},
    {"inputs": [{"name": "withdrawalId", "type": "uint256"}, {"name": "l1TxHash", "type": "bytes32"}], "name": "markProcessed", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [], "name": "relayer", "outputs": [{"name": "", "type": "address"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "challengePeriod", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
]

withdrawal_contract = w3_l2.eth.contract(
    address=Web3.to_checksum_address(WITHDRAWAL_CONTRACT),
    abi=WITHDRAWAL_ABI_FULL
)

# ==================== Stats ====================

stats = {
    "processed": 0,
    "failed": 0,
    "total_eth_sent": 0,
    "start_time": time.time(),
}

# ==================== Helper Functions ====================

def get_l1_balance():
    """Get L1 account balance."""
    if not l1_account:
        return 0
    return w3_l1.eth.get_balance(l1_account.address)

def get_l2_balance():
    """Get L2 account balance."""
    return w3_l2.eth.get_balance(l2_account.address)

def check_gas_price():
    """Check if L1 gas price is acceptable."""
    if not w3_l1.is_connected():
        return True
    
    gas_price = w3_l1.eth.gas_price
    gas_price_gwei = gas_price / 1e9
    
    if gas_price_gwei > MAX_GAS_PRICE_GWEI:
        print(f"[WITHDRAWAL] Gas price too high: {gas_price_gwei:.2f} gwei > {MAX_GAS_PRICE_GWEI} gwei")
        return False
    
    return True

def send_eth_on_l1(to_address: str, amount_wei: int) -> str:
    """Send ETH on Base (L1) to user."""
    if not l1_account:
        raise Exception("No L1 account configured")
    
    # Check balance
    balance = get_l1_balance()
    if balance < amount_wei + (0.01 * 1e18):  # Need extra for gas
        raise Exception(f"Insufficient L1 balance: {balance / 1e18:.4f} ETH")
    
    # Build transaction
    nonce = w3_l1.eth.get_transaction_count(l1_account.address)
    gas_price = w3_l1.eth.gas_price
    
    tx = {
        "from": l1_account.address,
        "to": Web3.to_checksum_address(to_address),
        "value": amount_wei,
        "gas": 21000,
        "gasPrice": gas_price,
        "nonce": nonce,
        "chainId": 8453,  # Base mainnet
    }
    
    # Sign and send
    signed_tx = w3_l1.eth.account.sign_transaction(tx, l1_account.key)
    tx_hash = w3_l1.eth.send_raw_transaction(signed_tx.raw_transaction)
    
    print(f"[WITHDRAWAL] L1 tx sent: {tx_hash.hex()}")
    
    # Wait for confirmation
    receipt = w3_l1.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    
    if receipt.status != 1:
        raise Exception(f"L1 transaction failed: {tx_hash.hex()}")
    
    return tx_hash.hex()

def mark_processed_on_l2(withdrawal_id: int, l1_tx_hash: str):
    """Mark withdrawal as processed on L2."""
    # Convert tx hash to bytes32
    l1_tx_bytes = bytes.fromhex(l1_tx_hash.replace("0x", ""))
    
    # Build transaction
    nonce = w3_l2.eth.get_transaction_count(l2_account.address)
    
    tx = withdrawal_contract.functions.markProcessed(
        withdrawal_id,
        l1_tx_bytes
    ).build_transaction({
        "from": l2_account.address,
        "gas": 100000,
        "gasPrice": w3_l2.eth.gas_price,
        "nonce": nonce,
        "chainId": 77777,
    })
    
    # Sign and send
    signed_tx = w3_l2.eth.account.sign_transaction(tx, l2_account.key)
    tx_hash = w3_l2.eth.send_raw_transaction(signed_tx.raw_transaction)
    
    # Wait for confirmation
    receipt = w3_l2.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
    
    if receipt.status != 1:
        raise Exception(f"L2 markProcessed failed: {tx_hash.hex()}")
    
    print(f"[WITHDRAWAL] Marked processed on L2: {tx_hash.hex()}")

def process_withdrawal(withdrawal_id: int):
    """Process a single withdrawal."""
    print(f"\n[WITHDRAWAL] Processing withdrawal #{withdrawal_id}")
    
    # Get withdrawal details
    user, amount, timestamp, processed, l1_tx_hash, can_process = \
        withdrawal_contract.functions.getWithdrawal(withdrawal_id).call()
    
    if processed:
        print(f"[WITHDRAWAL] #{withdrawal_id} already processed")
        return
    
    if not can_process:
        print(f"[WITHDRAWAL] #{withdrawal_id} not ready (challenge period)")
        return
    
    print(f"[WITHDRAWAL] User: {user}")
    print(f"[WITHDRAWAL] Amount: {amount / 1e18:.6f} ETH")
    
    # Check gas price
    if not check_gas_price():
        print(f"[WITHDRAWAL] Skipping - gas too high")
        return
    
    try:
        # Step 1: Send ETH on L1
        if l1_account:
            l1_hash = send_eth_on_l1(user, amount)
            print(f"[WITHDRAWAL] L1 transfer complete: {l1_hash}")
        else:
            # Development mode - simulate
            l1_hash = "0x" + "0" * 64
            print(f"[WITHDRAWAL] DEV MODE - simulated L1 transfer")
        
        # Step 2: Mark as processed on L2
        mark_processed_on_l2(withdrawal_id, l1_hash)
        
        stats["processed"] += 1
        stats["total_eth_sent"] += amount / 1e18
        
        send_alert(f"Processed withdrawal #{withdrawal_id}: {amount/1e18:.4f} ETH to {user[:10]}...", "info")
        
    except Exception as e:
        stats["failed"] += 1
        print(f"[WITHDRAWAL] ERROR processing #{withdrawal_id}: {e}")
        send_alert(f"Withdrawal #{withdrawal_id} failed: {e}", "critical")

# ==================== Main Loop ====================

def main():
    print("\n" + "=" * 60)
    print("THRYX Withdrawal Agent")
    print("=" * 60)
    
    # Check relayer authorization
    try:
        relayer = withdrawal_contract.functions.relayer().call()
        print(f"[WITHDRAWAL] Authorized relayer: {relayer}")
        
        if l2_account.address.lower() != relayer.lower():
            print(f"[WITHDRAWAL] WARNING: Agent address {l2_account.address} != relayer {relayer}")
            print("[WITHDRAWAL] Agent may not be authorized to process withdrawals")
    except Exception as e:
        print(f"[WITHDRAWAL] Could not check relayer: {e}")
    
    # Check challenge period
    try:
        challenge_period = withdrawal_contract.functions.challengePeriod().call()
        print(f"[WITHDRAWAL] Challenge period: {challenge_period} seconds ({challenge_period/3600:.1f} hours)")
    except:
        pass
    
    # Check balances
    l2_balance = get_l2_balance()
    print(f"[WITHDRAWAL] L2 balance: {l2_balance / 1e18:.4f} ETH")
    
    if l1_account:
        l1_balance = get_l1_balance()
        print(f"[WITHDRAWAL] L1 balance: {l1_balance / 1e18:.4f} ETH")
        
        if l1_balance < MIN_BALANCE_ETH * 1e18:
            print(f"[WITHDRAWAL] WARNING: Low L1 balance!")
            send_alert(f"Low L1 balance: {l1_balance/1e18:.4f} ETH", "warning")
    
    print(f"\n[WITHDRAWAL] Starting main loop (polling every {POLL_INTERVAL}s)")
    print("=" * 60)
    
    while True:
        try:
            # Get pending withdrawals
            pending = withdrawal_contract.functions.getPendingWithdrawals().call()
            
            if pending:
                print(f"\n[WITHDRAWAL] {len(pending)} pending withdrawals ready")
                
                for withdrawal_id in pending[:10]:  # Process up to 10 at a time
                    process_withdrawal(withdrawal_id)
            else:
                # Quiet status every 5 minutes
                if int(time.time()) % 300 < POLL_INTERVAL:
                    uptime = time.time() - stats["start_time"]
                    print(f"[WITHDRAWAL] Status: {stats['processed']} processed, "
                          f"{stats['total_eth_sent']:.4f} ETH sent, "
                          f"uptime {uptime/3600:.1f}h")
            
        except Exception as e:
            print(f"[WITHDRAWAL] Error in main loop: {e}")
            time.sleep(5)
        
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
