// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";
import "./AgentRegistry.sol";

/**
 * @title AgentOracle
 * @dev ENHANCED decentralized price oracle with:
 *      - Minimum 3 submissions for consensus
 *      - Price deviation checks
 *      - Agent reputation scoring
 *      - Emergency pause capability
 */
contract AgentOracle is Ownable, Pausable {
    AgentRegistry public registry;
    
    struct PriceData {
        uint256 price;
        uint256 timestamp;
        address submitter;
    }
    
    struct PriceFeed {
        bytes32 pair;
        uint256 consensusPrice;
        uint256 lastUpdate;
        uint256 submissionCount;
        PriceData[] submissions;
    }
    
    // Agent reputation (tracks accuracy)
    struct AgentReputation {
        uint256 totalSubmissions;
        uint256 accurateSubmissions;  // Within 2% of consensus
        uint256 lastSubmission;
        bool isBanned;
    }
    
    mapping(bytes32 => PriceFeed) public priceFeeds;
    mapping(address => AgentReputation) public agentReputations;
    bytes32[] public activePairs;
    
    // ENHANCED: Increased minimum submissions for stronger consensus
    uint256 public constant MIN_SUBMISSIONS = 3;
    uint256 public constant MAX_PRICE_AGE = 5 minutes;
    uint256 public constant SUBMISSION_WINDOW = 30 seconds;
    
    // Price deviation limits (in basis points, 100 = 1%)
    uint256 public constant MAX_DEVIATION_BPS = 1000;  // 10% max deviation from previous price
    uint256 public constant ACCURACY_THRESHOLD_BPS = 200;  // 2% accuracy threshold
    
    // Reputation thresholds
    uint256 public constant MIN_REPUTATION_FOR_CONSENSUS = 50;  // 50% accuracy required
    
    event PriceSubmitted(bytes32 indexed pair, address indexed agent, uint256 price);
    event ConsensusReached(bytes32 indexed pair, uint256 price, uint256 submissions);
    event PriceRejected(bytes32 indexed pair, address indexed agent, uint256 price, string reason);
    event AgentBanned(address indexed agent, string reason);
    event ReputationUpdated(address indexed agent, uint256 accuracy);

    constructor(address _registry) Ownable(msg.sender) {
        registry = AgentRegistry(_registry);
    }

    /**
     * @dev Submit price data (only registered agents with good reputation)
     */
    function submitPrice(bytes32 pair, uint256 price) external whenNotPaused {
        require(registry.validateAgent(msg.sender), "Not a valid agent");
        require(price > 0, "Invalid price");
        require(!agentReputations[msg.sender].isBanned, "Agent is banned");
        
        PriceFeed storage feed = priceFeeds[pair];
        
        // Initialize new pair
        if (feed.pair == bytes32(0)) {
            feed.pair = pair;
            activePairs.push(pair);
        }
        
        // Check price deviation from previous consensus (if exists)
        if (feed.consensusPrice > 0) {
            uint256 deviation = _calculateDeviation(price, feed.consensusPrice);
            if (deviation > MAX_DEVIATION_BPS) {
                emit PriceRejected(pair, msg.sender, price, "Excessive deviation");
                _updateReputation(msg.sender, false);
                revert("Price deviates too much from consensus");
            }
        }
        
        // Clear old submissions if outside window
        if (block.timestamp > feed.lastUpdate + SUBMISSION_WINDOW) {
            delete feed.submissions;
            feed.submissionCount = 0;
        }
        
        // Check for duplicate submission
        for (uint256 i = 0; i < feed.submissions.length; i++) {
            require(feed.submissions[i].submitter != msg.sender, "Already submitted");
        }
        
        // Add submission
        feed.submissions.push(PriceData({
            price: price,
            timestamp: block.timestamp,
            submitter: msg.sender
        }));
        feed.submissionCount++;
        feed.lastUpdate = block.timestamp;
        
        // Update agent reputation
        agentReputations[msg.sender].totalSubmissions++;
        agentReputations[msg.sender].lastSubmission = block.timestamp;
        
        emit PriceSubmitted(pair, msg.sender, price);
        
        // Calculate consensus if enough submissions
        if (feed.submissionCount >= MIN_SUBMISSIONS) {
            _calculateConsensus(pair);
        }
    }
    
    /**
     * @dev Calculate deviation between two prices in basis points
     */
    function _calculateDeviation(uint256 price1, uint256 price2) internal pure returns (uint256) {
        if (price1 == price2) return 0;
        
        uint256 diff = price1 > price2 ? price1 - price2 : price2 - price1;
        return (diff * 10000) / price2;
    }
    
    /**
     * @dev Update agent reputation based on submission accuracy
     */
    function _updateReputation(address agent, bool accurate) internal {
        AgentReputation storage rep = agentReputations[agent];
        
        if (accurate) {
            rep.accurateSubmissions++;
        }
        
        // Calculate accuracy percentage
        if (rep.totalSubmissions >= 10) {
            uint256 accuracy = (rep.accurateSubmissions * 100) / rep.totalSubmissions;
            emit ReputationUpdated(agent, accuracy);
            
            // Ban agents with very low accuracy after 20 submissions
            if (rep.totalSubmissions >= 20 && accuracy < 30) {
                rep.isBanned = true;
                emit AgentBanned(agent, "Low accuracy");
            }
        }
    }

    /**
     * @dev Calculate median price from submissions with reputation weighting
     */
    function _calculateConsensus(bytes32 pair) internal {
        PriceFeed storage feed = priceFeeds[pair];
        uint256 count = feed.submissions.length;
        
        if (count == 0) return;
        
        // Sort prices (simple insertion sort for small arrays)
        uint256[] memory prices = new uint256[](count);
        for (uint256 i = 0; i < count; i++) {
            prices[i] = feed.submissions[i].price;
        }
        
        for (uint256 i = 1; i < count; i++) {
            uint256 key = prices[i];
            int256 j = int256(i) - 1;
            while (j >= 0 && prices[uint256(j)] > key) {
                prices[uint256(j + 1)] = prices[uint256(j)];
                j--;
            }
            prices[uint256(j + 1)] = key;
        }
        
        // Get median
        uint256 median;
        if (count % 2 == 0) {
            median = (prices[count / 2 - 1] + prices[count / 2]) / 2;
        } else {
            median = prices[count / 2];
        }
        
        feed.consensusPrice = median;
        emit ConsensusReached(pair, median, count);
        
        // Update reputation for all submitters
        for (uint256 i = 0; i < count; i++) {
            uint256 deviation = _calculateDeviation(feed.submissions[i].price, median);
            bool accurate = deviation <= ACCURACY_THRESHOLD_BPS;
            _updateReputation(feed.submissions[i].submitter, accurate);
        }
    }

    /**
     * @dev Get current price for a pair
     */
    function getPrice(bytes32 pair) external view returns (uint256 price, uint256 timestamp, bool isStale) {
        PriceFeed storage feed = priceFeeds[pair];
        price = feed.consensusPrice;
        timestamp = feed.lastUpdate;
        isStale = block.timestamp > feed.lastUpdate + MAX_PRICE_AGE;
    }

    /**
     * @dev Get number of active price pairs
     */
    function getActivePairCount() external view returns (uint256) {
        return activePairs.length;
    }

    /**
     * @dev Get submission count for a pair
     */
    function getSubmissionCount(bytes32 pair) external view returns (uint256) {
        return priceFeeds[pair].submissionCount;
    }

    /**
     * @dev Get all submitters for a pair
     */
    function getSubmitters(bytes32 pair) external view returns (address[] memory) {
        PriceFeed storage feed = priceFeeds[pair];
        address[] memory submitters = new address[](feed.submissions.length);
        for (uint256 i = 0; i < feed.submissions.length; i++) {
            submitters[i] = feed.submissions[i].submitter;
        }
        return submitters;
    }
    
    /**
     * @dev Get agent reputation stats
     */
    function getAgentReputation(address agent) external view returns (
        uint256 totalSubmissions,
        uint256 accurateSubmissions,
        uint256 accuracy,
        bool isBanned
    ) {
        AgentReputation storage rep = agentReputations[agent];
        totalSubmissions = rep.totalSubmissions;
        accurateSubmissions = rep.accurateSubmissions;
        accuracy = totalSubmissions > 0 ? (accurateSubmissions * 100) / totalSubmissions : 0;
        isBanned = rep.isBanned;
    }
    
    /**
     * @dev Unban an agent (owner only)
     */
    function unbanAgent(address agent) external onlyOwner {
        agentReputations[agent].isBanned = false;
    }
    
    /**
     * @dev Emergency pause (owner only)
     */
    function pause() external onlyOwner {
        _pause();
    }
    
    /**
     * @dev Unpause (owner only)
     */
    function unpause() external onlyOwner {
        _unpause();
    }
}
