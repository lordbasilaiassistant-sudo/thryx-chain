"""Execute withdrawal from THRYX to Base"""
import os
from web3 import Web3
from eth_account import Account

BASE_RPC = "https://mainnet.base.org"
BASE_PRIVATE_KEY = os.getenv("BASE_PRIVATE_KEY", "")

# Recipient - Anthony's sender address on Base
RECIPIENT = "0x718d6142Fb15F95F43FaC6F70498d8Da130240BC"

w3 = Web3(Web3.HTTPProvider(BASE_RPC))

if not BASE_PRIVATE_KEY:
    print("ERROR: BASE_PRIVATE_KEY not set!")
    exit(1)

bridge_account = Account.from_key(BASE_PRIVATE_KEY)
print(f"Bridge wallet: {bridge_account.address}")

# Check balance
balance = w3.eth.get_balance(bridge_account.address)
print(f"Base balance: {w3.from_wei(balance, 'ether')} ETH")

# Calculate max withdrawal (leave 0.0001 for gas)
gas_reserve = w3.to_wei(0.00015, 'ether')  # Extra buffer for gas price fluctuation
if balance <= gas_reserve:
    print("Not enough ETH for withdrawal!")
    exit(1)

withdraw_amount = balance - gas_reserve
print(f"Withdrawing: {w3.from_wei(withdraw_amount, 'ether')} ETH")
print(f"To: {RECIPIENT}")

# Build transaction
nonce = w3.eth.get_transaction_count(bridge_account.address)
gas_price = w3.eth.gas_price

tx = {
    'from': bridge_account.address,
    'to': Web3.to_checksum_address(RECIPIENT),
    'value': withdraw_amount,
    'nonce': nonce,
    'gas': 21000,
    'gasPrice': gas_price,
    'chainId': 8453  # Base mainnet
}

print(f"\nGas price: {w3.from_wei(gas_price, 'gwei')} gwei")
print(f"Estimated gas cost: {w3.from_wei(gas_price * 21000, 'ether')} ETH")

# Sign and send
print("\nSending transaction...")
signed = bridge_account.sign_transaction(tx)
tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)

print()
print("=" * 60)
print("WITHDRAWAL SENT!")
print("=" * 60)
print(f"TX Hash: {tx_hash.hex()}")
print(f"View on Basescan: https://basescan.org/tx/{tx_hash.hex()}")
print()
print(f"Sent {w3.from_wei(withdraw_amount, 'ether')} ETH to {RECIPIENT}")
print("=" * 60)
