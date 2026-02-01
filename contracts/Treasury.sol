// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

/**
 * @title THRYX Treasury
 * @notice Collects protocol revenue and distributes to stakers
 * @dev Receives fees from AMM, bridge, intent system
 */
contract Treasury is Ownable, ReentrancyGuard {
    // Distribution percentages (basis points, 10000 = 100%)
    uint256 public stakerShare = 7000;      // 70% to stakers
    uint256 public operationalShare = 2000; // 20% operational
    uint256 public developmentShare = 1000; // 10% development
    
    // Addresses
    address public stakingContract;
    address public operationalWallet;
    address public developmentWallet;
    
    // Distribution tracking
    uint256 public lastDistribution;
    uint256 public distributionInterval = 7 days;
    uint256 public minDistributionAmount = 0.1 ether;
    
    // Stats
    uint256 public totalDistributed;
    uint256 public distributionCount;
    uint256 public totalEthReceived;
    
    // Events
    event RevenueReceived(address indexed from, uint256 amount, string source);
    event DistributionExecuted(uint256 stakerAmount, uint256 operationalAmount, uint256 developmentAmount);
    event SharesUpdated(uint256 staker, uint256 operational, uint256 development);
    event WalletsUpdated(address staking, address operational, address development);
    
    constructor(
        address _operationalWallet,
        address _developmentWallet
    ) Ownable(msg.sender) {
        operationalWallet = _operationalWallet;
        developmentWallet = _developmentWallet;
        lastDistribution = block.timestamp;
    }
    
    /**
     * @notice Receive ETH with source tracking
     * @param source Description of revenue source
     */
    function receiveRevenue(string calldata source) external payable {
        require(msg.value > 0, "No value sent");
        totalEthReceived += msg.value;
        emit RevenueReceived(msg.sender, msg.value, source);
    }
    
    /**
     * @notice Check if distribution is ready
     */
    function canDistribute() public view returns (bool) {
        return block.timestamp >= lastDistribution + distributionInterval &&
               address(this).balance >= minDistributionAmount;
    }
    
    /**
     * @notice Execute weekly distribution
     */
    function distribute() external nonReentrant {
        require(canDistribute(), "Distribution not ready");
        
        uint256 balance = address(this).balance;
        require(balance > 0, "No balance to distribute");
        
        // Calculate shares
        uint256 stakerAmount = (balance * stakerShare) / 10000;
        uint256 operationalAmount = (balance * operationalShare) / 10000;
        uint256 developmentAmount = balance - stakerAmount - operationalAmount;
        
        // Update tracking
        lastDistribution = block.timestamp;
        totalDistributed += balance;
        distributionCount++;
        
        // Send to wallets
        if (stakingContract != address(0) && stakerAmount > 0) {
            (bool success1, ) = payable(stakingContract).call{value: stakerAmount}("");
            require(success1, "Staker transfer failed");
        } else if (stakerAmount > 0) {
            // If no staking contract, send to operational
            operationalAmount += stakerAmount;
            stakerAmount = 0;
        }
        
        if (operationalWallet != address(0) && operationalAmount > 0) {
            (bool success2, ) = payable(operationalWallet).call{value: operationalAmount}("");
            require(success2, "Operational transfer failed");
        }
        
        if (developmentWallet != address(0) && developmentAmount > 0) {
            (bool success3, ) = payable(developmentWallet).call{value: developmentAmount}("");
            require(success3, "Development transfer failed");
        }
        
        emit DistributionExecuted(stakerAmount, operationalAmount, developmentAmount);
    }
    
    /**
     * @notice Get treasury stats
     */
    function getStats() external view returns (
        uint256 balance,
        uint256 _totalReceived,
        uint256 _totalDistributed,
        uint256 _distributionCount,
        uint256 nextDistribution,
        bool _canDistribute
    ) {
        return (
            address(this).balance,
            totalEthReceived,
            totalDistributed,
            distributionCount,
            lastDistribution + distributionInterval,
            canDistribute()
        );
    }
    
    /**
     * @notice Update distribution shares (owner only)
     * @param _staker Staker share in basis points
     * @param _operational Operational share in basis points
     * @param _development Development share in basis points
     */
    function updateShares(
        uint256 _staker,
        uint256 _operational,
        uint256 _development
    ) external onlyOwner {
        require(_staker + _operational + _development == 10000, "Shares must equal 100%");
        stakerShare = _staker;
        operationalShare = _operational;
        developmentShare = _development;
        emit SharesUpdated(_staker, _operational, _development);
    }
    
    /**
     * @notice Update wallet addresses (owner only)
     */
    function updateWallets(
        address _staking,
        address _operational,
        address _development
    ) external onlyOwner {
        stakingContract = _staking;
        operationalWallet = _operational;
        developmentWallet = _development;
        emit WalletsUpdated(_staking, _operational, _development);
    }
    
    /**
     * @notice Update distribution interval (owner only)
     */
    function setDistributionInterval(uint256 _interval) external onlyOwner {
        require(_interval >= 1 days, "Interval too short");
        distributionInterval = _interval;
    }
    
    /**
     * @notice Emergency withdraw (owner only)
     */
    function emergencyWithdraw(address to, uint256 amount) external onlyOwner {
        require(to != address(0), "Invalid address");
        (bool success, ) = payable(to).call{value: amount}("");
        require(success, "Transfer failed");
    }
    
    // Accept ETH
    receive() external payable {
        totalEthReceived += msg.value;
        emit RevenueReceived(msg.sender, msg.value, "direct");
    }
}
