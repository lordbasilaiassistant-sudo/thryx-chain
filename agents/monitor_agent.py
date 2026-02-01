"""
THRYX Monitor Agent - ENHANCED
Watches chain health, agent activity, and system metrics.
Now with AUTO-REMEDIATION capabilities.

Features:
- Chain health monitoring
- Agent activity tracking
- AMM liquidity monitoring
- Oracle freshness checking
- AUTO-REMEDIATION for common issues
- Persistent alert history
"""
import os
import time
import json
import subprocess
from datetime import datetime
from base_agent import BaseAgent
from config import CONTRACTS, AGENT_REGISTRY_ABI, SIMPLE_AMM_ABI, AGENT_ORACLE_ABI
from web3 import Web3


# Remediation configuration
ENABLE_AUTO_REMEDIATION = os.getenv("ENABLE_AUTO_REMEDIATION", "true").lower() == "true"
ALERT_LOG_FILE = "monitor_alerts.json"


class AutoRemediation:
    """
    Auto-remediation actions for common issues.
    """
    
    @staticmethod
    def restart_agent(agent_name: str) -> dict:
        """Restart a Docker agent container"""
        try:
            container_name = f"thryx-{agent_name}"
            result = subprocess.run(
                ["docker", "restart", container_name],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return {"success": True, "action": f"Restarted {container_name}"}
            else:
                return {"success": False, "error": result.stderr}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def add_liquidity_alert() -> dict:
        """Log low liquidity alert for manual action"""
        # In production, this could trigger an automated liquidity provision
        return {"success": True, "action": "Low liquidity alert logged - manual action required"}
    
    @staticmethod
    def trigger_oracle_update() -> dict:
        """Attempt to restart oracle agent to refresh prices"""
        return AutoRemediation.restart_agent("oracle")
    
    @staticmethod
    def scale_up_agents() -> dict:
        """Log request to scale up agents"""
        return {"success": True, "action": "Scale-up request logged"}


class MonitorAgent(BaseAgent):
    """
    Enhanced monitoring agent with auto-remediation.
    """
    
    def __init__(self):
        super().__init__(agent_type="monitor", loop_interval=5.0)
        
        self.last_block = 0
        self.blocks_seen = 0
        self.tx_count_total = 0
        self.last_tx_count = 0
        
        self.registry_contract = None
        self.amm_contract = None
        self.oracle_contract = None
        
        # Alert thresholds
        self.min_block_rate = 0.4
        self.max_price_age = 120
        self.min_liquidity_usdc = 1000
        self.min_active_agents = 3
        
        # Track issues for remediation
        self.issue_counts = {}  # issue_type -> count
        self.last_remediation = {}  # issue_type -> timestamp
        self.remediation_cooldown = 300  # 5 minutes between remediations
        
        # Alert history
        self.alerts_history = []
        self._load_alert_history()
        
        # Remediation handlers
        self.remediation_actions = {
            "oracle_stale": AutoRemediation.trigger_oracle_update,
            "low_liquidity": AutoRemediation.add_liquidity_alert,
            "few_agents": AutoRemediation.scale_up_agents,
            "agent_down": lambda agent=None: AutoRemediation.restart_agent(agent or "oracle")
        }
    
    def _load_alert_history(self):
        """Load alert history from file"""
        try:
            with open(ALERT_LOG_FILE, 'r') as f:
                self.alerts_history = json.load(f)
        except:
            self.alerts_history = []
    
    def _save_alert_history(self):
        """Save alert history to file"""
        try:
            # Keep last 1000 alerts
            if len(self.alerts_history) > 1000:
                self.alerts_history = self.alerts_history[-1000:]
            
            with open(ALERT_LOG_FILE, 'w') as f:
                json.dump(self.alerts_history, f, indent=2, default=str)
        except:
            pass
    
    def _log_alert(self, severity: str, alert_type: str, message: str, remediation: dict = None):
        """Log an alert with optional remediation result"""
        alert = {
            "timestamp": datetime.now().isoformat(),
            "severity": severity,
            "type": alert_type,
            "message": message,
            "remediation": remediation
        }
        
        self.alerts_history.append(alert)
        self._save_alert_history()
        
        severity_prefix = {
            "info": "INFO",
            "warning": "WARN",
            "critical": "CRIT",
            "error": "ERR"
        }
        
        print(f"[MONITOR] [{severity_prefix.get(severity, 'INFO')}] {message}")
        
        if remediation:
            if remediation.get("success"):
                print(f"[MONITOR] AUTO-FIX: {remediation.get('action', 'Applied')}")
            else:
                print(f"[MONITOR] FIX-FAILED: {remediation.get('error', 'Unknown')}")
    
    def _should_remediate(self, issue_type: str) -> bool:
        """Check if we should attempt remediation for this issue"""
        if not ENABLE_AUTO_REMEDIATION:
            return False
        
        # Track issue occurrences
        self.issue_counts[issue_type] = self.issue_counts.get(issue_type, 0) + 1
        
        # Only remediate if issue persists (seen 3+ times)
        if self.issue_counts[issue_type] < 3:
            return False
        
        # Check cooldown
        last_time = self.last_remediation.get(issue_type, 0)
        if time.time() - last_time < self.remediation_cooldown:
            return False
        
        return True
    
    def _attempt_remediation(self, issue_type: str, **kwargs) -> dict:
        """Attempt auto-remediation for an issue"""
        if issue_type not in self.remediation_actions:
            return None
        
        self.last_remediation[issue_type] = time.time()
        self.issue_counts[issue_type] = 0  # Reset count after remediation
        
        try:
            action = self.remediation_actions[issue_type]
            if kwargs:
                result = action(**kwargs)
            else:
                result = action()
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _init_contracts(self):
        """Initialize contract instances"""
        if self.registry_contract is None:
            self.registry_contract = self.get_contract("AgentRegistry", AGENT_REGISTRY_ABI)
            self.amm_contract = self.get_contract("SimpleAMM", SIMPLE_AMM_ABI)
            self.oracle_contract = self.get_contract("AgentOracle", AGENT_ORACLE_ABI)
    
    def _check_chain_health(self) -> dict:
        """Check blockchain health metrics"""
        try:
            current_block = self.w3.eth.block_number
            
            if self.last_block == 0:
                self.last_block = current_block
                return {"status": "initializing", "block": current_block}
            
            blocks_produced = current_block - self.last_block
            self.blocks_seen += blocks_produced
            self.last_block = current_block
            
            block = self.w3.eth.get_block(current_block)
            tx_count = len(block.transactions)
            
            return {
                "status": "healthy",
                "block": current_block,
                "blocks_since_last": blocks_produced,
                "tx_in_block": tx_count,
                "gas_used": block.gasUsed,
                "timestamp": block.timestamp
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def _check_agents(self) -> dict:
        """Check agent registry status"""
        try:
            agent_count = self.call_contract(self.registry_contract, "getAgentCount")
            active_agents = self.call_contract(self.registry_contract, "getActiveAgents")
            
            return {
                "total_registered": agent_count,
                "active_count": len(active_agents) if active_agents else 0,
                "active_addresses": active_agents[:5] if active_agents else []
            }
        except Exception as e:
            return {"error": str(e)}
    
    def _check_amm(self) -> dict:
        """Check AMM health"""
        try:
            reserve_a = self.call_contract(self.amm_contract, "reserveA")
            reserve_b = self.call_contract(self.amm_contract, "reserveB")
            price = self.call_contract(self.amm_contract, "getPrice")
            
            return {
                "reserve_usdc": reserve_a / 10**6 if reserve_a else 0,
                "reserve_weth": reserve_b / 10**18 if reserve_b else 0,
                "price_weth_usdc": price / 10**18 if price else 0,
                "tvl_usdc": (reserve_a / 10**6 * 2) if reserve_a else 0
            }
        except Exception as e:
            return {"error": str(e)}
    
    def _check_oracle(self) -> dict:
        """Check oracle health"""
        try:
            eth_pair = Web3.keccak(text="ETH/USD")
            result = self.call_contract(self.oracle_contract, "getPrice", eth_pair)
            
            if result:
                price, timestamp, is_stale = result
                age = int(time.time()) - timestamp
                
                return {
                    "eth_usd": price / 10**8 if price else 0,
                    "last_update_age_sec": age,
                    "is_stale": is_stale
                }
            return {"error": "No price data"}
        except Exception as e:
            return {"error": str(e)}
    
    def _check_docker_containers(self) -> dict:
        """Check if Docker containers are running"""
        try:
            result = subprocess.run(
                ["docker", "ps", "--format", "{{.Names}}:{{.Status}}"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            containers = {}
            for line in result.stdout.strip().split("\n"):
                if ":" in line:
                    name, status = line.split(":", 1)
                    containers[name] = "healthy" if "Up" in status else "down"
            
            return containers
        except:
            return {}
    
    def _generate_alerts_with_remediation(self, chain: dict, agents: dict, amm: dict, oracle: dict) -> list:
        """Generate alerts and attempt auto-remediation"""
        alerts = []
        
        # Chain connection error
        if chain.get("status") == "error":
            self._log_alert("critical", "chain_error", 
                          f"Chain connection error: {chain.get('error')}")
            alerts.append("CRITICAL: Chain error")
        
        # Few active agents
        active_count = agents.get("active_count", 0)
        if active_count < self.min_active_agents:
            should_fix = self._should_remediate("few_agents")
            remediation = None
            
            if should_fix:
                remediation = self._attempt_remediation("few_agents")
            
            self._log_alert("warning", "few_agents",
                          f"Only {active_count} active agents (min: {self.min_active_agents})",
                          remediation)
            alerts.append(f"WARNING: Low agent count")
        else:
            # Reset issue count if resolved
            self.issue_counts["few_agents"] = 0
        
        # Low AMM liquidity
        liquidity = amm.get("reserve_usdc", 0)
        if liquidity < self.min_liquidity_usdc:
            should_fix = self._should_remediate("low_liquidity")
            remediation = None
            
            if should_fix:
                remediation = self._attempt_remediation("low_liquidity")
            
            self._log_alert("warning", "low_liquidity",
                          f"Low AMM liquidity: ${liquidity:,.0f} USDC",
                          remediation)
            alerts.append("WARNING: Low liquidity")
        else:
            self.issue_counts["low_liquidity"] = 0
        
        # Stale oracle
        if oracle.get("is_stale", True) or oracle.get("last_update_age_sec", 999) > self.max_price_age:
            should_fix = self._should_remediate("oracle_stale")
            remediation = None
            
            if should_fix:
                remediation = self._attempt_remediation("oracle_stale")
            
            age = oracle.get("last_update_age_sec", 0)
            self._log_alert("warning", "oracle_stale",
                          f"Oracle data stale ({age}s old)",
                          remediation)
            alerts.append("WARNING: Stale oracle")
        else:
            self.issue_counts["oracle_stale"] = 0
        
        # Check Docker containers
        containers = self._check_docker_containers()
        for name, status in containers.items():
            if status == "down" and "thryx" in name.lower():
                agent_name = name.replace("thryx-", "")
                should_fix = self._should_remediate(f"agent_down_{agent_name}")
                remediation = None
                
                if should_fix:
                    remediation = self._attempt_remediation("agent_down", agent=agent_name)
                
                self._log_alert("critical", "agent_down",
                              f"Container {name} is DOWN",
                              remediation)
                alerts.append(f"CRITICAL: {name} down")
        
        return alerts
    
    def execute(self):
        """Run health check with auto-remediation"""
        self._init_contracts()
        
        # Gather metrics
        chain = self._check_chain_health()
        agents = self._check_agents()
        amm = self._check_amm()
        oracle = self._check_oracle()
        
        # Generate alerts and attempt remediation
        alerts = self._generate_alerts_with_remediation(chain, agents, amm, oracle)
        
        # Log summary periodically
        if not hasattr(self, '_loop_count'):
            self._loop_count = 0
        self._loop_count += 1
        
        if self._loop_count % 12 == 0:  # Every minute
            print(f"[MONITOR] " + "=" * 50)
            print(f"[MONITOR] Block #{chain.get('block', 0)} | TX: {chain.get('tx_in_block', 0)}")
            print(f"[MONITOR] Agents: {agents.get('active_count', 0)}/{agents.get('total_registered', 0)} active")
            print(f"[MONITOR] AMM: ${amm.get('reserve_usdc', 0):,.0f} USDC | TVL: ${amm.get('tvl_usdc', 0):,.0f}")
            print(f"[MONITOR] Oracle: ETH ${oracle.get('eth_usd', 0):,.2f} | Age: {oracle.get('last_update_age_sec', 0)}s")
            
            if alerts:
                print(f"[MONITOR] ALERTS: {len(alerts)} active")
            else:
                print(f"[MONITOR] STATUS: All systems operational")
            
            print(f"[MONITOR] Auto-remediation: {'ENABLED' if ENABLE_AUTO_REMEDIATION else 'DISABLED'}")
            print(f"[MONITOR] " + "=" * 50)
    
    def get_health_summary(self) -> dict:
        """Get current health summary"""
        self._init_contracts()
        
        return {
            "chain": self._check_chain_health(),
            "agents": self._check_agents(),
            "amm": self._check_amm(),
            "oracle": self._check_oracle(),
            "containers": self._check_docker_containers(),
            "active_issues": dict(self.issue_counts),
            "recent_alerts": self.alerts_history[-10:] if self.alerts_history else []
        }


if __name__ == "__main__":
    agent = MonitorAgent()
    agent.run_forever()
