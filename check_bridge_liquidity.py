"""Check bridge liquidity - what can be withdrawn"""
from web3 import Web3
import os

BASE_RPC = "https://mainnet.base.org"
BRIDGE_WALLET = "0x03F2B0AE7f6badE9944d2CFB8Ad66b62CF6ba1d4"

w3 = Web3(Web3.HTTPProvider(BASE_RPC))

print("=" * 60)
print("THRYX BRIDGE LIQUIDITY")
print("=" * 60)

# Base balance
base_bal = w3.eth.get_balance(BRIDGE_WALLET)
base_eth = float(w3.from_wei(base_bal, 'ether'))

# Gas reserve
gas_reserve = 0.0001

# Available for withdrawal
available = max(0, base_eth - gas_reserve)

print(f"Bridge Wallet: {BRIDGE_WALLET}")
print(f"Base ETH Balance: {base_eth} ETH")
print(f"Gas Reserve: {gas_reserve} ETH")
print(f"Available to Withdraw: {available} ETH")
print()
print("=" * 60)

if available > 0:
    usd_value = available * 2500  # Approximate ETH price
    print(f"You can withdraw up to ~${usd_value:.2f} worth of real Base ETH!")
else:
    print("No ETH available for withdrawal.")
    print("Deposit more ETH to the bridge wallet on Base first.")
