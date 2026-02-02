"""Verify bridge transaction and balances"""
from web3 import Web3

w3 = Web3(Web3.HTTPProvider('http://localhost:8545'))

# Addresses
ANTHONY_ADDR = '0x718d6142Fb15F95F43FaC6F70498d8Da130240BC'
MINTER_ADDR = '0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266'  # Hardhat account 0

print("=" * 60)
print("THRYX CHAIN VERIFICATION")
print("=" * 60)

# Check connection
print(f"Connected: {w3.is_connected()}")
print(f"Chain ID: {w3.eth.chain_id}")
print(f"Latest Block: {w3.eth.block_number}")

# Check balances
anthony_bal = w3.eth.get_balance(ANTHONY_ADDR)
minter_bal = w3.eth.get_balance(MINTER_ADDR)

print(f"\nAnthony's Address: {ANTHONY_ADDR}")
print(f"Anthony's ETH Balance: {w3.from_wei(anthony_bal, 'ether')} ETH")
print(f"\nMinter's Address: {MINTER_ADDR}")
print(f"Minter's ETH Balance: {w3.from_wei(minter_bal, 'ether')} ETH")

# Check recent transactions TO Anthony
print("\n" + "=" * 60)
print("RECENT BLOCKS (checking for transactions to Anthony)")
print("=" * 60)

latest = w3.eth.block_number
for i in range(max(0, latest - 20), latest + 1):
    try:
        block = w3.eth.get_block(i, full_transactions=True)
        for tx in block.transactions:
            if tx.to and tx.to.lower() == ANTHONY_ADDR.lower():
                print(f"\nBLOCK {i} - TX FOUND TO ANTHONY!")
                print(f"  From: {tx['from']}")
                print(f"  To: {tx.to}")
                print(f"  Value: {w3.from_wei(tx.value, 'ether')} ETH")
                print(f"  Hash: {tx.hash.hex()}")
            if tx['from'].lower() == MINTER_ADDR.lower():
                print(f"\nBLOCK {i} - TX FROM MINTER:")
                print(f"  From: {tx['from']}")
                print(f"  To: {tx.to}")
                print(f"  Value: {w3.from_wei(tx.value, 'ether')} ETH")
                print(f"  Hash: {tx.hash.hex()}")
    except Exception as e:
        print(f"Block {i}: Error - {e}")

# Check transaction count
anthony_nonce = w3.eth.get_transaction_count(ANTHONY_ADDR)
minter_nonce = w3.eth.get_transaction_count(MINTER_ADDR)
print(f"\nAnthony tx count: {anthony_nonce}")
print(f"Minter tx count: {minter_nonce}")
