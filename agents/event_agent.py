"""
THRYX Event Scheduler Agent
Runs scheduled events: daily token launches, weekly airdrops, monthly mega-events
"""
import os
import json
import time
import random
from datetime import datetime, timedelta
from web3 import Web3
from eth_account import Account
from price_feed import format_eth_with_usdc

# Config
RPC_URL = os.getenv("RPC_URL", "http://thryx-node:8545")
STATE_FILE = os.getenv("EVENT_STATE", "/app/data/event_state.json")

# Event agent account
EVENT_KEY = "0xde9be858da4a475276426320d5e9262ecfc3ba460bfac56360bfa6c4c28b4ee0"  # Account 12

FACTORY_ABI = [
    {"name": "createCoin", "type": "function", "stateMutability": "nonpayable",
     "inputs": [{"name": "name", "type": "string"}, {"name": "symbol", "type": "string"}, 
               {"name": "profileUri", "type": "string"}],
     "outputs": [{"name": "", "type": "address"}]},
    {"name": "totalCoins", "type": "function", "stateMutability": "view",
     "inputs": [], "outputs": [{"name": "", "type": "uint256"}]},
]

COIN_ABI = [
    {"name": "buy", "type": "function", "stateMutability": "payable",
     "inputs": [{"name": "minTokensOut", "type": "uint256"}],
     "outputs": [{"name": "", "type": "uint256"}]},
]

# Event themes
DAILY_THEMES = [
    ("Morning Coffee", "COFFEE", "Start your day with gains"),
    ("Night Owl", "OWL", "Late night trading vibes"),
    ("Sunrise Token", "RISE", "New day, new gains"),
    ("Lunch Break", "LUNCH", "Quick trades, quick wins"),
    ("Power Hour", "POWER", "Maximum energy"),
    ("Zero to Hero", "HERO", "From nothing to everything"),
    ("Fast Lane", "FAST", "Speed is key"),
]

WEEKLY_THEMES = [
    ("Weekly Winner", "WINNER", "This week's champion token"),
    ("Sunday Special", "SUNDAY", "Weekend vibes only"),
    ("Monday Motivation", "MONDAY", "Start the week strong"),
    ("Midweek Magic", "MAGIC", "Wednesday wizardry"),
    ("Friday Feels", "FRIDAY", "End the week right"),
]

MONTHLY_THEMES = [
    ("Monthly Mega", "MEGA", "The biggest launch of the month"),
    ("Elite Edition", "ELITE", "For the true believers"),
    ("Genesis Drop", "GEN", "A new era begins"),
    ("Legendary Launch", "LEGEND", "One for the history books"),
]


class EventState:
    def __init__(self, filepath):
        self.filepath = filepath
        self.data = self._load()
    
    def _load(self):
        try:
            if os.path.exists(self.filepath):
                with open(self.filepath, 'r') as f:
                    return json.load(f)
        except:
            pass
        return {
            "last_daily": None,
            "last_weekly": None,
            "last_monthly": None,
            "events_run": 0,
            "coins_launched": [],
            "event_history": [],
            "started_at": datetime.now().isoformat(),
        }
    
    def save(self):
        try:
            os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
            with open(self.filepath, 'w') as f:
                json.dump(self.data, f, indent=2)
        except:
            pass


class EventAgent:
    def __init__(self):
        self.name = "EVENT"
        self.w3 = Web3(Web3.HTTPProvider(RPC_URL))
        self.state = EventState(STATE_FILE)
        self.account = Account.from_key(EVENT_KEY)
        self.deployment = self._load_deployment()
        self.used_symbols = set(self.state.data.get("coins_launched", []))
        
    def _load_deployment(self):
        try:
            with open("/app/deployment.json", "r") as f:
                return json.load(f)
        except:
            return {"contracts": {}}
    
    def log(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] 📅 {self.name}: {msg}")
    
    def should_run_daily(self):
        """Check if daily event should run"""
        last = self.state.data.get("last_daily")
        if not last:
            return True
        last_dt = datetime.fromisoformat(last)
        return datetime.now() - last_dt > timedelta(hours=20)
    
    def should_run_weekly(self):
        """Check if weekly event should run"""
        last = self.state.data.get("last_weekly")
        if not last:
            return True
        last_dt = datetime.fromisoformat(last)
        return datetime.now() - last_dt > timedelta(days=6)
    
    def should_run_monthly(self):
        """Check if monthly event should run"""
        last = self.state.data.get("last_monthly")
        if not last:
            return True
        last_dt = datetime.fromisoformat(last)
        return datetime.now() - last_dt > timedelta(days=25)
    
    def launch_coin(self, name, symbol, bio, liquidity_eth):
        """Launch a new coin with initial liquidity"""
        factory_addr = self.deployment.get("contracts", {}).get("CreatorCoinFactory", "")
        if not factory_addr:
            self.log("No factory address")
            return None
        
        # Make symbol unique
        base_symbol = symbol
        counter = 1
        while symbol in self.used_symbols:
            symbol = f"{base_symbol}{counter}"
            counter += 1
        
        try:
            factory = self.w3.eth.contract(
                address=Web3.to_checksum_address(factory_addr),
                abi=FACTORY_ABI
            )
            
            # Create coin
            nonce = self.w3.eth.get_transaction_count(self.account.address)
            tx = factory.functions.createCoin(name, symbol, bio).build_transaction({
                'from': self.account.address,
                'nonce': nonce,
                'gas': 3000000,
                'chainId': 31337,
                'maxFeePerGas': self.w3.to_wei(2, 'gwei'),
                'maxPriorityFeePerGas': self.w3.to_wei(1, 'gwei'),
            })
            
            signed = self.w3.eth.account.sign_transaction(tx, self.account.key)
            raw = getattr(signed, 'rawTransaction', None) or getattr(signed, 'raw_transaction', None)
            tx_hash = self.w3.eth.send_raw_transaction(raw)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            if receipt.status != 1:
                return None
            
            # Get the new coin address from logs
            total = factory.functions.totalCoins().call()
            coin_addr = factory.functions.allCoins(total - 1).call()
            
            self.log(f"🚀 Launched ${symbol} - {name}")
            self.used_symbols.add(symbol)
            self.state.data["coins_launched"].append(symbol)
            
            # Add initial liquidity
            if liquidity_eth > 0:
                time.sleep(2)
                coin = self.w3.eth.contract(
                    address=Web3.to_checksum_address(coin_addr),
                    abi=COIN_ABI
                )
                
                nonce = self.w3.eth.get_transaction_count(self.account.address)
                buy_tx = coin.functions.buy(0).build_transaction({
                    'from': self.account.address,
                    'nonce': nonce,
                    'value': self.w3.to_wei(liquidity_eth, 'ether'),
                    'gas': 200000,
                    'chainId': 31337,
                    'maxFeePerGas': self.w3.to_wei(2, 'gwei'),
                    'maxPriorityFeePerGas': self.w3.to_wei(1, 'gwei'),
                })
                
                signed = self.w3.eth.account.sign_transaction(buy_tx, self.account.key)
                raw = getattr(signed, 'rawTransaction', None) or getattr(signed, 'raw_transaction', None)
                self.w3.eth.send_raw_transaction(raw)
                
                self.log(f"💰 Added {format_eth_with_usdc(liquidity_eth)} initial liquidity")
            
            return coin_addr
            
        except Exception as e:
            self.log(f"Launch error: {e}")
            return None
    
    def run_daily_event(self):
        """Run daily mini token launch"""
        self.log("🌅 Running DAILY event...")
        
        theme = random.choice(DAILY_THEMES)
        name, symbol, bio = theme
        
        # Add date to make unique
        date_suffix = datetime.now().strftime("%m%d")
        name = f"{name} {date_suffix}"
        
        coin_addr = self.launch_coin(name, symbol, bio, 0.05)
        
        if coin_addr:
            self.state.data["last_daily"] = datetime.now().isoformat()
            self.state.data["events_run"] += 1
            self.state.data["event_history"].append({
                "type": "daily",
                "coin": symbol,
                "address": coin_addr,
                "timestamp": datetime.now().isoformat()
            })
            self.state.save()
    
    def run_weekly_event(self):
        """Run weekly token launch with airdrop"""
        self.log("📅 Running WEEKLY event...")
        
        theme = random.choice(WEEKLY_THEMES)
        name, symbol, bio = theme
        
        # Add week number
        week = datetime.now().isocalendar()[1]
        name = f"{name} W{week}"
        
        coin_addr = self.launch_coin(name, symbol, bio, 0.2)
        
        if coin_addr:
            self.state.data["last_weekly"] = datetime.now().isoformat()
            self.state.data["events_run"] += 1
            self.state.data["event_history"].append({
                "type": "weekly",
                "coin": symbol,
                "address": coin_addr,
                "timestamp": datetime.now().isoformat()
            })
            self.state.save()
    
    def run_monthly_event(self):
        """Run monthly mega launch"""
        self.log("🎉 Running MONTHLY MEGA event...")
        
        theme = random.choice(MONTHLY_THEMES)
        name, symbol, bio = theme
        
        # Add month
        month = datetime.now().strftime("%b")
        name = f"{name} {month}"
        
        coin_addr = self.launch_coin(name, symbol, bio, 0.5)
        
        if coin_addr:
            self.state.data["last_monthly"] = datetime.now().isoformat()
            self.state.data["events_run"] += 1
            self.state.data["event_history"].append({
                "type": "monthly",
                "coin": symbol,
                "address": coin_addr,
                "timestamp": datetime.now().isoformat()
            })
            self.state.save()
    
    def run_cycle(self):
        """Check and run scheduled events"""
        # Check monthly first (most important)
        if self.should_run_monthly():
            self.run_monthly_event()
            time.sleep(5)
        
        # Then weekly
        if self.should_run_weekly():
            self.run_weekly_event()
            time.sleep(5)
        
        # Then daily
        if self.should_run_daily():
            self.run_daily_event()
    
    def run(self):
        """Main loop"""
        self.log("🚀 Event Scheduler Agent started!")
        self.log(f"Event wallet: {self.account.address}")
        
        while True:
            try:
                if not self.w3.is_connected():
                    self.log("Waiting for node...")
                    time.sleep(5)
                    continue
                
                self.run_cycle()
                
                # Check every 5 minutes
                time.sleep(300)
                
            except KeyboardInterrupt:
                self.log("Shutting down...")
                break
            except Exception as e:
                self.log(f"Error: {e}")
                time.sleep(30)


if __name__ == "__main__":
    agent = EventAgent()
    agent.run()
