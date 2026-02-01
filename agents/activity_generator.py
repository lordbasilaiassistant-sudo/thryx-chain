"""
THRYX Activity Generator - Creates organic on-chain activity
Run this to make the chain look alive with real transactions
"""
import os
import time
import random
from web3 import Web3
from eth_account import Account

RPC_URL = os.getenv("RPC_URL", "http://localhost:8545")

# Hardhat default accounts with 10000 ETH each
ACCOUNTS = [
    ("Deployer", "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"),
    ("Treasury", "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d"),
    ("Oracle", "0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a"),
    ("Arbitrage", "0x7c852118294e51e653712a81e05800f419141751be58f605c371e15141b007a6"),
    ("Liquidity", "0x47e179ec197488593b187f80a00eb0da91f1b9d0b13f8733639f19c30a34926a"),
    ("Governance", "0x8b3a350cf5c34c9194ca85829a2df0ec3153be0318b5e2d3348e872092edffba"),
    ("Monitor", "0x92db14e403b83dfe3df233f83dfa3a0d7096f21ca9b0d6d6b8d88b2b4ec1564e"),
    ("Security", "0x4bbbf85ce3377467afe5d46f804f221813b2bb87f24d81f60f1fcdbf7cbf4356"),
    ("Intent", "0xdbda1821b80551c9d65939329250298aa3472ba22feea921c0cf5d620ea67b97"),
    ("Evolution", "0x2a871d0798f97d79848a013d4936a73bf4cc922c825d33c1cf7073dff6d409c6"),
]

# Contract addresses (update these after deploy)
FACTORY_ADDRESS = os.getenv("FACTORY_ADDRESS", "0x2E2Ed0Cfd3AD2f1d34481277b3204d807Ca2F8c2")

FACTORY_ABI = [
    {"name": "createCoin", "type": "function", "stateMutability": "nonpayable",
     "inputs": [{"name": "name", "type": "string"}, {"name": "symbol", "type": "string"}, 
               {"name": "profileUri", "type": "string"}],
     "outputs": [{"name": "", "type": "address"}]},
    {"name": "totalCoins", "type": "function", "stateMutability": "view",
     "inputs": [], "outputs": [{"name": "", "type": "uint256"}]},
    {"name": "allCoins", "type": "function", "stateMutability": "view",
     "inputs": [{"name": "index", "type": "uint256"}],
     "outputs": [{"name": "", "type": "address"}]},
]

COIN_ABI = [
    {"name": "buy", "type": "function", "stateMutability": "payable",
     "inputs": [{"name": "minTokensOut", "type": "uint256"}],
     "outputs": [{"name": "", "type": "uint256"}]},
    {"name": "sell", "type": "function", "stateMutability": "nonpayable",
     "inputs": [{"name": "tokenAmount", "type": "uint256"}, {"name": "minEthOut", "type": "uint256"}],
     "outputs": [{"name": "", "type": "uint256"}]},
    {"name": "symbol", "type": "function", "stateMutability": "view",
     "inputs": [], "outputs": [{"name": "", "type": "string"}]},
    {"name": "balanceOf", "type": "function", "stateMutability": "view",
     "inputs": [{"name": "account", "type": "address"}],
     "outputs": [{"name": "", "type": "uint256"}]},
    {"name": "totalTrades", "type": "function", "stateMutability": "view",
     "inputs": [], "outputs": [{"name": "", "type": "uint256"}]},
    {"name": "getCurrentPrice", "type": "function", "stateMutability": "view",
     "inputs": [], "outputs": [{"name": "", "type": "uint256"}]},
]

# Fun coin ideas
COIN_IDEAS = [
    ("THRYX Genesis", "GENESIS", "The first official THRYX ecosystem token"),
    ("AI Collective", "AICOL", "Representing the AI agent collective on THRYX"),
    ("THRYX OG", "OG", "For the original THRYX supporters"),
    ("Moon Mission", "MOON", "To the moon and beyond"),
    ("Diamond Hands", "DIAMOND", "For those who never sell"),
    ("THRYX Meme", "MEME", "The official meme token of THRYX"),
    ("Builder Token", "BUILD", "For the builders of THRYX ecosystem"),
    ("THRYX Culture", "CULTURE", "Celebrating THRYX culture"),
    ("AI Dreams", "DREAM", "Where AI dreams become reality"),
    ("THRYX Fire", "FIRE", "The hottest token on THRYX"),
]


def create_coin(w3, account, name, symbol, profile):
    """Create a new coin"""
    try:
        factory = w3.eth.contract(
            address=Web3.to_checksum_address(FACTORY_ADDRESS),
            abi=FACTORY_ABI
        )
        
        nonce = w3.eth.get_transaction_count(account.address)
        tx = factory.functions.createCoin(name, symbol, profile).build_transaction({
            'from': account.address,
            'nonce': nonce,
            'gas': 3000000,
            'chainId': 31337,
            'maxFeePerGas': w3.to_wei(2, 'gwei'),
            'maxPriorityFeePerGas': w3.to_wei(1, 'gwei'),
        })
        
        signed = w3.eth.account.sign_transaction(tx, account.key)
        raw_tx = getattr(signed, 'rawTransaction', None) or getattr(signed, 'raw_transaction', None)
        tx_hash = w3.eth.send_raw_transaction(raw_tx)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        
        if receipt.status == 1:
            print(f"✅ Created ${symbol} by {account.address[:10]}...")
            return True
        return False
    except Exception as e:
        print(f"❌ Failed to create {symbol}: {e}")
        return False


def buy_coin(w3, account, coin_address, eth_amount):
    """Buy a coin"""
    try:
        coin = w3.eth.contract(
            address=Web3.to_checksum_address(coin_address),
            abi=COIN_ABI
        )
        
        symbol = coin.functions.symbol().call()
        
        nonce = w3.eth.get_transaction_count(account.address)
        tx = coin.functions.buy(0).build_transaction({
            'from': account.address,
            'nonce': nonce,
            'value': w3.to_wei(eth_amount, 'ether'),
            'gas': 200000,
            'chainId': 31337,
            'maxFeePerGas': w3.to_wei(2, 'gwei'),
            'maxPriorityFeePerGas': w3.to_wei(1, 'gwei'),
        })
        
        signed = w3.eth.account.sign_transaction(tx, account.key)
        raw_tx = getattr(signed, 'rawTransaction', None) or getattr(signed, 'raw_transaction', None)
        tx_hash = w3.eth.send_raw_transaction(raw_tx)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        
        if receipt.status == 1:
            print(f"💰 {account.address[:10]}... bought {eth_amount} ETH of ${symbol}")
            return True
        return False
    except Exception as e:
        print(f"❌ Failed to buy: {e}")
        return False


def transfer_eth(w3, from_account, to_address, amount):
    """Simple ETH transfer"""
    try:
        nonce = w3.eth.get_transaction_count(from_account.address)
        tx = {
            'from': from_account.address,
            'to': Web3.to_checksum_address(to_address),
            'value': w3.to_wei(amount, 'ether'),
            'nonce': nonce,
            'gas': 21000,
            'chainId': 31337,
            'maxFeePerGas': w3.to_wei(2, 'gwei'),
            'maxPriorityFeePerGas': w3.to_wei(1, 'gwei'),
        }
        
        signed = w3.eth.account.sign_transaction(tx, from_account.key)
        raw_tx = getattr(signed, 'rawTransaction', None) or getattr(signed, 'raw_transaction', None)
        tx_hash = w3.eth.send_raw_transaction(raw_tx)
        w3.eth.wait_for_transaction_receipt(tx_hash)
        print(f"💸 Transferred {amount} ETH: {from_account.address[:10]}... → {to_address[:10]}...")
        return True
    except Exception as e:
        print(f"❌ Transfer failed: {e}")
        return False


def main():
    print("=" * 60)
    print("🚀 THRYX ACTIVITY GENERATOR")
    print("=" * 60)
    print("Generating organic on-chain activity...")
    print()
    
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    print(f"Connected to THRYX: {w3.is_connected()}")
    print(f"Current block: {w3.eth.block_number}")
    print()
    
    # Load accounts
    accounts = [Account.from_key(pk) for _, pk in ACCOUNTS]
    
    # Phase 1: Create coins
    print("=" * 60)
    print("📦 PHASE 1: Creating Creator Coins")
    print("=" * 60)
    
    created_coins = 0
    for i, (name, symbol, profile) in enumerate(COIN_IDEAS[:5]):  # Create 5 coins
        creator = accounts[i % len(accounts)]
        if create_coin(w3, creator, name, symbol, profile):
            created_coins += 1
        time.sleep(1)
    
    print(f"\n✅ Created {created_coins} coins\n")
    
    # Get coin addresses
    factory = w3.eth.contract(
        address=Web3.to_checksum_address(FACTORY_ADDRESS),
        abi=FACTORY_ABI
    )
    total = factory.functions.totalCoins().call()
    coin_addresses = []
    for i in range(total):
        addr = factory.functions.allCoins(i).call()
        coin_addresses.append(addr)
    
    # Phase 2: Buy coins (generate trading activity)
    print("=" * 60)
    print("💰 PHASE 2: Trading Activity")
    print("=" * 60)
    
    trades = 0
    for _ in range(20):  # 20 random trades
        buyer = random.choice(accounts)
        if coin_addresses:
            coin = random.choice(coin_addresses)
            amount = random.uniform(0.01, 0.5)
            if buy_coin(w3, buyer, coin, round(amount, 4)):
                trades += 1
        time.sleep(0.5)
    
    print(f"\n✅ Executed {trades} trades\n")
    
    # Phase 3: ETH transfers (general activity)
    print("=" * 60)
    print("💸 PHASE 3: ETH Transfers")
    print("=" * 60)
    
    transfers = 0
    for _ in range(10):  # 10 transfers
        sender = random.choice(accounts)
        receiver = random.choice(accounts)
        if sender != receiver:
            amount = random.uniform(0.1, 1.0)
            if transfer_eth(w3, sender, receiver.address, round(amount, 4)):
                transfers += 1
        time.sleep(0.5)
    
    print(f"\n✅ Executed {transfers} transfers\n")
    
    # Summary
    print("=" * 60)
    print("📊 ACTIVITY SUMMARY")
    print("=" * 60)
    print(f"Coins created: {created_coins}")
    print(f"Trades executed: {trades}")
    print(f"ETH transfers: {transfers}")
    print(f"Total transactions: {created_coins + trades + transfers}")
    print(f"Current block: {w3.eth.block_number}")
    print()
    print("🔥 Chain is now buzzing with activity!")
    print("Check the explorer: https://crispy-goggles-v6jg77gvqwqv3pxpg-5100.app.github.dev")


if __name__ == "__main__":
    main()
