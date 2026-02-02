from web3 import Web3

w3 = Web3(Web3.HTTPProvider('http://localhost:8545'))

# Both addresses
BRIDGE_WALLET = '0x03F2B0AE7f6badE9944d2CFB8Ad66b62CF6ba1d4'  # Anthony controls this
SENDER_ADDR = '0x718d6142Fb15F95F43FaC6F70498d8Da130240BC'    # Sent ETH from Base

print("THRYX BALANCES:")
print("=" * 50)

bal1 = w3.eth.get_balance(BRIDGE_WALLET)
bal2 = w3.eth.get_balance(SENDER_ADDR)

print(f"Bridge Wallet (you control):")
print(f"  {BRIDGE_WALLET}")
print(f"  Balance: {w3.from_wei(bal1, 'ether')} ETH")
print()
print(f"Sender Address (sent ETH on Base):")
print(f"  {SENDER_ADDR}")
print(f"  Balance: {w3.from_wei(bal2, 'ether')} ETH")
