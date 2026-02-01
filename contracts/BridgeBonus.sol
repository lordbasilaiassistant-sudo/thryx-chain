// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title BridgeBonus
 * @dev Rewards token for users who bridge from Base to THRYX
 * 
 * Features:
 * - Mint bonus tokens when users bridge ETH/USDC from Base
 * - Tiered bonuses based on bridge amount
 * - Early adopter multipliers
 * - Loyalty rewards for repeat bridgers
 */
contract BridgeBonus is ERC20, Ownable {
    // Bridge agent that can mint bonuses
    address public bridgeAgent;
    
    // Bonus tiers (in ETH, scaled by 1e18)
    uint256 public constant TIER1_THRESHOLD = 0.01 ether;  // 0.01 ETH
    uint256 public constant TIER2_THRESHOLD = 0.1 ether;   // 0.1 ETH
    uint256 public constant TIER3_THRESHOLD = 1 ether;     // 1 ETH
    
    // Bonus multipliers (100 = 1x, 200 = 2x, etc)
    uint256 public constant TIER1_MULTIPLIER = 100;   // 1x bonus
    uint256 public constant TIER2_MULTIPLIER = 150;   // 1.5x bonus
    uint256 public constant TIER3_MULTIPLIER = 200;   // 2x bonus
    
    // Base bonus rate: 100 BRIDGE tokens per ETH bridged
    uint256 public constant BASE_BONUS_RATE = 100;
    
    // Early adopter bonus (first 100 bridgers get 3x)
    uint256 public totalBridgers;
    uint256 public constant EARLY_ADOPTER_LIMIT = 100;
    uint256 public constant EARLY_ADOPTER_MULTIPLIER = 300;  // 3x
    
    // Track bridger stats for loyalty
    mapping(address => uint256) public bridgeCount;
    mapping(address => uint256) public totalBridged;
    mapping(address => uint256) public bonusEarned;
    
    // Events
    event BonusMinted(address indexed user, uint256 bridgeAmount, uint256 bonusAmount, string tier);
    event BridgeAgentUpdated(address newAgent);
    
    constructor() ERC20("THRYX Bridge Bonus", "BRIDGE") Ownable(msg.sender) {}
    
    /**
     * @dev Set the bridge agent address (can mint bonuses)
     */
    function setBridgeAgent(address _agent) external onlyOwner {
        bridgeAgent = _agent;
        emit BridgeAgentUpdated(_agent);
    }
    
    /**
     * @dev Calculate bonus amount for a bridge
     */
    function calculateBonus(address user, uint256 bridgeAmount) public view returns (uint256 bonus, string memory tier) {
        // Base bonus
        bonus = (bridgeAmount * BASE_BONUS_RATE) / 1 ether;
        tier = "Base";
        
        // Apply tier multiplier
        if (bridgeAmount >= TIER3_THRESHOLD) {
            bonus = (bonus * TIER3_MULTIPLIER) / 100;
            tier = "Whale";
        } else if (bridgeAmount >= TIER2_THRESHOLD) {
            bonus = (bonus * TIER2_MULTIPLIER) / 100;
            tier = "Gold";
        } else if (bridgeAmount >= TIER1_THRESHOLD) {
            bonus = (bonus * TIER1_MULTIPLIER) / 100;
            tier = "Silver";
        }
        
        // Early adopter bonus
        if (totalBridgers < EARLY_ADOPTER_LIMIT && bridgeCount[user] == 0) {
            bonus = (bonus * EARLY_ADOPTER_MULTIPLIER) / 100;
            tier = string(abi.encodePacked(tier, " + Early Adopter"));
        }
        
        // Loyalty bonus (10% extra per previous bridge, max 50%)
        uint256 loyaltyBonus = bridgeCount[user] * 10;
        if (loyaltyBonus > 50) loyaltyBonus = 50;
        bonus = bonus + (bonus * loyaltyBonus) / 100;
        
        // Scale to 18 decimals
        bonus = bonus * 1e18;
        
        return (bonus, tier);
    }
    
    /**
     * @dev Mint bonus tokens for a bridge (called by bridge agent)
     */
    function mintBonus(address user, uint256 bridgeAmount) external returns (uint256) {
        require(msg.sender == bridgeAgent || msg.sender == owner(), "Only bridge agent");
        require(user != address(0), "Invalid user");
        require(bridgeAmount > 0, "Invalid amount");
        
        (uint256 bonus, string memory tier) = calculateBonus(user, bridgeAmount);
        
        // Update stats
        if (bridgeCount[user] == 0) {
            totalBridgers++;
        }
        bridgeCount[user]++;
        totalBridged[user] += bridgeAmount;
        bonusEarned[user] += bonus;
        
        // Mint bonus tokens
        _mint(user, bonus);
        
        emit BonusMinted(user, bridgeAmount, bonus, tier);
        
        return bonus;
    }
    
    /**
     * @dev Get user stats
     */
    function getUserStats(address user) external view returns (
        uint256 bridges,
        uint256 totalBridgedAmount,
        uint256 totalBonusEarned,
        uint256 currentBalance
    ) {
        return (
            bridgeCount[user],
            totalBridged[user],
            bonusEarned[user],
            balanceOf(user)
        );
    }
    
    /**
     * @dev Get global stats
     */
    function getGlobalStats() external view returns (
        uint256 bridgers,
        uint256 totalSupplyAmount,
        bool earlyAdopterActive
    ) {
        return (
            totalBridgers,
            totalSupply(),
            totalBridgers < EARLY_ADOPTER_LIMIT
        );
    }
}
