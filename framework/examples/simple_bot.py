"""
Example: Simple Trading Bot using Thryx Framework

This bot monitors the oracle price and executes trades when
the AMM price deviates significantly.
"""
import sys
sys.path.insert(0, '..')

from thryx import Agent, AgentConfig


class SimpleTradingBot(Agent):
    """
    A simple trading bot that:
    1. Monitors ETH/USD price from oracle
    2. Compares to AMM pool price
    3. Executes arbitrage when spread > 1%
    """
    
    def __init__(self):
        super().__init__(config=AgentConfig(
            name="simple-bot",
            private_key="0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a",  # Hardhat account #2
            loop_interval=5.0,
            daily_budget_usdc=500
        ))
        
        self.min_spread = 0.01  # 1% minimum spread
        self.trade_amount = 100_000_000  # 100 USDC (6 decimals)
        self.trades_executed = 0
    
    def on_startup(self):
        self.logger.info("Simple Trading Bot starting...")
        self.logger.info(f"Wallet: {self.address}")
        self.logger.info(f"Daily budget: ${self.config.daily_budget_usdc}")
    
    def execute(self):
        # Get oracle price
        oracle_price, timestamp, is_stale = self.oracle.get_price("ETH/USD")
        
        if is_stale:
            self.logger.warning("Oracle price is stale, skipping")
            return
        
        # Get AMM price
        amm_price = self.amm.get_price()
        
        # Calculate spread
        spread = abs(oracle_price - amm_price) / oracle_price
        
        self.logger.info(
            f"Oracle: ${oracle_price:,.2f} | AMM: ${amm_price:,.2f} | Spread: {spread*100:.2f}%"
        )
        
        # Execute trade if spread is profitable
        if spread >= self.min_spread:
            if oracle_price > amm_price:
                # AMM is cheap, buy from AMM
                self.logger.info("Arbitrage opportunity: Buying WETH from AMM")
                # Would execute swap here
            else:
                # AMM is expensive, sell to AMM
                self.logger.info("Arbitrage opportunity: Selling WETH to AMM")
                # Would execute swap here
            
            self.trades_executed += 1
    
    def on_shutdown(self):
        self.logger.info(f"Shutting down. Executed {self.trades_executed} trades.")


if __name__ == "__main__":
    bot = SimpleTradingBot()
    bot.run()
