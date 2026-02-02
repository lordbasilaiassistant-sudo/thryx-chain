"""
THRYX Agent Memory System
Enables agents to learn from outcomes and adapt their behavior.

Features:
- Action tracking with outcomes
- Performance metrics calculation
- Parameter adjustment recommendations
- Persistent storage
"""
import os
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from collections import defaultdict
import math


MEMORY_FILE = os.getenv("AGENT_MEMORY_FILE", "agent_memory.json")


@dataclass
class ActionRecord:
    """Record of an agent action and its outcome"""
    agent_name: str
    action_type: str
    parameters: Dict[str, Any]
    timestamp: float
    outcome: str  # success, failure, partial
    result_value: float  # Numeric result (profit, price accuracy, etc.)
    gas_used: int
    execution_time_ms: int
    context: Dict[str, Any]  # Market conditions, etc.


class AgentMemory:
    """
    Learning memory system for THRYX agents.
    Tracks actions, outcomes, and provides adaptive recommendations.
    """
    
    def __init__(self, agent_name: str, memory_file: str = None):
        self.agent_name = agent_name
        self.memory_file = memory_file or MEMORY_FILE
        self.memory = self._load_memory()
        
        # Initialize agent section if needed
        if agent_name not in self.memory["agents"]:
            self.memory["agents"][agent_name] = {
                "actions": [],
                "parameters": {},
                "metrics": {
                    "total_actions": 0,
                    "successful_actions": 0,
                    "failed_actions": 0,
                    "total_profit": 0.0,
                    "total_gas_spent": 0,
                    "avg_execution_time": 0
                },
                "learned_parameters": {},
                "created_at": datetime.now().isoformat()
            }
    
    def _load_memory(self) -> dict:
        """Load memory from file"""
        try:
            with open(self.memory_file, 'r') as f:
                return json.load(f)
        except:
            return {
                "version": "1.0",
                "agents": {},
                "global_metrics": {
                    "total_transactions": 0,
                    "system_uptime_hours": 0,
                    "last_update": None
                }
            }
    
    def _save_memory(self):
        """Save memory to file"""
        try:
            self.memory["global_metrics"]["last_update"] = datetime.now().isoformat()
            with open(self.memory_file, 'w') as f:
                json.dump(self.memory, f, indent=2, default=str)
        except Exception as e:
            print(f"[{self.agent_name}] Warning: Could not save memory: {e}")
    
    def record_action(self, action: ActionRecord):
        """Record an action and its outcome"""
        agent_data = self.memory["agents"][self.agent_name]
        
        # Add to actions list (keep last 1000)
        action_dict = asdict(action)
        agent_data["actions"].append(action_dict)
        if len(agent_data["actions"]) > 1000:
            agent_data["actions"] = agent_data["actions"][-1000:]
        
        # Update metrics
        metrics = agent_data["metrics"]
        metrics["total_actions"] += 1
        
        if action.outcome == "success":
            metrics["successful_actions"] += 1
        elif action.outcome == "failure":
            metrics["failed_actions"] += 1
        
        metrics["total_profit"] += action.result_value
        metrics["total_gas_spent"] += action.gas_used
        
        # Update average execution time
        n = metrics["total_actions"]
        old_avg = metrics["avg_execution_time"]
        metrics["avg_execution_time"] = old_avg + (action.execution_time_ms - old_avg) / n
        
        # Update global metrics
        self.memory["global_metrics"]["total_transactions"] += 1
        
        self._save_memory()
        
        # Trigger learning
        self._learn_from_action(action)
    
    def _learn_from_action(self, action: ActionRecord):
        """Analyze action and adjust learned parameters"""
        agent_data = self.memory["agents"][self.agent_name]
        learned = agent_data["learned_parameters"]
        
        # Get recent actions for this type
        recent = self.get_recent_actions(action.action_type, hours=24)
        if len(recent) < 5:
            return  # Not enough data
        
        # Calculate success rate
        success_count = sum(1 for a in recent if a["outcome"] == "success")
        success_rate = success_count / len(recent)
        
        # Calculate average profit
        avg_profit = sum(a["result_value"] for a in recent) / len(recent)
        
        # Store learned insights
        learned[action.action_type] = {
            "success_rate": success_rate,
            "avg_profit": avg_profit,
            "sample_size": len(recent),
            "last_updated": datetime.now().isoformat(),
            "recommended_adjustments": self._calculate_adjustments(action.action_type, recent)
        }
        
        self._save_memory()
    
    def _calculate_adjustments(self, action_type: str, recent_actions: List[dict]) -> dict:
        """Calculate recommended parameter adjustments based on outcomes"""
        adjustments = {}
        
        # Analyze which parameters correlate with success
        successful = [a for a in recent_actions if a["outcome"] == "success"]
        failed = [a for a in recent_actions if a["outcome"] == "failure"]
        
        if not successful or not failed:
            return adjustments
        
        # Get all parameter keys
        all_params = set()
        for a in recent_actions:
            all_params.update(a.get("parameters", {}).keys())
        
        for param in all_params:
            # Get average values for successful vs failed
            success_vals = [a["parameters"].get(param) for a in successful if param in a.get("parameters", {})]
            fail_vals = [a["parameters"].get(param) for a in failed if param in a.get("parameters", {})]
            
            # Only analyze numeric parameters
            try:
                success_vals = [float(v) for v in success_vals if v is not None]
                fail_vals = [float(v) for v in fail_vals if v is not None]
                
                if success_vals and fail_vals:
                    success_avg = sum(success_vals) / len(success_vals)
                    fail_avg = sum(fail_vals) / len(fail_vals)
                    
                    # Recommend moving toward successful values
                    if success_avg != fail_avg:
                        direction = "increase" if success_avg > fail_avg else "decrease"
                        magnitude = abs(success_avg - fail_avg) / max(abs(success_avg), abs(fail_avg), 0.0001)
                        
                        adjustments[param] = {
                            "direction": direction,
                            "magnitude": magnitude,
                            "target_value": success_avg,
                            "confidence": len(recent_actions) / 100  # More data = more confidence
                        }
            except (ValueError, TypeError):
                continue  # Skip non-numeric parameters
        
        return adjustments
    
    def get_recent_actions(self, action_type: str = None, hours: int = 24) -> List[dict]:
        """Get recent actions, optionally filtered by type"""
        agent_data = self.memory["agents"][self.agent_name]
        cutoff = time.time() - (hours * 3600)
        
        actions = [
            a for a in agent_data["actions"]
            if a["timestamp"] > cutoff
        ]
        
        if action_type:
            actions = [a for a in actions if a["action_type"] == action_type]
        
        return actions
    
    def get_success_rate(self, action_type: str = None, hours: int = 24) -> float:
        """Get success rate for recent actions"""
        recent = self.get_recent_actions(action_type, hours)
        if not recent:
            return 0.0
        
        success_count = sum(1 for a in recent if a["outcome"] == "success")
        return success_count / len(recent)
    
    def get_recommended_parameter(self, param_name: str, action_type: str, default: Any) -> Any:
        """Get learned parameter value or default"""
        agent_data = self.memory["agents"][self.agent_name]
        learned = agent_data.get("learned_parameters", {}).get(action_type, {})
        adjustments = learned.get("recommended_adjustments", {})
        
        if param_name in adjustments:
            adj = adjustments[param_name]
            confidence = adj.get("confidence", 0)
            
            # Only use learned value if confidence is high enough
            if confidence > 0.3:
                return adj.get("target_value", default)
        
        return default
    
    def get_metrics(self) -> dict:
        """Get agent performance metrics"""
        return self.memory["agents"][self.agent_name]["metrics"]
    
    def get_learning_insights(self) -> dict:
        """Get current learned parameters and insights"""
        agent_data = self.memory["agents"][self.agent_name]
        return {
            "agent": self.agent_name,
            "metrics": agent_data["metrics"],
            "learned_parameters": agent_data.get("learned_parameters", {}),
            "recent_success_rate": self.get_success_rate(hours=24),
            "total_actions_24h": len(self.get_recent_actions(hours=24))
        }
    
    def should_execute(self, action_type: str, min_success_rate: float = 0.3) -> tuple:
        """
        Determine if an action should be executed based on historical performance.
        Returns (should_execute, reason)
        """
        recent = self.get_recent_actions(action_type, hours=24)
        
        if len(recent) < 3:
            return True, "Insufficient data - exploring"
        
        success_rate = self.get_success_rate(action_type, hours=24)
        
        if success_rate < min_success_rate:
            # Check if it's been consistently bad
            last_10 = recent[-10:] if len(recent) >= 10 else recent
            recent_success = sum(1 for a in last_10 if a["outcome"] == "success") / len(last_10)
            
            if recent_success < min_success_rate:
                return False, f"Low success rate: {success_rate:.1%}"
        
        return True, f"Success rate: {success_rate:.1%}"


class LearningMixin:
    """
    Mixin class to add learning capabilities to any agent.
    Add this to BaseAgent or individual agents.
    """
    
    def init_learning(self, agent_name: str):
        """Initialize the learning system"""
        self.memory = AgentMemory(agent_name)
        self._action_start_time = None
    
    def start_action(self):
        """Call before starting an action"""
        self._action_start_time = time.time()
    
    def record_action_result(
        self,
        action_type: str,
        parameters: dict,
        outcome: str,
        result_value: float,
        gas_used: int = 0,
        context: dict = None
    ):
        """Record the result of an action"""
        if not hasattr(self, 'memory'):
            return
        
        execution_time = 0
        if self._action_start_time:
            execution_time = int((time.time() - self._action_start_time) * 1000)
        
        action = ActionRecord(
            agent_name=self.memory.agent_name,
            action_type=action_type,
            parameters=parameters,
            timestamp=time.time(),
            outcome=outcome,
            result_value=result_value,
            gas_used=gas_used,
            execution_time_ms=execution_time,
            context=context or {}
        )
        
        self.memory.record_action(action)
    
    def get_learned_param(self, param_name: str, action_type: str, default: Any) -> Any:
        """Get a learned parameter value"""
        if not hasattr(self, 'memory'):
            return default
        return self.memory.get_recommended_parameter(param_name, action_type, default)
    
    def should_proceed(self, action_type: str) -> tuple:
        """Check if we should proceed with an action"""
        if not hasattr(self, 'memory'):
            return True, "No memory - proceeding"
        return self.memory.should_execute(action_type)


def print_learning_report():
    """Print a report of all agent learning"""
    try:
        with open(MEMORY_FILE, 'r') as f:
            memory = json.load(f)
    except:
        print("No memory file found")
        return
    
    print("=" * 60)
    print("THRYX AGENT LEARNING REPORT")
    print("=" * 60)
    
    for agent_name, agent_data in memory.get("agents", {}).items():
        metrics = agent_data.get("metrics", {})
        learned = agent_data.get("learned_parameters", {})
        
        print(f"\n{agent_name}:")
        print(f"  Total Actions: {metrics.get('total_actions', 0)}")
        
        total = metrics.get('total_actions', 1)
        success = metrics.get('successful_actions', 0)
        print(f"  Success Rate: {success/total*100:.1f}%")
        print(f"  Total Profit: ${metrics.get('total_profit', 0):.2f}")
        print(f"  Avg Execution: {metrics.get('avg_execution_time', 0):.0f}ms")
        
        if learned:
            print(f"  Learned Parameters:")
            for action_type, params in learned.items():
                print(f"    {action_type}: {params.get('success_rate', 0)*100:.0f}% success")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    print_learning_report()
