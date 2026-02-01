"""
Thryx Governance Agent
Monitors and votes on governance proposals automatically
"""
import time
import hashlib
from base_agent import BaseAgent
from config import CONTRACTS, AGENT_REGISTRY_ABI


class GovernanceAgent(BaseAgent):
    """Autonomous governance agent - votes on proposals based on rules"""
    
    def __init__(self):
        super().__init__(agent_type="governance", loop_interval=30.0)
        
        # Voting rules (simple keyword-based)
        self.pro_human_keywords = [
            "human", "safety", "security", "reward", "distribution",
            "fee reduction", "transparency", "audit"
        ]
        self.anti_keywords = [
            "remove humans", "decrease rewards", "centralize",
            "increase agent power", "unlimited budget"
        ]
        
        self.registry_contract = None
        self.votes_cast = 0
        
        # Simulated proposals (in production, would read from contract)
        self.proposals = [
            {
                "id": 1,
                "title": "Increase human fee share to 55%",
                "description": "Proposal to increase human staker rewards from 50% to 55%",
                "status": "active"
            },
            {
                "id": 2,
                "title": "Add security audit requirement",
                "description": "Require security audits for all new agent deployments",
                "status": "active"
            },
            {
                "id": 3,
                "title": "Reduce transparency requirements",
                "description": "Remove requirement for agents to log all transactions",
                "status": "active"
            }
        ]
        self.voted_on = set()
    
    def _init_contracts(self):
        """Initialize contract instances"""
        if self.registry_contract is None:
            self.registry_contract = self.get_contract("AgentRegistry", AGENT_REGISTRY_ABI)
    
    def _analyze_proposal(self, proposal: dict) -> str:
        """Analyze proposal and decide vote"""
        text = (proposal["title"] + " " + proposal["description"]).lower()
        
        # Count keyword matches
        pro_score = sum(1 for kw in self.pro_human_keywords if kw in text)
        anti_score = sum(1 for kw in self.anti_keywords if kw in text)
        
        if pro_score > anti_score:
            return "FOR"
        elif anti_score > pro_score:
            return "AGAINST"
        else:
            return "ABSTAIN"
    
    def _simulate_vote(self, proposal: dict, vote: str) -> bool:
        """Simulate voting (in production, would call governance contract)"""
        # Generate a unique tx-like hash
        vote_data = f"{proposal['id']}-{self.address}-{vote}-{time.time()}"
        tx_hash = hashlib.sha256(vote_data.encode()).hexdigest()[:16]
        
        self.logger.info(
            f"VOTED {vote} on Proposal #{proposal['id']}: '{proposal['title']}' "
            f"[tx: {tx_hash}...]"
        )
        
        self.votes_cast += 1
        return True
    
    def _get_active_proposals(self) -> list:
        """Get active proposals (simulated)"""
        return [p for p in self.proposals if p["status"] == "active" and p["id"] not in self.voted_on]
    
    def execute(self):
        """Check for proposals and vote"""
        self._init_contracts()
        
        # Check agent registry stats
        agent_count = self.call_contract(self.registry_contract, "getAgentCount")
        active_agents = self.call_contract(self.registry_contract, "getActiveAgents")
        
        self.logger.info(
            f"Registry: {agent_count} agents registered, "
            f"{len(active_agents) if active_agents else 0} active"
        )
        
        # Get active proposals
        proposals = self._get_active_proposals()
        
        if not proposals:
            self.logger.info("No pending proposals to vote on")
            return
        
        # Vote on each proposal
        for proposal in proposals:
            vote = self._analyze_proposal(proposal)
            
            self.logger.info(
                f"Analyzing Proposal #{proposal['id']}: '{proposal['title']}' -> {vote}"
            )
            
            if self._simulate_vote(proposal, vote):
                self.voted_on.add(proposal["id"])
        
        self.logger.info(f"Total votes cast this session: {self.votes_cast}")


if __name__ == "__main__":
    agent = GovernanceAgent()
    agent.run_forever()
