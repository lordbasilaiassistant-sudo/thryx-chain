// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title AgentRegistry
 * @dev Registry for AI agent identities, permissions, and budgets
 */
contract AgentRegistry is Ownable {
    struct Agent {
        address owner;
        uint256 dailyBudget;
        uint256 spentToday;
        uint256 lastResetTimestamp;
        bytes32 permissions;
        bool isActive;
        string metadata;
    }

    mapping(address => Agent) public agents;
    address[] public agentList;
    
    // Permission flags
    bytes32 public constant PERM_TRADE = keccak256("TRADE");
    bytes32 public constant PERM_ORACLE = keccak256("ORACLE");
    bytes32 public constant PERM_GOVERNANCE = keccak256("GOVERNANCE");
    bytes32 public constant PERM_LIQUIDITY = keccak256("LIQUIDITY");
    bytes32 public constant PERM_MONITOR = keccak256("MONITOR");

    event AgentRegistered(address indexed agent, address indexed owner, uint256 dailyBudget);
    event AgentDeactivated(address indexed agent);
    event AgentBudgetUpdated(address indexed agent, uint256 newBudget);
    event AgentSpent(address indexed agent, uint256 amount);

    constructor() Ownable(msg.sender) {}

    /**
     * @dev Register a new AI agent
     */
    function registerAgent(
        address agentAddress,
        uint256 dailyBudget,
        bytes32 permissions,
        string calldata metadata
    ) external {
        require(agents[agentAddress].owner == address(0), "Agent already registered");
        
        agents[agentAddress] = Agent({
            owner: msg.sender,
            dailyBudget: dailyBudget,
            spentToday: 0,
            lastResetTimestamp: block.timestamp,
            permissions: permissions,
            isActive: true,
            metadata: metadata
        });
        
        agentList.push(agentAddress);
        emit AgentRegistered(agentAddress, msg.sender, dailyBudget);
    }

    /**
     * @dev Validate if an agent can spend a given amount
     */
    function validateAgent(address agentAddress) external view returns (bool) {
        Agent storage agent = agents[agentAddress];
        return agent.isActive && agent.owner != address(0);
    }

    /**
     * @dev Check if agent has specific permission
     */
    function hasPermission(address agentAddress, bytes32 permission) external view returns (bool) {
        return agents[agentAddress].permissions == permission || 
               agents[agentAddress].permissions == keccak256("ALL");
    }

    /**
     * @dev Record spending by an agent (called by gas payment contract)
     */
    function recordSpending(address agentAddress, uint256 amount) external {
        Agent storage agent = agents[agentAddress];
        require(agent.isActive, "Agent not active");
        
        // Reset daily spending if new day
        if (block.timestamp >= agent.lastResetTimestamp + 1 days) {
            agent.spentToday = 0;
            agent.lastResetTimestamp = block.timestamp;
        }
        
        require(agent.spentToday + amount <= agent.dailyBudget, "Daily budget exceeded");
        agent.spentToday += amount;
        emit AgentSpent(agentAddress, amount);
    }

    /**
     * @dev Get remaining daily budget for an agent
     */
    function getRemainingBudget(address agentAddress) external view returns (uint256) {
        Agent storage agent = agents[agentAddress];
        if (block.timestamp >= agent.lastResetTimestamp + 1 days) {
            return agent.dailyBudget;
        }
        return agent.dailyBudget - agent.spentToday;
    }

    /**
     * @dev Deactivate an agent (only owner)
     */
    function deactivateAgent(address agentAddress) external {
        require(agents[agentAddress].owner == msg.sender, "Not agent owner");
        agents[agentAddress].isActive = false;
        emit AgentDeactivated(agentAddress);
    }

    /**
     * @dev Update agent's daily budget (only owner)
     */
    function updateBudget(address agentAddress, uint256 newBudget) external {
        require(agents[agentAddress].owner == msg.sender, "Not agent owner");
        agents[agentAddress].dailyBudget = newBudget;
        emit AgentBudgetUpdated(agentAddress, newBudget);
    }

    /**
     * @dev Get total number of registered agents
     */
    function getAgentCount() external view returns (uint256) {
        return agentList.length;
    }

    /**
     * @dev Get all active agents
     */
    function getActiveAgents() external view returns (address[] memory) {
        uint256 activeCount = 0;
        for (uint256 i = 0; i < agentList.length; i++) {
            if (agents[agentList[i]].isActive) {
                activeCount++;
            }
        }
        
        address[] memory activeAgents = new address[](activeCount);
        uint256 index = 0;
        for (uint256 i = 0; i < agentList.length; i++) {
            if (agents[agentList[i]].isActive) {
                activeAgents[index] = agentList[i];
                index++;
            }
        }
        return activeAgents;
    }
}
