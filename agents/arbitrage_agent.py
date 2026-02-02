"""
Thryx Arbitrage Agent
Monitors AMM prices vs oracle prices and executes profitable swaps
"""
from web3 import Web3

from base_agent import BaseAgent
from config import CONTRACTS, SIMPLE_AMM_ABI, AGENT_ORACLE_ABI, ERC20_ABI


class ArbitrageAgent(BaseAgent):
    """Autonomous arbitrage agent - finds and executes profitable trades"""
    
    def __init__(self):
        super().__init__(agent_type="arbitrage", loop_interval=5.0)
        
        self.min_profit_percent = 0.5  # 0.5% minimum profit
        self.max_trade_usdc = 1000 * 10**6  # Max 1000 USDC per trade
        
        self.amm_contract = None
        self.oracle_contract = None
        self.usdc_contract = None
        self.weth_contract = None
        
        self.total_profit = 0
    
    def _init_contracts(self):
        """Initialize contract instances"""
        if self.amm_contract is None:
            self.amm_contract = self.get_contract("SimpleAMM", SIMPLE_AMM_ABI)
            self.oracle_contract = self.get_contract("AgentOracle", AGENT_ORACLE_ABI)
            self.usdc_contract = self.get_contract("MockUSDC", ERC20_ABI)
            self.weth_contract = self.get_contract("MockWETH", ERC20_ABI)
    
    def _get_oracle_price(self) -> int:
        """Get ETH/USD price from oracle (8 decimals)"""
        pair_hash = Web3.keccak(text="ETH/USD")
        result = self.call_contract(self.oracle_contract, "getPrice", pair_hash)
        if result:
            return result[0]  # (price, timestamp, isStale)
        return 0
    
    def _get_amm_price(self) -> int:
        """Get ETH price from AMM reserves (18 decimals -> convert to 8)"""
        reserve_a = self.call_contract(self.amm_contract, "reserveA")  # USDC (6 decimals)
        reserve_b = self.call_contract(self.amm_contract, "reserveB")  # WETH (18 decimals)
        
        if not reserve_a or not reserve_b or reserve_b == 0:
            return 0
        
        # Price = USDC per WETH, convert to 8 decimals
        # USDC has 6 decimals, WETH has 18
        # price = (reserve_a * 10^18) / (reserve_b * 10^6) * 10^8
        price = (reserve_a * 10**20) // reserve_b
        return price
    
    def _check_arbitrage(self) -> dict:
        """Check for arbitrage opportunity"""
        oracle_price = self._get_oracle_price()
        amm_price = self._get_amm_price()
        
        if oracle_price == 0 or amm_price == 0:
            return None
        
        # Calculate price difference
        if amm_price > oracle_price:
            # AMM price higher than oracle -> sell WETH for USDC
            diff_percent = ((amm_price - oracle_price) / oracle_price) * 100
            direction = "sell_weth"
        else:
            # AMM price lower than oracle -> buy WETH with USDC  
            diff_percent = ((oracle_price - amm_price) / oracle_price) * 100
            direction = "buy_weth"
        
        if diff_percent >= self.min_profit_percent:
            return {
                "direction": direction,
                "oracle_price": oracle_price,
                "amm_price": amm_price,
                "diff_percent": diff_percent
            }
        
        return None
    
    def _execute_swap(self, direction: str) -> bool:
        """Execute swap transaction"""
        try:
            if direction == "buy_weth":
                # Buy WETH with USDC
                amount_in = min(self.max_trade_usdc, 100 * 10**6)  # 100 USDC
                token_in = CONTRACTS["MockUSDC"]
                
                # Approve USDC
                approve_tx = self.build_contract_tx(
                    self.usdc_contract, "approve",
                    CONTRACTS["SimpleAMM"], amount_in
                )
                self.send_transaction(approve_tx)
                
                # Get expected output
                amount_out = self.call_contract(
                    self.amm_contract, "getAmountOut",
                    token_in, amount_in
                )
                
                if not amount_out or amount_out == 0:
                    return False
                
                # Execute swap with 1% slippage
                min_out = int(amount_out * 0.99)
                swap_tx = self.build_contract_tx(
                    self.amm_contract, "swap",
                    token_in, amount_in, min_out
                )
                result = self.send_transaction(swap_tx)
                
                if result:
                    profit = (amount_out * self._get_oracle_price() // 10**26) - (amount_in // 10**6)
                    self.total_profit += profit
                    self.logger.info(f"Bought WETH, estimated profit: ${profit:.2f}")
                    return True
                    
            else:
                # Sell WETH for USDC
                amount_in = 10**16  # 0.01 WETH
                token_in = CONTRACTS["MockWETH"]
                
                # Approve WETH
                approve_tx = self.build_contract_tx(
                    self.weth_contract, "approve",
                    CONTRACTS["SimpleAMM"], amount_in
                )
                self.send_transaction(approve_tx)
                
                # Get expected output
                amount_out = self.call_contract(
                    self.amm_contract, "getAmountOut",
                    token_in, amount_in
                )
                
                if not amount_out or amount_out == 0:
                    return False
                
                # Execute swap
                min_out = int(amount_out * 0.99)
                swap_tx = self.build_contract_tx(
                    self.amm_contract, "swap",
                    token_in, amount_in, min_out
                )
                result = self.send_transaction(swap_tx)
                
                if result:
                    expected_value = (amount_in * self._get_oracle_price()) // 10**26
                    profit = (amount_out // 10**6) - expected_value
                    self.total_profit += profit
                    self.logger.info(f"Sold WETH, estimated profit: ${profit:.2f}")
                    return True
                    
        except Exception as e:
            self.logger.error(f"Swap execution failed: {e}")
        
        return False
    
    def execute(self):
        """Check for and execute arbitrage opportunities"""
        self._init_contracts()
        
        opportunity = self._check_arbitrage()
        
        if opportunity:
            self.logger.info(
                f"Arb opportunity: {opportunity['direction']} | "
                f"Oracle: ${opportunity['oracle_price']/1e8:,.2f} | "
                f"AMM: ${opportunity['amm_price']/1e8:,.2f} | "
                f"Spread: {opportunity['diff_percent']:.2f}%"
            )
            self._execute_swap(opportunity["direction"])
        else:
            oracle = self._get_oracle_price()
            amm = self._get_amm_price()
            if oracle > 0 and amm > 0:
                self.logger.info(
                    f"No arb | Oracle: ${oracle/1e8:,.2f} | AMM: ${amm/1e8:,.2f}"
                )


if __name__ == "__main__":
    agent = ArbitrageAgent()
    agent.run_forever()
