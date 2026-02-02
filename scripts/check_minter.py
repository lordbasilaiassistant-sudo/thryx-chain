#!/usr/bin/env python3
"""Check THRYX minter account balance and status"""
from web3 import Web3
from eth_account import Account

# Hardhat account 0 (default minter when THRYX_MINTER_KEY not set)
HARDHAT_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"

w3 = Web3(Web3.HTTPProvider("http://thryx-node:8545"))
account = Account.from_key(HARDHAT_KEY)

print(f"Chain ID: {w3.eth.chain_id}")
print(f"Connected: {w3.is_connected()}")
print(f"Minter address: {account.address}")
print(f"Minter balance: {w3.from_wei(w3.eth.get_balance(account.address), 'ether')} ETH")

# Test signing
try:
    tx = {
        'to': account.address,
        'value': 0,
        'gas': 21000,
        'gasPrice': w3.to_wei(1, 'gwei'),
        'nonce': 0,
        'chainId': 77777
    }
    signed = account.sign_transaction(tx)
    print(f"Signing test: OK (v={signed.v})")
except Exception as e:
    print(f"Signing test: FAILED - {e}")
