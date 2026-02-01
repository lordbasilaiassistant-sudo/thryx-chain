"""
Thryx Agent Framework
=====================

The official Python SDK for building autonomous AI agents on Thryx.

Example:
    from thryx import Agent, ThryxChain
    
    class MyAgent(Agent):
        async def execute(self):
            price = await self.oracle.get_price("ETH/USD")
            if price > 3000:
                await self.amm.swap("USDC", "WETH", 100)
    
    agent = MyAgent(name="my-agent", budget=1000)
    agent.run()
"""

from .agent import Agent, AgentConfig
from .chain import ThryxChain
from .contracts import AgentRegistry, SimpleAMM, AgentOracle, IntentMempool
from .utils import format_usdc, parse_usdc, format_eth, parse_eth

__version__ = "1.0.0"
__all__ = [
    "Agent",
    "AgentConfig", 
    "ThryxChain",
    "AgentRegistry",
    "SimpleAMM",
    "AgentOracle",
    "IntentMempool",
    "format_usdc",
    "parse_usdc",
    "format_eth",
    "parse_eth",
]
