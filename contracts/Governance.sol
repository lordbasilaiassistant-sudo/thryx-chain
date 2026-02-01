// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

interface IThryxToken {
    function getVotingPower(address account) external view returns (uint256);
    function totalStaked() external view returns (uint256);
}

/**
 * @title THRYX Governance
 * @notice On-chain governance for protocol parameter changes
 * @dev Proposal creation, voting, and execution
 */
contract Governance is Ownable, ReentrancyGuard {
    // Governance parameters
    uint256 public proposalThreshold = 1000 * 10**18; // 1000 THRYX to propose
    uint256 public votingPeriod = 3 days;
    uint256 public executionDelay = 1 days;
    uint256 public quorumPercentage = 1000; // 10% in basis points
    
    // Token contract
    IThryxToken public thryxToken;
    
    // Proposal states
    enum ProposalState { Pending, Active, Succeeded, Defeated, Executed, Expired }
    
    struct Proposal {
        uint256 id;
        address proposer;
        string description;
        address target;
        bytes callData;
        uint256 forVotes;
        uint256 againstVotes;
        uint256 startTime;
        uint256 endTime;
        bool executed;
        mapping(address => bool) hasVoted;
    }
    
    // Storage
    uint256 public proposalCount;
    mapping(uint256 => Proposal) public proposals;
    
    // Events
    event ProposalCreated(uint256 indexed id, address indexed proposer, string description, address target);
    event VoteCast(uint256 indexed proposalId, address indexed voter, bool support, uint256 weight);
    event ProposalExecuted(uint256 indexed id);
    event ProposalCancelled(uint256 indexed id);
    event ParameterUpdated(string parameter, uint256 oldValue, uint256 newValue);
    
    constructor(address _thryxToken) Ownable(msg.sender) {
        thryxToken = IThryxToken(_thryxToken);
    }
    
    /**
     * @notice Create a new proposal
     * @param description Human-readable description
     * @param target Contract to call if passed
     * @param callData Encoded function call
     */
    function propose(
        string calldata description,
        address target,
        bytes calldata callData
    ) external returns (uint256) {
        require(
            thryxToken.getVotingPower(msg.sender) >= proposalThreshold,
            "Below proposal threshold"
        );
        
        proposalCount++;
        Proposal storage proposal = proposals[proposalCount];
        proposal.id = proposalCount;
        proposal.proposer = msg.sender;
        proposal.description = description;
        proposal.target = target;
        proposal.callData = callData;
        proposal.startTime = block.timestamp;
        proposal.endTime = block.timestamp + votingPeriod;
        
        emit ProposalCreated(proposalCount, msg.sender, description, target);
        
        return proposalCount;
    }
    
    /**
     * @notice Cast a vote on a proposal
     * @param proposalId Proposal to vote on
     * @param support True for yes, false for no
     */
    function vote(uint256 proposalId, bool support) external {
        Proposal storage proposal = proposals[proposalId];
        require(proposal.id != 0, "Proposal does not exist");
        require(block.timestamp >= proposal.startTime, "Voting not started");
        require(block.timestamp <= proposal.endTime, "Voting ended");
        require(!proposal.hasVoted[msg.sender], "Already voted");
        
        uint256 weight = thryxToken.getVotingPower(msg.sender);
        require(weight > 0, "No voting power");
        
        proposal.hasVoted[msg.sender] = true;
        
        if (support) {
            proposal.forVotes += weight;
        } else {
            proposal.againstVotes += weight;
        }
        
        emit VoteCast(proposalId, msg.sender, support, weight);
    }
    
    /**
     * @notice Execute a passed proposal
     * @param proposalId Proposal to execute
     */
    function execute(uint256 proposalId) external nonReentrant {
        Proposal storage proposal = proposals[proposalId];
        require(getProposalState(proposalId) == ProposalState.Succeeded, "Cannot execute");
        require(block.timestamp >= proposal.endTime + executionDelay, "Execution delay not met");
        
        proposal.executed = true;
        
        // Execute the proposal
        (bool success, ) = proposal.target.call(proposal.callData);
        require(success, "Execution failed");
        
        emit ProposalExecuted(proposalId);
    }
    
    /**
     * @notice Get the current state of a proposal
     * @param proposalId Proposal to check
     */
    function getProposalState(uint256 proposalId) public view returns (ProposalState) {
        Proposal storage proposal = proposals[proposalId];
        
        if (proposal.id == 0) {
            revert("Proposal does not exist");
        }
        
        if (proposal.executed) {
            return ProposalState.Executed;
        }
        
        if (block.timestamp < proposal.startTime) {
            return ProposalState.Pending;
        }
        
        if (block.timestamp <= proposal.endTime) {
            return ProposalState.Active;
        }
        
        // Check if expired (30 days after end)
        if (block.timestamp > proposal.endTime + 30 days) {
            return ProposalState.Expired;
        }
        
        // Check quorum
        uint256 totalStaked = thryxToken.totalStaked();
        uint256 quorum = (totalStaked * quorumPercentage) / 10000;
        uint256 totalVotes = proposal.forVotes + proposal.againstVotes;
        
        if (totalVotes < quorum) {
            return ProposalState.Defeated;
        }
        
        if (proposal.forVotes > proposal.againstVotes) {
            return ProposalState.Succeeded;
        }
        
        return ProposalState.Defeated;
    }
    
    /**
     * @notice Get proposal details
     * @param proposalId Proposal to query
     */
    function getProposal(uint256 proposalId) external view returns (
        address proposer,
        string memory description,
        address target,
        uint256 forVotes,
        uint256 againstVotes,
        uint256 startTime,
        uint256 endTime,
        bool executed,
        ProposalState state
    ) {
        Proposal storage proposal = proposals[proposalId];
        return (
            proposal.proposer,
            proposal.description,
            proposal.target,
            proposal.forVotes,
            proposal.againstVotes,
            proposal.startTime,
            proposal.endTime,
            proposal.executed,
            getProposalState(proposalId)
        );
    }
    
    /**
     * @notice Check if an address has voted on a proposal
     */
    function hasVoted(uint256 proposalId, address voter) external view returns (bool) {
        return proposals[proposalId].hasVoted[voter];
    }
    
    // Admin functions
    
    function setProposalThreshold(uint256 _threshold) external onlyOwner {
        emit ParameterUpdated("proposalThreshold", proposalThreshold, _threshold);
        proposalThreshold = _threshold;
    }
    
    function setVotingPeriod(uint256 _period) external onlyOwner {
        require(_period >= 1 days, "Period too short");
        emit ParameterUpdated("votingPeriod", votingPeriod, _period);
        votingPeriod = _period;
    }
    
    function setQuorum(uint256 _quorum) external onlyOwner {
        require(_quorum <= 5000, "Quorum too high"); // Max 50%
        emit ParameterUpdated("quorumPercentage", quorumPercentage, _quorum);
        quorumPercentage = _quorum;
    }
    
    function setThryxToken(address _token) external onlyOwner {
        thryxToken = IThryxToken(_token);
    }
}
