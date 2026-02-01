// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

/**
 * @title THRYX Campaign
 * @notice Manages time-limited promotional events and airdrops
 * @dev Supports ETH and ERC20 reward pools
 */
contract Campaign is Ownable, ReentrancyGuard {
    struct CampaignData {
        uint256 id;
        string name;
        string description;
        uint256 startTime;
        uint256 endTime;
        uint256 totalRewards;
        uint256 claimedRewards;
        uint256 participantsCount;
        uint256 maxParticipants;
        uint256 rewardPerParticipant;
        bool isEth;
        address rewardToken;
        bool active;
        mapping(address => bool) hasParticipated;
        mapping(address => uint256) rewards;
    }
    
    // Storage
    uint256 public campaignCount;
    mapping(uint256 => CampaignData) public campaigns;
    
    // Agent authorization
    mapping(address => bool) public authorizedAgents;
    
    // Events
    event CampaignCreated(uint256 indexed id, string name, uint256 totalRewards, uint256 startTime, uint256 endTime);
    event Participated(uint256 indexed campaignId, address indexed participant, uint256 reward);
    event RewardClaimed(uint256 indexed campaignId, address indexed participant, uint256 amount);
    event CampaignEnded(uint256 indexed id, uint256 totalClaimed, uint256 participantsCount);
    event AgentAuthorized(address indexed agent, bool authorized);
    
    constructor() Ownable(msg.sender) {}
    
    modifier onlyAuthorized() {
        require(msg.sender == owner() || authorizedAgents[msg.sender], "Not authorized");
        _;
    }
    
    /**
     * @notice Create a new ETH campaign
     * @param name Campaign name
     * @param description Campaign description
     * @param startTime When campaign starts
     * @param duration How long campaign runs
     * @param maxParticipants Maximum participants (0 for unlimited)
     */
    function createEthCampaign(
        string calldata name,
        string calldata description,
        uint256 startTime,
        uint256 duration,
        uint256 maxParticipants
    ) external payable onlyAuthorized returns (uint256) {
        require(msg.value > 0, "No rewards provided");
        require(duration > 0, "Duration must be > 0");
        require(startTime >= block.timestamp, "Start must be in future");
        
        campaignCount++;
        CampaignData storage campaign = campaigns[campaignCount];
        
        campaign.id = campaignCount;
        campaign.name = name;
        campaign.description = description;
        campaign.startTime = startTime;
        campaign.endTime = startTime + duration;
        campaign.totalRewards = msg.value;
        campaign.maxParticipants = maxParticipants;
        campaign.isEth = true;
        campaign.active = true;
        
        // Calculate reward per participant if maxParticipants is set
        if (maxParticipants > 0) {
            campaign.rewardPerParticipant = msg.value / maxParticipants;
        }
        
        emit CampaignCreated(campaignCount, name, msg.value, startTime, startTime + duration);
        
        return campaignCount;
    }
    
    /**
     * @notice Record participation and allocate reward
     * @param campaignId Campaign to participate in
     * @param participant Address of participant
     * @param rewardAmount Custom reward amount (0 for default)
     */
    function recordParticipation(
        uint256 campaignId,
        address participant,
        uint256 rewardAmount
    ) external onlyAuthorized {
        CampaignData storage campaign = campaigns[campaignId];
        
        require(campaign.active, "Campaign not active");
        require(block.timestamp >= campaign.startTime, "Campaign not started");
        require(block.timestamp <= campaign.endTime, "Campaign ended");
        require(!campaign.hasParticipated[participant], "Already participated");
        
        if (campaign.maxParticipants > 0) {
            require(campaign.participantsCount < campaign.maxParticipants, "Max participants reached");
        }
        
        // Calculate reward
        uint256 reward = rewardAmount > 0 ? rewardAmount : campaign.rewardPerParticipant;
        if (reward == 0) {
            // Dynamic reward based on remaining pool
            uint256 remaining = campaign.totalRewards - campaign.claimedRewards;
            reward = remaining / 100; // 1% of remaining
            if (reward > 0.01 ether) reward = 0.01 ether; // Cap at 0.01 ETH
        }
        
        require(campaign.claimedRewards + reward <= campaign.totalRewards, "Insufficient rewards");
        
        campaign.hasParticipated[participant] = true;
        campaign.rewards[participant] = reward;
        campaign.participantsCount++;
        campaign.claimedRewards += reward;
        
        // Send reward immediately
        if (campaign.isEth && reward > 0) {
            (bool success, ) = payable(participant).call{value: reward}("");
            require(success, "Reward transfer failed");
        }
        
        emit Participated(campaignId, participant, reward);
    }
    
    /**
     * @notice End a campaign and reclaim unused funds
     * @param campaignId Campaign to end
     */
    function endCampaign(uint256 campaignId) external onlyAuthorized {
        CampaignData storage campaign = campaigns[campaignId];
        require(campaign.active, "Already ended");
        
        campaign.active = false;
        
        // Return unused funds to owner
        uint256 unused = campaign.totalRewards - campaign.claimedRewards;
        if (unused > 0 && campaign.isEth) {
            (bool success, ) = payable(owner()).call{value: unused}("");
            require(success, "Refund failed");
        }
        
        emit CampaignEnded(campaignId, campaign.claimedRewards, campaign.participantsCount);
    }
    
    /**
     * @notice Check if address can participate
     */
    function canParticipate(uint256 campaignId, address participant) external view returns (bool) {
        CampaignData storage campaign = campaigns[campaignId];
        
        if (!campaign.active) return false;
        if (block.timestamp < campaign.startTime) return false;
        if (block.timestamp > campaign.endTime) return false;
        if (campaign.hasParticipated[participant]) return false;
        if (campaign.maxParticipants > 0 && campaign.participantsCount >= campaign.maxParticipants) return false;
        if (campaign.claimedRewards >= campaign.totalRewards) return false;
        
        return true;
    }
    
    /**
     * @notice Get campaign details
     */
    function getCampaign(uint256 campaignId) external view returns (
        string memory name,
        string memory description,
        uint256 startTime,
        uint256 endTime,
        uint256 totalRewards,
        uint256 claimedRewards,
        uint256 participantsCount,
        uint256 maxParticipants,
        bool active
    ) {
        CampaignData storage campaign = campaigns[campaignId];
        return (
            campaign.name,
            campaign.description,
            campaign.startTime,
            campaign.endTime,
            campaign.totalRewards,
            campaign.claimedRewards,
            campaign.participantsCount,
            campaign.maxParticipants,
            campaign.active
        );
    }
    
    /**
     * @notice Get active campaigns
     */
    function getActiveCampaigns() external view returns (uint256[] memory) {
        uint256 activeCount = 0;
        for (uint256 i = 1; i <= campaignCount; i++) {
            if (campaigns[i].active && block.timestamp <= campaigns[i].endTime) {
                activeCount++;
            }
        }
        
        uint256[] memory result = new uint256[](activeCount);
        uint256 index = 0;
        for (uint256 i = 1; i <= campaignCount; i++) {
            if (campaigns[i].active && block.timestamp <= campaigns[i].endTime) {
                result[index] = i;
                index++;
            }
        }
        
        return result;
    }
    
    /**
     * @notice Authorize an agent to manage campaigns
     */
    function authorizeAgent(address agent, bool authorized) external onlyOwner {
        authorizedAgents[agent] = authorized;
        emit AgentAuthorized(agent, authorized);
    }
    
    // Accept ETH for campaign funding
    receive() external payable {}
}
