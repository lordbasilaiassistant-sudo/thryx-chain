// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "./AgentRegistry.sol";

/**
 * @title IntentMempool
 * @dev Intent-based execution system where agents submit goals and solvers fulfill them
 */
contract IntentMempool is Ownable {
    AgentRegistry public registry;
    IERC20 public usdc;
    
    enum IntentStatus { Pending, Fulfilled, Cancelled, Expired }
    
    struct Intent {
        uint256 id;
        address creator;
        bytes32 goal;
        bytes constraints;
        uint256 maxCost;
        uint256 deadline;
        IntentStatus status;
        address solver;
        bytes solution;
        uint256 actualCost;
    }
    
    uint256 public nextIntentId = 1;
    mapping(uint256 => Intent) public intents;
    uint256[] public pendingIntentIds;
    
    uint256 public constant MIN_DEADLINE = 1 minutes;
    uint256 public constant MAX_DEADLINE = 1 hours;
    
    // Solver rewards
    uint256 public solverRewardPercent = 80; // 80% of maxCost goes to solver

    event IntentSubmitted(uint256 indexed id, address indexed creator, bytes32 goal, uint256 maxCost);
    event IntentFulfilled(uint256 indexed id, address indexed solver, uint256 cost);
    event IntentCancelled(uint256 indexed id);
    event IntentExpired(uint256 indexed id);

    constructor(address _registry, address _usdc) Ownable(msg.sender) {
        registry = AgentRegistry(_registry);
        usdc = IERC20(_usdc);
    }

    /**
     * @dev Submit a new intent
     */
    function submitIntent(
        bytes32 goal,
        bytes calldata constraints,
        uint256 maxCost,
        uint256 deadlineSeconds
    ) external returns (uint256 intentId) {
        require(registry.validateAgent(msg.sender), "Not a valid agent");
        require(maxCost > 0, "Max cost must be > 0");
        require(deadlineSeconds >= MIN_DEADLINE && deadlineSeconds <= MAX_DEADLINE, "Invalid deadline");
        
        // Lock USDC for max cost
        require(usdc.transferFrom(msg.sender, address(this), maxCost), "Transfer failed");
        
        intentId = nextIntentId++;
        
        intents[intentId] = Intent({
            id: intentId,
            creator: msg.sender,
            goal: goal,
            constraints: constraints,
            maxCost: maxCost,
            deadline: block.timestamp + deadlineSeconds,
            status: IntentStatus.Pending,
            solver: address(0),
            solution: "",
            actualCost: 0
        });
        
        pendingIntentIds.push(intentId);
        
        emit IntentSubmitted(intentId, msg.sender, goal, maxCost);
    }

    /**
     * @dev Fulfill an intent (solvers call this)
     */
    function fulfillIntent(
        uint256 intentId,
        bytes calldata solution,
        uint256 actualCost
    ) external {
        Intent storage intent = intents[intentId];
        
        require(intent.status == IntentStatus.Pending, "Intent not pending");
        require(block.timestamp <= intent.deadline, "Intent expired");
        require(actualCost <= intent.maxCost, "Cost exceeds max");
        require(registry.validateAgent(msg.sender), "Not a valid agent");
        
        intent.status = IntentStatus.Fulfilled;
        intent.solver = msg.sender;
        intent.solution = solution;
        intent.actualCost = actualCost;
        
        // Pay solver
        uint256 solverReward = (actualCost * solverRewardPercent) / 100;
        require(usdc.transfer(msg.sender, solverReward), "Solver payment failed");
        
        // Refund excess to creator
        uint256 refund = intent.maxCost - actualCost;
        if (refund > 0) {
            require(usdc.transfer(intent.creator, refund), "Refund failed");
        }
        
        _removePendingIntent(intentId);
        
        emit IntentFulfilled(intentId, msg.sender, actualCost);
    }

    /**
     * @dev Cancel an intent (only creator)
     */
    function cancelIntent(uint256 intentId) external {
        Intent storage intent = intents[intentId];
        
        require(intent.creator == msg.sender, "Not intent creator");
        require(intent.status == IntentStatus.Pending, "Intent not pending");
        
        intent.status = IntentStatus.Cancelled;
        
        // Refund locked USDC
        require(usdc.transfer(msg.sender, intent.maxCost), "Refund failed");
        
        _removePendingIntent(intentId);
        
        emit IntentCancelled(intentId);
    }

    /**
     * @dev Clean up expired intents (anyone can call)
     */
    function cleanupExpired() external {
        uint256[] memory toRemove = new uint256[](pendingIntentIds.length);
        uint256 removeCount = 0;
        
        for (uint256 i = 0; i < pendingIntentIds.length; i++) {
            uint256 id = pendingIntentIds[i];
            Intent storage intent = intents[id];
            
            if (intent.status == IntentStatus.Pending && block.timestamp > intent.deadline) {
                intent.status = IntentStatus.Expired;
                
                // Refund locked USDC
                usdc.transfer(intent.creator, intent.maxCost);
                
                toRemove[removeCount++] = id;
                emit IntentExpired(id);
            }
        }
        
        // Remove expired intents from pending list
        for (uint256 i = 0; i < removeCount; i++) {
            _removePendingIntent(toRemove[i]);
        }
    }

    /**
     * @dev Get pending intents
     */
    function getPendingIntents() external view returns (uint256[] memory) {
        return pendingIntentIds;
    }

    /**
     * @dev Get intent details
     */
    function getIntent(uint256 intentId) external view returns (Intent memory) {
        return intents[intentId];
    }

    /**
     * @dev Remove intent from pending list
     */
    function _removePendingIntent(uint256 intentId) internal {
        for (uint256 i = 0; i < pendingIntentIds.length; i++) {
            if (pendingIntentIds[i] == intentId) {
                pendingIntentIds[i] = pendingIntentIds[pendingIntentIds.length - 1];
                pendingIntentIds.pop();
                break;
            }
        }
    }
}
