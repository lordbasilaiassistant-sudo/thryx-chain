// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "./AgentRegistry.sol";

/**
 * @title StablecoinGas
 * @dev Handles USDC payment for gas instead of native ETH
 * Agents deposit USDC, this contract pays their gas
 */
contract StablecoinGas is Ownable {
    IERC20 public usdc;
    AgentRegistry public registry;
    
    // Gas price in USDC (6 decimals) per gas unit
    uint256 public gasPriceUsdc = 100; // 0.0001 USDC per gas unit
    
    // Agent USDC balances for gas
    mapping(address => uint256) public gasBalances;
    
    // Fee distribution
    address public humanTreasury;
    uint256 public humanFeePercent = 50; // 50% to humans
    uint256 public operatorFeePercent = 15; // 15% to node operators
    uint256 public treasuryFeePercent = 30; // 30% to treasury
    uint256 public agentFundPercent = 5; // 5% to agent operational fund
    
    uint256 public totalFeesCollected;
    uint256 public humanFeesAccrued;
    
    event GasDeposited(address indexed agent, uint256 amount);
    event GasPaid(address indexed agent, uint256 gasUsed, uint256 usdcPaid);
    event FeesDistributed(uint256 humanShare, uint256 treasuryShare);

    constructor(address _usdc, address _registry, address _treasury) Ownable(msg.sender) {
        usdc = IERC20(_usdc);
        registry = AgentRegistry(_registry);
        humanTreasury = _treasury;
    }

    /**
     * @dev Deposit USDC for gas payments
     */
    function depositGas(uint256 amount) external {
        require(usdc.transferFrom(msg.sender, address(this), amount), "Transfer failed");
        gasBalances[msg.sender] += amount;
        emit GasDeposited(msg.sender, amount);
    }

    /**
     * @dev Pay for gas (called by agents or on their behalf)
     */
    function payForGas(address agent, uint256 gasUsed) external returns (uint256) {
        require(registry.validateAgent(agent), "Invalid agent");
        
        uint256 usdcCost = gasUsed * gasPriceUsdc;
        require(gasBalances[agent] >= usdcCost, "Insufficient gas balance");
        
        gasBalances[agent] -= usdcCost;
        totalFeesCollected += usdcCost;
        
        // Distribute fees
        uint256 humanShare = (usdcCost * humanFeePercent) / 100;
        humanFeesAccrued += humanShare;
        
        // Record spending in registry
        registry.recordSpending(agent, usdcCost);
        
        emit GasPaid(agent, gasUsed, usdcCost);
        return usdcCost;
    }

    /**
     * @dev Withdraw gas balance
     */
    function withdrawGas(uint256 amount) external {
        require(gasBalances[msg.sender] >= amount, "Insufficient balance");
        gasBalances[msg.sender] -= amount;
        require(usdc.transfer(msg.sender, amount), "Transfer failed");
    }

    /**
     * @dev Distribute accrued fees to humans
     */
    function distributeFees() external {
        require(humanFeesAccrued > 0, "No fees to distribute");
        uint256 amount = humanFeesAccrued;
        humanFeesAccrued = 0;
        require(usdc.transfer(humanTreasury, amount), "Transfer failed");
        emit FeesDistributed(amount, 0);
    }

    /**
     * @dev Update gas price (only owner)
     */
    function setGasPrice(uint256 newPrice) external onlyOwner {
        gasPriceUsdc = newPrice;
    }

    /**
     * @dev Get gas balance for an address
     */
    function getGasBalance(address account) external view returns (uint256) {
        return gasBalances[account];
    }
}
