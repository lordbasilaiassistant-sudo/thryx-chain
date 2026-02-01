// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

interface ICreatorCoin {
    function buy(uint256 minTokensOut) external payable returns (uint256);
    function getCurrentPrice() external view returns (uint256);
    function totalEthLocked() external view returns (uint256);
    function symbol() external view returns (string memory);
}

/**
 * @title THRYX Value Protector
 * @notice Maintains price floors and protects ecosystem value
 * @dev AI agents use this to buy dips and support coin prices
 */
contract ValueProtector is Ownable, ReentrancyGuard {
    // Configuration
    uint256 public minBuyAmount = 0.01 ether;
    uint256 public maxBuyAmount = 1 ether;
    uint256 public dailyBudget = 10 ether;
    uint256 public cooldownTime = 300;  // 5 minutes between buys per coin
    
    // Tracking
    mapping(address => uint256) public lastBuyTime;
    mapping(address => uint256) public priceFloor;  // Minimum price to maintain
    mapping(address => uint256) public totalSupported;  // ETH spent supporting each coin
    
    uint256 public dailySpent;
    uint256 public lastDayReset;
    uint256 public totalValueProtected;
    uint256 public protectionCount;
    
    // Authorized agents
    mapping(address => bool) public authorizedAgents;
    
    // Events
    event ValueProtected(address indexed coin, uint256 amount, uint256 newPrice, string reason);
    event PriceFloorSet(address indexed coin, uint256 floor);
    event BudgetRefilled(uint256 amount);
    
    constructor() Ownable(msg.sender) {
        lastDayReset = block.timestamp;
    }
    
    modifier onlyAuthorized() {
        require(msg.sender == owner() || authorizedAgents[msg.sender], "Not authorized");
        _;
    }
    
    /**
     * @notice Protect a coin's value by buying
     * @param coin Creator coin to support
     * @param amount ETH to spend
     * @param reason Why protection is triggered
     */
    function protectValue(
        address coin,
        uint256 amount,
        string calldata reason
    ) external onlyAuthorized nonReentrant returns (bool) {
        // Reset daily budget if new day
        if (block.timestamp > lastDayReset + 1 days) {
            dailySpent = 0;
            lastDayReset = block.timestamp;
        }
        
        // Checks
        require(amount >= minBuyAmount, "Amount too small");
        require(amount <= maxBuyAmount, "Amount too large");
        require(dailySpent + amount <= dailyBudget, "Daily budget exceeded");
        require(block.timestamp >= lastBuyTime[coin] + cooldownTime, "Cooldown active");
        require(address(this).balance >= amount, "Insufficient balance");
        
        // Execute buy
        ICreatorCoin coinContract = ICreatorCoin(coin);
        uint256 priceBefore = coinContract.getCurrentPrice();
        
        coinContract.buy{value: amount}(0);
        
        uint256 priceAfter = coinContract.getCurrentPrice();
        
        // Update tracking
        lastBuyTime[coin] = block.timestamp;
        dailySpent += amount;
        totalSupported[coin] += amount;
        totalValueProtected += amount;
        protectionCount++;
        
        emit ValueProtected(coin, amount, priceAfter, reason);
        
        return priceAfter > priceBefore;
    }
    
    /**
     * @notice Set minimum price floor for a coin
     */
    function setPriceFloor(address coin, uint256 floor) external onlyAuthorized {
        priceFloor[coin] = floor;
        emit PriceFloorSet(coin, floor);
    }
    
    /**
     * @notice Check if a coin needs protection
     */
    function needsProtection(address coin) external view returns (bool, uint256 currentPrice, uint256 floor) {
        ICreatorCoin coinContract = ICreatorCoin(coin);
        currentPrice = coinContract.getCurrentPrice();
        floor = priceFloor[coin];
        
        if (floor == 0) {
            return (false, currentPrice, 0);
        }
        
        return (currentPrice < floor, currentPrice, floor);
    }
    
    /**
     * @notice Get protection stats
     */
    function getStats() external view returns (
        uint256 balance,
        uint256 _dailySpent,
        uint256 _dailyBudget,
        uint256 _totalProtected,
        uint256 _protectionCount,
        uint256 budgetRemaining
    ) {
        return (
            address(this).balance,
            dailySpent,
            dailyBudget,
            totalValueProtected,
            protectionCount,
            dailyBudget > dailySpent ? dailyBudget - dailySpent : 0
        );
    }
    
    // Admin
    function authorizeAgent(address agent, bool authorized) external onlyOwner {
        authorizedAgents[agent] = authorized;
    }
    
    function setDailyBudget(uint256 budget) external onlyOwner {
        dailyBudget = budget;
    }
    
    function setBuyLimits(uint256 min, uint256 max) external onlyOwner {
        minBuyAmount = min;
        maxBuyAmount = max;
    }
    
    function setCooldown(uint256 time) external onlyOwner {
        cooldownTime = time;
    }
    
    // Receive ETH for protection fund
    receive() external payable {
        emit BudgetRefilled(msg.value);
    }
}
