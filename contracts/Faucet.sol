// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title THRYX Faucet
 * @notice Gives new users free ETH to get started on THRYX
 * @dev Simple faucet with rate limiting and amount caps
 */
contract Faucet is Ownable {
    // Faucet settings
    uint256 public dripAmount = 0.01 ether;  // Amount per claim
    uint256 public cooldownTime = 1 hours;    // Time between claims
    uint256 public maxClaims = 3;             // Max claims per wallet
    
    // User tracking
    mapping(address => uint256) public lastClaimTime;
    mapping(address => uint256) public claimCount;
    mapping(address => bool) public hasClaimedWelcome;
    
    // Stats
    uint256 public totalDrips;
    uint256 public totalUsers;
    uint256 public totalEthDripped;
    
    // Events
    event Drip(address indexed user, uint256 amount, uint256 claimNumber);
    event WelcomeBonus(address indexed user, uint256 amount);
    event FaucetFunded(address indexed funder, uint256 amount);
    event SettingsUpdated(uint256 dripAmount, uint256 cooldownTime, uint256 maxClaims);
    
    constructor() Ownable(msg.sender) {}
    
    /**
     * @notice Claim free ETH from the faucet
     */
    function drip() external {
        require(address(this).balance >= dripAmount, "Faucet empty");
        require(claimCount[msg.sender] < maxClaims, "Max claims reached");
        require(
            block.timestamp >= lastClaimTime[msg.sender] + cooldownTime,
            "Cooldown not finished"
        );
        
        // Update tracking
        if (claimCount[msg.sender] == 0) {
            totalUsers++;
        }
        
        claimCount[msg.sender]++;
        lastClaimTime[msg.sender] = block.timestamp;
        totalDrips++;
        totalEthDripped += dripAmount;
        
        // Send ETH
        (bool success, ) = payable(msg.sender).call{value: dripAmount}("");
        require(success, "Transfer failed");
        
        emit Drip(msg.sender, dripAmount, claimCount[msg.sender]);
    }
    
    /**
     * @notice First-time welcome bonus (slightly larger, one-time)
     */
    function claimWelcomeBonus() external {
        require(!hasClaimedWelcome[msg.sender], "Already claimed welcome bonus");
        uint256 welcomeAmount = dripAmount * 2; // 2x normal drip
        require(address(this).balance >= welcomeAmount, "Faucet empty");
        
        hasClaimedWelcome[msg.sender] = true;
        
        if (claimCount[msg.sender] == 0) {
            totalUsers++;
        }
        
        totalDrips++;
        totalEthDripped += welcomeAmount;
        
        (bool success, ) = payable(msg.sender).call{value: welcomeAmount}("");
        require(success, "Transfer failed");
        
        emit WelcomeBonus(msg.sender, welcomeAmount);
    }
    
    /**
     * @notice Check if user can claim
     */
    function canClaim(address user) external view returns (bool canDrip, bool canWelcome, uint256 nextClaimTime, uint256 claimsLeft) {
        canDrip = claimCount[user] < maxClaims && 
                  block.timestamp >= lastClaimTime[user] + cooldownTime &&
                  address(this).balance >= dripAmount;
        canWelcome = !hasClaimedWelcome[user] && address(this).balance >= dripAmount * 2;
        nextClaimTime = lastClaimTime[user] + cooldownTime;
        claimsLeft = maxClaims > claimCount[user] ? maxClaims - claimCount[user] : 0;
    }
    
    /**
     * @notice Get faucet stats
     */
    function getStats() external view returns (
        uint256 balance,
        uint256 drips,
        uint256 users,
        uint256 totalDripped,
        uint256 currentDripAmount
    ) {
        return (
            address(this).balance,
            totalDrips,
            totalUsers,
            totalEthDripped,
            dripAmount
        );
    }
    
    /**
     * @notice Owner can update settings
     */
    function updateSettings(uint256 _dripAmount, uint256 _cooldownTime, uint256 _maxClaims) external onlyOwner {
        dripAmount = _dripAmount;
        cooldownTime = _cooldownTime;
        maxClaims = _maxClaims;
        emit SettingsUpdated(_dripAmount, _cooldownTime, _maxClaims);
    }
    
    /**
     * @notice Owner can withdraw excess funds
     */
    function withdraw(uint256 amount) external onlyOwner {
        (bool success, ) = payable(owner()).call{value: amount}("");
        require(success, "Withdraw failed");
    }
    
    /**
     * @notice Accept ETH to fund the faucet
     */
    receive() external payable {
        emit FaucetFunded(msg.sender, msg.value);
    }
}
