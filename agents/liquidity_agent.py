"""
Thryx Liquidity Agent
Provides and manages liquidity in the SimpleAMM
"""
from base_agent import BaseAgent
from config import CONTRACTS, SIMPLE_AMM_ABI, ERC20_ABI


class LiquidityAgent(BaseAgent):
    """Autonomous liquidity provider - manages AMM liquidity positions"""
    
    def __init__(self):
        super().__init__(agent_type="liquidity", loop_interval=60.0)  # Check every minute
        
        self.target_ratio = 1.0  # Target USDC/WETH value ratio
        self.rebalance_threshold = 0.1  # Rebalance if ratio off by 10%
        
        self.amm_contract = None
        self.usdc_contract = None
        self.weth_contract = None
        
        self.liquidity_added = False
    
    def _init_contracts(self):
        """Initialize contract instances"""
        if self.amm_contract is None:
            self.amm_contract = self.get_contract("SimpleAMM", SIMPLE_AMM_ABI)
            self.usdc_contract = self.get_contract("MockUSDC", ERC20_ABI)
            self.weth_contract = self.get_contract("MockWETH", ERC20_ABI)
    
    def _get_balances(self) -> dict:
        """Get agent's token balances"""
        usdc_balance = self.call_contract(self.usdc_contract, "balanceOf", self.address)
        weth_balance = self.call_contract(self.weth_contract, "balanceOf", self.address)
        
        return {
            "usdc": usdc_balance or 0,
            "weth": weth_balance or 0
        }
    
    def _get_pool_state(self) -> dict:
        """Get current pool reserves"""
        reserve_a = self.call_contract(self.amm_contract, "reserveA") or 0
        reserve_b = self.call_contract(self.amm_contract, "reserveB") or 0
        price = self.call_contract(self.amm_contract, "getPrice") or 0
        
        return {
            "reserve_usdc": reserve_a,
            "reserve_weth": reserve_b,
            "price": price
        }
    
    def _add_initial_liquidity(self):
        """Add initial liquidity if pool needs it"""
        pool = self._get_pool_state()
        balances = self._get_balances()
        
        if pool["reserve_usdc"] == 0 or pool["reserve_weth"] == 0:
            # Pool empty, add initial liquidity
            usdc_amount = min(balances["usdc"], 10000 * 10**6)  # 10k USDC
            weth_amount = min(balances["weth"], 4 * 10**18)  # 4 WETH (~$10k at $2500)
            
            if usdc_amount > 0 and weth_amount > 0:
                self.logger.info(f"Adding initial liquidity: {usdc_amount/1e6} USDC + {weth_amount/1e18} WETH")
                
                # Approve tokens
                approve_usdc = self.build_contract_tx(
                    self.usdc_contract, "approve",
                    CONTRACTS["SimpleAMM"], usdc_amount
                )
                self.send_transaction(approve_usdc)
                
                approve_weth = self.build_contract_tx(
                    self.weth_contract, "approve",
                    CONTRACTS["SimpleAMM"], weth_amount
                )
                self.send_transaction(approve_weth)
                
                # Add liquidity
                add_liq = self.build_contract_tx(
                    self.amm_contract, "addLiquidity",
                    usdc_amount, weth_amount
                )
                result = self.send_transaction(add_liq)
                
                if result:
                    self.liquidity_added = True
                    self.logger.info("Initial liquidity added successfully")
    
    def _check_rebalance_needed(self) -> bool:
        """Check if pool needs rebalancing"""
        pool = self._get_pool_state()
        
        if pool["reserve_weth"] == 0:
            return False
        
        # Calculate current ratio (USDC value / WETH value)
        # Assuming 1 WETH = $2500 for simplicity
        eth_price_usd = 2500
        usdc_value = pool["reserve_usdc"] / 10**6
        weth_value = (pool["reserve_weth"] / 10**18) * eth_price_usd
        
        if weth_value == 0:
            return False
        
        ratio = usdc_value / weth_value
        deviation = abs(ratio - self.target_ratio) / self.target_ratio
        
        return deviation > self.rebalance_threshold
    
    def execute(self):
        """Manage liquidity position"""
        self._init_contracts()
        
        pool = self._get_pool_state()
        balances = self._get_balances()
        
        # Log current state
        self.logger.info(
            f"Pool: {pool['reserve_usdc']/1e6:,.0f} USDC / {pool['reserve_weth']/1e18:.2f} WETH | "
            f"Balance: {balances['usdc']/1e6:,.0f} USDC / {balances['weth']/1e18:.2f} WETH"
        )
        
        # Add initial liquidity if needed
        if pool["reserve_usdc"] == 0 or pool["reserve_weth"] == 0:
            self._add_initial_liquidity()
            return
        
        # Check if rebalancing needed
        if self._check_rebalance_needed():
            self.logger.info("Rebalancing needed - would adjust position here")
            # In production, would remove and re-add liquidity at proper ratio


if __name__ == "__main__":
    agent = LiquidityAgent()
    agent.run_forever()
