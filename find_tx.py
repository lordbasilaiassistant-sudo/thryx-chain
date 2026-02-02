"""Find the actual bridge transaction"""
from web3 import Web3
import sys

w3 = Web3(Web3.HTTPProvider('http://localhost:8545'))

ANTHONY_ADDR = '0x718d6142Fb15F95F43FaC6F70498d8Da130240BC'.lower()

print("Scanning ALL blocks for transactions to Anthony...")
print("=" * 60)
sys.stdout.flush()

latest = w3.eth.block_number
found = []

for i in range(0, latest + 1):
    try:
        block = w3.eth.get_block(i, full_transactions=True)
        for tx in block.transactions:
            to_addr = tx.to.lower() if tx.to else ""
            if to_addr == ANTHONY_ADDR:
                found.append({
                    'block': i,
                    'hash': tx.hash.hex(),
                    'from': tx['from'],
                    'value': float(w3.from_wei(tx.value, 'ether')),
                    'gas': tx.gas
                })
    except:
        pass

print(f"\nFound {len(found)} transaction(s) to Anthony:")
for tx in found:
    print(f"\n[OK] BLOCK {tx['block']}:")
    print(f"   Hash: {tx['hash']}")
    print(f"   From: {tx['from']}")
    print(f"   Value: {tx['value']} ETH")
    print(f"   Gas: {tx['gas']}")

# Also show current balance
bal = w3.eth.get_balance(ANTHONY_ADDR)
print(f"\n{'='*60}")
print(f"Current Balance: {w3.from_wei(bal, 'ether')} ETH")
