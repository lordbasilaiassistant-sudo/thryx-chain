// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

interface ICreatorCoin {
    function buy(uint256 minTokensOut) external payable returns (uint256);
    function getCurrentPrice() external view returns (uint256);
    function totalTrades() external view returns (uint256);
    function creator() external view returns (address);
    function symbol() external view returns (string memory);
}

/**
 * @title THRYX Creator Boost
 * @notice Promotes verified creators with strategic buys
 * @dev AI agents identify quality creators and boost their coins
 */
contract CreatorBoost is Ownable, ReentrancyGuard {
    // Creator verification status
    enum VerificationLevel { None, Basic, Verified, Premium }
    
    struct CreatorProfile {
        VerificationLevel level;
        uint256 boostsReceived;
        uint256 totalBoostValue;
        uint256 lastBoostTime;
        string category;  // "art", "music", "tech", "content", etc.
        bool active;
    }
    
    // Storage
    mapping(address => CreatorProfile) public creators;  // creator address => profile
    mapping(address => address) public coinToCreator;    // coin => creator
    address[] public verifiedCreators;
    
    // Boost configuration
    uint256 public boostAmount = 0.05 ether;
    uint256 public boostCooldown = 1 hours;
    uint256 public dailyBoostBudget = 5 ether;
    uint256 public dailyBoostSpent;
    uint256 public lastDayReset;
    
    // Stats
    uint256 public totalBoosts;
    uint256 public totalBoostValue;
    
    // Authorized agents
    mapping(address => bool) public authorizedAgents;
    
    // Events
    event CreatorVerified(address indexed creator, VerificationLevel level, string category);
    event CreatorBoosted(address indexed creator, address indexed coin, uint256 amount);
    event CoinRegistered(address indexed coin, address indexed creator);
    
    constructor() Ownable(msg.sender) {
        lastDayReset = block.timestamp;
    }
    
    modifier onlyAuthorized() {
        require(msg.sender == owner() || authorizedAgents[msg.sender], "Not authorized");
        _;
    }
    
    /**
     * @notice Register a coin with its creator
     */
    function registerCoin(address coin, address creator) external onlyAuthorized {
        coinToCreator[coin] = creator;
        
        if (!creators[creator].active) {
            creators[creator] = CreatorProfile({
                level: VerificationLevel.Basic,
                boostsReceived: 0,
                totalBoostValue: 0,
                lastBoostTime: 0,
                category: "",
                active: true
            });
        }
        
        emit CoinRegistered(coin, creator);
    }
    
    /**
     * @notice Verify a creator (upgrades their status)
     */
    function verifyCreator(
        address creator,
        VerificationLevel level,
        string calldata category
    ) external onlyAuthorized {
        CreatorProfile storage profile = creators[creator];
        
        if (!profile.active) {
            profile.active = true;
            verifiedCreators.push(creator);
        }
        
        profile.level = level;
        profile.category = category;
        
        emit CreatorVerified(creator, level, category);
    }
    
    /**
     * @notice Boost a creator's coin with a buy
     */
    function boostCreator(address coin) external onlyAuthorized nonReentrant returns (bool) {
        // Reset daily budget
        if (block.timestamp > lastDayReset + 1 days) {
            dailyBoostSpent = 0;
            lastDayReset = block.timestamp;
        }
        
        address creator = coinToCreator[coin];
        require(creator != address(0), "Coin not registered");
        
        CreatorProfile storage profile = creators[creator];
        require(profile.active, "Creator not active");
        require(profile.level >= VerificationLevel.Basic, "Creator not verified");
        require(block.timestamp >= profile.lastBoostTime + boostCooldown, "Boost cooldown");
        require(dailyBoostSpent + boostAmount <= dailyBoostBudget, "Daily budget exceeded");
        require(address(this).balance >= boostAmount, "Insufficient balance");
        
        // Calculate boost amount based on verification level
        uint256 amount = boostAmount;
        if (profile.level == VerificationLevel.Verified) {
            amount = boostAmount * 2;  // 2x for verified
        } else if (profile.level == VerificationLevel.Premium) {
            amount = boostAmount * 3;  // 3x for premium
        }
        
        if (amount > address(this).balance) {
            amount = address(this).balance;
        }
        
        // Execute boost buy
        ICreatorCoin(coin).buy{value: amount}(0);
        
        // Update tracking
        profile.boostsReceived++;
        profile.totalBoostValue += amount;
        profile.lastBoostTime = block.timestamp;
        dailyBoostSpent += amount;
        totalBoosts++;
        totalBoostValue += amount;
        
        emit CreatorBoosted(creator, coin, amount);
        
        return true;
    }
    
    /**
     * @notice Get creator profile
     */
    function getCreator(address creator) external view returns (
        VerificationLevel level,
        uint256 boostsReceived,
        uint256 totalBoostValue,
        string memory category,
        bool canBoost
    ) {
        CreatorProfile storage profile = creators[creator];
        bool _canBoost = profile.active && 
                         profile.level >= VerificationLevel.Basic &&
                         block.timestamp >= profile.lastBoostTime + boostCooldown;
        
        return (
            profile.level,
            profile.boostsReceived,
            profile.totalBoostValue,
            profile.category,
            _canBoost
        );
    }
    
    /**
     * @notice Get all verified creators
     */
    function getVerifiedCreators() external view returns (address[] memory) {
        return verifiedCreators;
    }
    
    /**
     * @notice Get stats
     */
    function getStats() external view returns (
        uint256 balance,
        uint256 _totalBoosts,
        uint256 _totalValue,
        uint256 creatorCount,
        uint256 dailyRemaining
    ) {
        return (
            address(this).balance,
            totalBoosts,
            totalBoostValue,
            verifiedCreators.length,
            dailyBoostBudget > dailyBoostSpent ? dailyBoostBudget - dailyBoostSpent : 0
        );
    }
    
    // Admin
    function authorizeAgent(address agent, bool authorized) external onlyOwner {
        authorizedAgents[agent] = authorized;
    }
    
    function setBoostAmount(uint256 amount) external onlyOwner {
        boostAmount = amount;
    }
    
    function setDailyBudget(uint256 budget) external onlyOwner {
        dailyBoostBudget = budget;
    }
    
    receive() external payable {}
}
