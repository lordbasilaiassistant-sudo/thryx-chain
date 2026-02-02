"""Fund Anthony's wallet on THRYX"""
from web3 import Web3
from eth_account import Account

w3 = Web3(Web3.HTTPProvider('http://localhost:8545'))

# Hardhat minter (has 10000 ETH)
MINTER_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
minter = Account.from_key(MINTER_KEY)

# Anthony's wallet (he controls this via BASE_PRIVATE_KEY)
ANTHONY_WALLET = "0x03F2B0AE7f6badE9944d2CFB8Ad66b62CF6ba1d4"

# Also fund the sender address for completeness
SENDER_ADDR = "0x718d6142Fb15F95F43FaC6F70498d8Da130240BC"

# Amount to send (1 ETH each)
AMOUNT = w3.to_wei(1, 'ether')

print("Funding wallets on THRYX...")
print("=" * 50)

for addr, name in [(ANTHONY_WALLET, "Bridge Wallet"), (SENDER_ADDR, "Sender Address")]:
    nonce = w3.eth.get_transaction_count(minter.address)
    tx = {
        'from': minter.address,
        'to': addr,
        'value': AMOUNT,
        'nonce': nonce,
        'gas': 21000,
        'chainId': 77777,  # THRYX Mainnet
        'maxFeePerGas': w3.to_wei(2, 'gwei'),
        'maxPriorityFeePerGas': w3.to_wei(1, 'gwei'),
    }
    
    signed = minter.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    
    print(f"Sent 1 ETH to {name}")
    print(f"  Address: {addr}")
    print(f"  TX: {tx_hash.hex()}")
    print()

# Verify balances
print("=" * 50)
print("NEW BALANCES:")
for addr, name in [(ANTHONY_WALLET, "Bridge Wallet"), (SENDER_ADDR, "Sender Address")]:
    bal = w3.eth.get_balance(addr)
    print(f"{name}: {w3.from_wei(bal, 'ether')} ETH")
