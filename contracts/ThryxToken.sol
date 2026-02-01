// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Permit.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/**
 * @title THRYX Governance Token
 * @notice The native governance token of the THRYX AI-native blockchain
 * @dev ERC20 with staking, delegation, and voting power features
 */
contract ThryxToken is ERC20, ERC20Permit, Ownable, ReentrancyGuard {
    // Total supply: 1 billion THRYX
    uint256 public constant MAX_SUPPLY = 1_000_000_000 * 10**18;
    
    // Staking
    mapping(address => uint256) public stakedBalance;
    mapping(address => uint256) public stakeTimestamp;
    mapping(address => address) public delegates;
    mapping(address => uint256) public delegatedVotes;
    
    // Staking rewards
    uint256 public rewardRate = 100; // 1% per epoch (100 basis points)
    uint256 public epochDuration = 7 days;
    mapping(address => uint256) public lastRewardClaim;
    
    // Stats
    uint256 public totalStaked;
    uint256 public totalDelegated;
    uint256 public stakersCount;
    
    // Events
    event Staked(address indexed user, uint256 amount);
    event Unstaked(address indexed user, uint256 amount);
    event DelegateChanged(address indexed delegator, address indexed fromDelegate, address indexed toDelegate);
    event RewardsClaimed(address indexed user, uint256 amount);
    event RewardRateUpdated(uint256 newRate);
    
    constructor() ERC20("THRYX", "THRYX") ERC20Permit("THRYX") Ownable(msg.sender) {
        // Initial distribution:
        // 40% - Treasury/Protocol (400M)
        // 30% - Staking Rewards Pool (300M)
        // 20% - Agent Operations Fund (200M)
        // 10% - Initial Liquidity (100M)
        
        _mint(msg.sender, MAX_SUPPLY);
    }
    
    /**
     * @notice Stake THRYX tokens to gain voting power
     * @param amount Amount of THRYX to stake
     */
    function stake(uint256 amount) external nonReentrant {
        require(amount > 0, "Cannot stake 0");
        require(balanceOf(msg.sender) >= amount, "Insufficient balance");
        
        // Claim any pending rewards first
        if (stakedBalance[msg.sender] > 0) {
            _claimRewards(msg.sender);
        }
        
        // Transfer tokens to contract
        _transfer(msg.sender, address(this), amount);
        
        // Update staking state
        if (stakedBalance[msg.sender] == 0) {
            stakersCount++;
        }
        stakedBalance[msg.sender] += amount;
        stakeTimestamp[msg.sender] = block.timestamp;
        totalStaked += amount;
        
        // Update voting power
        _updateVotingPower(msg.sender, amount, true);
        
        emit Staked(msg.sender, amount);
    }
    
    /**
     * @notice Unstake THRYX tokens
     * @param amount Amount of THRYX to unstake
     */
    function unstake(uint256 amount) external nonReentrant {
        require(amount > 0, "Cannot unstake 0");
        require(stakedBalance[msg.sender] >= amount, "Insufficient staked balance");
        
        // Claim any pending rewards first
        _claimRewards(msg.sender);
        
        // Update staking state
        stakedBalance[msg.sender] -= amount;
        if (stakedBalance[msg.sender] == 0) {
            stakersCount--;
        }
        totalStaked -= amount;
        
        // Update voting power
        _updateVotingPower(msg.sender, amount, false);
        
        // Transfer tokens back to user
        _transfer(address(this), msg.sender, amount);
        
        emit Unstaked(msg.sender, amount);
    }
    
    /**
     * @notice Delegate voting power to another address
     * @param delegatee Address to delegate to
     */
    function delegate(address delegatee) external {
        require(delegatee != address(0), "Cannot delegate to zero address");
        
        address currentDelegate = delegates[msg.sender];
        uint256 voterStake = stakedBalance[msg.sender];
        
        // Remove votes from old delegate
        if (currentDelegate != address(0) && voterStake > 0) {
            delegatedVotes[currentDelegate] -= voterStake;
            totalDelegated -= voterStake;
        }
        
        // Add votes to new delegate
        delegates[msg.sender] = delegatee;
        if (voterStake > 0) {
            delegatedVotes[delegatee] += voterStake;
            totalDelegated += voterStake;
        }
        
        emit DelegateChanged(msg.sender, currentDelegate, delegatee);
    }
    
    /**
     * @notice Claim staking rewards
     */
    function claimRewards() external nonReentrant {
        _claimRewards(msg.sender);
    }
    
    /**
     * @notice Get pending rewards for a user
     * @param user Address to check
     * @return Pending reward amount
     */
    function pendingRewards(address user) public view returns (uint256) {
        if (stakedBalance[user] == 0) return 0;
        
        uint256 lastClaim = lastRewardClaim[user];
        if (lastClaim == 0) lastClaim = stakeTimestamp[user];
        
        uint256 elapsed = block.timestamp - lastClaim;
        uint256 epochs = elapsed / epochDuration;
        
        if (epochs == 0) return 0;
        
        // Simple interest: stake * rate * epochs / 10000
        return (stakedBalance[user] * rewardRate * epochs) / 10000;
    }
    
    /**
     * @notice Get voting power of an address
     * @param account Address to check
     * @return Total voting power (own stake + delegated)
     */
    function getVotingPower(address account) public view returns (uint256) {
        return stakedBalance[account] + delegatedVotes[account];
    }
    
    /**
     * @notice Get staking stats
     */
    function getStakingStats() external view returns (
        uint256 _totalStaked,
        uint256 _stakersCount,
        uint256 _totalDelegated,
        uint256 _rewardRate,
        uint256 _epochDuration
    ) {
        return (totalStaked, stakersCount, totalDelegated, rewardRate, epochDuration);
    }
    
    /**
     * @notice Update reward rate (owner only)
     * @param newRate New reward rate in basis points
     */
    function setRewardRate(uint256 newRate) external onlyOwner {
        require(newRate <= 1000, "Rate too high"); // Max 10%
        rewardRate = newRate;
        emit RewardRateUpdated(newRate);
    }
    
    // Internal functions
    
    function _claimRewards(address user) internal {
        uint256 reward = pendingRewards(user);
        if (reward > 0) {
            lastRewardClaim[user] = block.timestamp;
            
            // Mint rewards if contract has enough balance, otherwise skip
            if (balanceOf(address(this)) >= reward) {
                _transfer(address(this), user, reward);
                emit RewardsClaimed(user, reward);
            }
        }
    }
    
    function _updateVotingPower(address user, uint256 amount, bool isStaking) internal {
        address delegatee = delegates[user];
        if (delegatee != address(0)) {
            if (isStaking) {
                delegatedVotes[delegatee] += amount;
                totalDelegated += amount;
            } else {
                delegatedVotes[delegatee] -= amount;
                totalDelegated -= amount;
            }
        }
    }
}
