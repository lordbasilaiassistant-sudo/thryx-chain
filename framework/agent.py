"""
Thryx Agent Base Class
"""
import time
import logging
import signal
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from .chain import ThryxChain
from .contracts import AgentRegistry, SimpleAMM, AgentOracle


@dataclass
class AgentConfig:
    """Configuration for a Thryx agent"""
    name: str
    private_key: str
    rpc_url: str = "http://localhost:8545"
    daily_budget_usdc: int = 1000
    loop_interval: float = 10.0
    max_retries: int = 3
    log_level: str = "INFO"
    permissions: List[str] = field(default_factory=lambda: ["TRADE"])


class Agent(ABC):
    """
    Base class for all Thryx autonomous agents.
    
    Subclass this and implement the `execute()` method to create your agent.
    
    Example:
        class PriceBot(Agent):
            async def execute(self):
                price = self.oracle.get_price("ETH/USD")
                self.logger.info(f"ETH price: ${price}")
                
                if price < 2000:
                    self.amm.swap("USDC", "WETH", 100)
        
        bot = PriceBot(config=AgentConfig(
            name="price-bot",
            private_key="0x...",
            daily_budget_usdc=500
        ))
        bot.run()
    """
    
    def __init__(self, config: AgentConfig = None, **kwargs):
        """
        Initialize agent.
        
        Args:
            config: AgentConfig object with all settings
            **kwargs: Override individual config values
        """
        # Build config from kwargs if not provided
        if config is None:
            config = AgentConfig(
                name=kwargs.get('name', 'unnamed-agent'),
                private_key=kwargs.get('private_key', ''),
                rpc_url=kwargs.get('rpc_url', 'http://localhost:8545'),
                daily_budget_usdc=kwargs.get('daily_budget_usdc', 1000),
                loop_interval=kwargs.get('loop_interval', 10.0),
            )
        
        self.config = config
        self.name = config.name
        
        # Setup logging
        self.logger = logging.getLogger(f"thryx.{self.name}")
        self.logger.setLevel(getattr(logging, config.log_level))
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter(
                f'[{self.name.upper()}] %(asctime)s - %(message)s',
                datefmt='%H:%M:%S'
            ))
            self.logger.addHandler(handler)
        
        # Initialize chain connection
        self.chain = ThryxChain(
            rpc_url=config.rpc_url,
            private_key=config.private_key
        )
        
        # Initialize contract helpers
        self._registry: Optional[AgentRegistry] = None
        self._amm: Optional[SimpleAMM] = None
        self._oracle: Optional[AgentOracle] = None
        
        # Stats
        self.tx_count = 0
        self.error_count = 0
        self.start_time = time.time()
        self._running = False
        
        # Graceful shutdown
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)
    
    @property
    def registry(self) -> AgentRegistry:
        """Get AgentRegistry contract helper"""
        if self._registry is None:
            self._registry = AgentRegistry(self.chain)
        return self._registry
    
    @property
    def amm(self) -> SimpleAMM:
        """Get SimpleAMM contract helper"""
        if self._amm is None:
            self._amm = SimpleAMM(self.chain)
        return self._amm
    
    @property
    def oracle(self) -> AgentOracle:
        """Get AgentOracle contract helper"""
        if self._oracle is None:
            self._oracle = AgentOracle(self.chain)
        return self._oracle
    
    @property
    def address(self) -> str:
        """Get agent's wallet address"""
        return self.chain.address
    
    def _handle_shutdown(self, signum, frame):
        """Handle graceful shutdown"""
        self.logger.info("Shutting down...")
        self._running = False
        self.on_shutdown()
        sys.exit(0)
    
    def on_startup(self):
        """Called when agent starts. Override for custom initialization."""
        pass
    
    def on_shutdown(self):
        """Called when agent stops. Override for cleanup."""
        pass
    
    def on_error(self, error: Exception):
        """Called when an error occurs. Override for custom error handling."""
        self.logger.error(f"Error: {error}")
    
    @abstractmethod
    def execute(self):
        """
        Main agent logic. Called every loop_interval seconds.
        
        Override this method to implement your agent's behavior.
        """
        pass
    
    def run(self):
        """Start the agent's main loop"""
        self.logger.info(f"Starting agent at {self.address}")
        self._running = True
        
        # Wait for RPC
        self._wait_for_rpc()
        
        # Startup hook
        self.on_startup()
        
        # Main loop
        while self._running:
            try:
                self.execute()
            except KeyboardInterrupt:
                break
            except Exception as e:
                self.error_count += 1
                self.on_error(e)
            
            time.sleep(self.config.loop_interval)
    
    def _wait_for_rpc(self, max_retries: int = 30):
        """Wait for RPC to become available"""
        for i in range(max_retries):
            if self.chain.connected:
                self.logger.info(f"Connected to RPC at block {self.chain.block_number}")
                return
            self.logger.info(f"Waiting for RPC... ({i+1}/{max_retries})")
            time.sleep(2)
        raise ConnectionError("RPC not available")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get agent statistics"""
        uptime = time.time() - self.start_time
        return {
            "name": self.name,
            "address": self.address,
            "tx_count": self.tx_count,
            "error_count": self.error_count,
            "uptime_seconds": uptime,
            "tx_per_minute": (self.tx_count / uptime) * 60 if uptime > 0 else 0
        }
