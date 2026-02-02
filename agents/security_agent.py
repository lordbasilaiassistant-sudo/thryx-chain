"""
THRYX Security Agent
Real-time fraud detection and anomaly monitoring.

Features:
- Transaction pattern analysis
- Large transfer alerts
- Unusual activity detection
- Emergency pause recommendations
- Bridge security monitoring
"""
import os
import time
import json
from datetime import datetime, timedelta
from web3 import Web3
from collections import defaultdict
from typing import Dict, List, Optional
from dataclasses import dataclass

from base_agent import BaseAgent
from config import CONTRACTS

# Configuration
THRYX_RPC = os.getenv("RPC_URL", "http://localhost:8545")

# Security thresholds
LARGE_TRANSFER_THRESHOLD = 1.0  # ETH
RAPID_TX_THRESHOLD = 10  # Max transactions per minute per address
PRICE_DEVIATION_THRESHOLD = 0.1  # 10% price deviation alert
MIN_BLOCKS_BETWEEN_WITHDRAWALS = 5
SUSPICIOUS_PATTERNS = [
    "rapid_transactions",
    "large_transfer",
    "price_manipulation",
    "unusual_time",
    "new_address_large_tx"
]


@dataclass
class SecurityAlert:
    """Security alert record"""
    severity: str  # low, medium, high, critical
    alert_type: str
    description: str
    address: str
    tx_hash: Optional[str]
    timestamp: float
    recommended_action: str
    auto_mitigated: bool = False


class SecurityAgent(BaseAgent):
    """
    Autonomous security monitoring agent.
    Detects fraud, anomalies, and recommends/takes protective actions.
    """
    
    def __init__(self):
        super().__init__(agent_type="security", loop_interval=5.0)
        self.name = "SECURITY"
        
        # Tracking data
        self.address_activity: Dict[str, List[float]] = defaultdict(list)  # address -> list of tx timestamps
        self.recent_alerts: List[SecurityAlert] = []
        self.known_addresses: set = set()
        self.price_history: List[tuple] = []  # (timestamp, price)
        self.last_block_checked = 0
        
        # Alert handlers
        self.alert_handlers = {
            "high": self._handle_high_alert,
            "critical": self._handle_critical_alert
        }
        
        # Load state
        self._load_state()
    
    def _load_state(self):
        """Load known addresses and historical data"""
        try:
            with open("security_state.json", "r") as f:
                data = json.load(f)
                self.known_addresses = set(data.get("known_addresses", []))
        except:
            pass
    
    def _save_state(self):
        """Save state to file"""
        try:
            with open("security_state.json", "w") as f:
                json.dump({
                    "known_addresses": list(self.known_addresses),
                    "last_updated": datetime.now().isoformat()
                }, f, indent=2)
        except:
            pass
    
    def _create_alert(
        self,
        severity: str,
        alert_type: str,
        description: str,
        address: str,
        tx_hash: str = None,
        recommended_action: str = "monitor"
    ) -> SecurityAlert:
        """Create and log a security alert"""
        alert = SecurityAlert(
            severity=severity,
            alert_type=alert_type,
            description=description,
            address=address,
            tx_hash=tx_hash,
            timestamp=time.time(),
            recommended_action=recommended_action
        )
        
        self.recent_alerts.append(alert)
        
        # Keep only last 100 alerts
        if len(self.recent_alerts) > 100:
            self.recent_alerts = self.recent_alerts[-100:]
        
        # Log alert
        severity_emoji = {
            "low": "ℹ️",
            "medium": "⚠️",
            "high": "🚨",
            "critical": "🔴"
        }
        emoji = severity_emoji.get(severity, "❓")
        
        print(f"[{self.name}] {emoji} {severity.upper()} ALERT: {alert_type}")
        print(f"[{self.name}]   {description}")
        print(f"[{self.name}]   Address: {address[:20]}...")
        print(f"[{self.name}]   Action: {recommended_action}")
        
        # Handle high/critical alerts
        if severity in self.alert_handlers:
            self.alert_handlers[severity](alert)
        
        return alert
    
    def _handle_high_alert(self, alert: SecurityAlert):
        """Handle high severity alerts"""
        # Log to separate file
        self._log_alert_to_file(alert)
    
    def _handle_critical_alert(self, alert: SecurityAlert):
        """Handle critical alerts - may trigger emergency actions"""
        self._log_alert_to_file(alert)
        
        # For critical alerts, we could:
        # 1. Pause contracts (if we have authority)
        # 2. Send notifications
        # 3. Block the address
        
        print(f"[{self.name}] CRITICAL: Consider emergency pause!")
    
    def _log_alert_to_file(self, alert: SecurityAlert):
        """Log alert to security log file"""
        try:
            with open("security_alerts.log", "a") as f:
                f.write(json.dumps({
                    "timestamp": datetime.fromtimestamp(alert.timestamp).isoformat(),
                    "severity": alert.severity,
                    "type": alert.alert_type,
                    "description": alert.description,
                    "address": alert.address,
                    "tx_hash": alert.tx_hash,
                    "action": alert.recommended_action
                }) + "\n")
        except:
            pass
    
    def check_transaction_patterns(self, address: str, tx_hash: str, value_wei: int):
        """Analyze transaction patterns for suspicious activity"""
        address = address.lower()
        now = time.time()
        
        # Track activity
        self.address_activity[address].append(now)
        
        # Clean old entries (keep last 5 minutes)
        cutoff = now - 300
        self.address_activity[address] = [
            t for t in self.address_activity[address] if t > cutoff
        ]
        
        value_eth = float(self.w3.from_wei(value_wei, 'ether'))
        
        # Check 1: Rapid transactions
        recent_count = len(self.address_activity[address])
        if recent_count > RAPID_TX_THRESHOLD:
            self._create_alert(
                severity="medium",
                alert_type="rapid_transactions",
                description=f"{recent_count} transactions in 5 minutes",
                address=address,
                tx_hash=tx_hash,
                recommended_action="rate_limit"
            )
        
        # Check 2: Large transfers
        if value_eth > LARGE_TRANSFER_THRESHOLD:
            severity = "high" if value_eth > LARGE_TRANSFER_THRESHOLD * 5 else "medium"
            self._create_alert(
                severity=severity,
                alert_type="large_transfer",
                description=f"Large transfer: {value_eth:.4f} ETH",
                address=address,
                tx_hash=tx_hash,
                recommended_action="verify_legitimacy"
            )
        
        # Check 3: New address with large transaction
        if address not in self.known_addresses and value_eth > 0.5:
            self._create_alert(
                severity="medium",
                alert_type="new_address_large_tx",
                description=f"New address making {value_eth:.4f} ETH transaction",
                address=address,
                tx_hash=tx_hash,
                recommended_action="monitor_closely"
            )
        
        # Add to known addresses
        self.known_addresses.add(address)
    
    def check_price_manipulation(self, current_price: float):
        """Check for potential price manipulation"""
        now = time.time()
        
        # Add to history
        self.price_history.append((now, current_price))
        
        # Keep only last hour
        cutoff = now - 3600
        self.price_history = [(t, p) for t, p in self.price_history if t > cutoff]
        
        if len(self.price_history) < 5:
            return
        
        # Get average price from last hour
        avg_price = sum(p for _, p in self.price_history) / len(self.price_history)
        
        # Check for sudden deviation
        deviation = abs(current_price - avg_price) / avg_price if avg_price > 0 else 0
        
        if deviation > PRICE_DEVIATION_THRESHOLD:
            severity = "critical" if deviation > 0.25 else "high"
            self._create_alert(
                severity=severity,
                alert_type="price_manipulation",
                description=f"Price deviation: {deviation*100:.1f}% from average",
                address="oracle",
                recommended_action="pause_trading" if severity == "critical" else "investigate"
            )
    
    def scan_recent_blocks(self):
        """Scan recent blocks for suspicious activity"""
        try:
            current_block = self.w3.eth.block_number
            
            if self.last_block_checked == 0:
                self.last_block_checked = current_block - 10
            
            for block_num in range(self.last_block_checked + 1, min(current_block + 1, self.last_block_checked + 20)):
                try:
                    block = self.w3.eth.get_block(block_num, full_transactions=True)
                    
                    for tx in block.transactions:
                        if tx.value > 0:
                            self.check_transaction_patterns(
                                tx["from"],
                                tx.hash.hex(),
                                tx.value
                            )
                except Exception as e:
                    print(f"[{self.name}] Error scanning block {block_num}: {e}")
            
            self.last_block_checked = current_block
            
        except Exception as e:
            print(f"[{self.name}] Block scan error: {e}")
    
    def check_oracle_health(self):
        """Monitor oracle price feeds for issues"""
        try:
            oracle = self.get_contract("AgentOracle")
            if not oracle:
                return
            
            # Get ETH/USD price
            eth_pair = self.w3.keccak(text="ETH/USD")
            
            try:
                price = oracle.functions.getPrice(eth_pair).call()
                price_float = price / 1e8
                
                if price_float > 0:
                    self.check_price_manipulation(price_float)
                    
            except Exception as e:
                # Oracle might be stale
                self._create_alert(
                    severity="medium",
                    alert_type="oracle_issue",
                    description=f"Oracle price fetch failed: {str(e)[:50]}",
                    address="oracle",
                    recommended_action="check_oracle_agents"
                )
        except:
            pass
    
    def check_bridge_health(self):
        """Monitor bridge for suspicious patterns"""
        try:
            # Check bridge state files exist
            deposit_state = "bridge_deposit_state.json"
            withdrawal_state = "withdrawal_state.json"
            
            for state_file in [deposit_state, withdrawal_state]:
                try:
                    with open(state_file, 'r') as f:
                        data = json.load(f)
                        
                    # Check for unusual patterns
                    deposits = data.get("deposits", [])
                    if deposits:
                        recent = [d for d in deposits if time.time() - d.get("timestamp", 0) < 3600]
                        
                        # Check for burst of deposits
                        if len(recent) > 20:
                            self._create_alert(
                                severity="high",
                                alert_type="bridge_flood",
                                description=f"{len(recent)} bridge operations in last hour",
                                address="bridge",
                                recommended_action="rate_limit_bridge"
                            )
                except:
                    pass
        except Exception as e:
            print(f"[{self.name}] Bridge health check error: {e}")
    
    def get_security_summary(self) -> dict:
        """Get current security status summary"""
        now = time.time()
        recent_alerts = [a for a in self.recent_alerts if now - a.timestamp < 3600]
        
        summary = {
            "status": "healthy",
            "alerts_last_hour": len(recent_alerts),
            "critical_alerts": sum(1 for a in recent_alerts if a.severity == "critical"),
            "high_alerts": sum(1 for a in recent_alerts if a.severity == "high"),
            "known_addresses": len(self.known_addresses),
            "monitoring_blocks": self.last_block_checked
        }
        
        if summary["critical_alerts"] > 0:
            summary["status"] = "critical"
        elif summary["high_alerts"] > 2:
            summary["status"] = "warning"
        elif summary["alerts_last_hour"] > 10:
            summary["status"] = "elevated"
        
        return summary
    
    def execute(self):
        """Main security monitoring loop"""
        # Scan blocks for suspicious activity
        self.scan_recent_blocks()
        
        # Check oracle health
        self.check_oracle_health()
        
        # Check bridge health
        self.check_bridge_health()
        
        # Save state periodically
        self._save_state()
        
        # Print status every 10 loops
        if not hasattr(self, '_loop_count'):
            self._loop_count = 0
        self._loop_count += 1
        
        if self._loop_count % 10 == 0:
            summary = self.get_security_summary()
            print(f"[{self.name}] Status: {summary['status'].upper()} | "
                  f"Alerts (1h): {summary['alerts_last_hour']} | "
                  f"Blocks: {summary['monitoring_blocks']}")


if __name__ == "__main__":
    agent = SecurityAgent()
    agent.run_forever()
