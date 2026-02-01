// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title THRYX Price Oracle
 * @notice Stores live ETH/USD price updated by oracle agents
 * @dev Agents fetch real prices from CoinGecko and update on-chain
 */
contract PriceOracle is Ownable {
    // Price data
    uint256 public ethUsdPrice;      // ETH price in USD (8 decimals, like Chainlink)
    uint256 public lastUpdate;       // Timestamp of last update
    uint256 public updateCount;      // Total updates
    
    // Oracle configuration
    mapping(address => bool) public authorizedOracles;
    uint256 public minUpdateInterval = 60;  // Minimum 60 seconds between updates
    uint256 public maxPriceAge = 3600;      // Price considered stale after 1 hour
    
    // Events
    event PriceUpdated(uint256 newPrice, uint256 timestamp, address indexed oracle);
    event OracleAuthorized(address indexed oracle, bool authorized);
    
    constructor() Ownable(msg.sender) {
        // Set initial price to $2500 (with 8 decimals)
        ethUsdPrice = 2500 * 10**8;
        lastUpdate = block.timestamp;
    }
    
    /**
     * @notice Update the ETH/USD price
     * @param newPrice Price in USD with 8 decimals (e.g., $2500 = 250000000000)
     */
    function updatePrice(uint256 newPrice) external {
        require(authorizedOracles[msg.sender] || msg.sender == owner(), "Not authorized");
        require(block.timestamp >= lastUpdate + minUpdateInterval, "Update too frequent");
        require(newPrice > 0, "Invalid price");
        
        // Sanity check: price shouldn't change more than 20% in one update
        // Skip check if this is the first real update (still at default $2500)
        if (updateCount > 0) {
            uint256 maxChange = ethUsdPrice / 5;  // 20% max change
            require(
                newPrice >= ethUsdPrice - maxChange && newPrice <= ethUsdPrice + maxChange,
                "Price change too large"
            );
        }
        
        ethUsdPrice = newPrice;
        lastUpdate = block.timestamp;
        updateCount++;
        
        emit PriceUpdated(newPrice, block.timestamp, msg.sender);
    }
    
    /**
     * @notice Get the current ETH/USD price
     * @return price ETH price in USD with 8 decimals
     * @return timestamp Last update timestamp
     * @return isStale True if price is older than maxPriceAge
     */
    function getPrice() external view returns (uint256 price, uint256 timestamp, bool isStale) {
        return (
            ethUsdPrice,
            lastUpdate,
            block.timestamp > lastUpdate + maxPriceAge
        );
    }
    
    /**
     * @notice Get ETH price as a simple USD value (no decimals)
     * @return USD price per ETH
     */
    function getEthUsdPrice() external view returns (uint256) {
        return ethUsdPrice / 10**8;
    }
    
    /**
     * @notice Convert ETH amount to USD value
     * @param ethAmount Amount in wei (18 decimals)
     * @return USD value with 2 decimals (e.g., $100.50 = 10050)
     */
    function ethToUsd(uint256 ethAmount) external view returns (uint256) {
        // ethAmount is in wei (18 decimals)
        // ethUsdPrice is in USD with 8 decimals
        // Result should be USD with 2 decimals
        return (ethAmount * ethUsdPrice) / (10**18 * 10**6);
    }
    
    /**
     * @notice Convert USD to ETH amount
     * @param usdAmount USD amount with 2 decimals
     * @return ETH amount in wei
     */
    function usdToEth(uint256 usdAmount) external view returns (uint256) {
        require(ethUsdPrice > 0, "Price not set");
        return (usdAmount * 10**18 * 10**6) / ethUsdPrice;
    }
    
    // Admin functions
    
    function authorizeOracle(address oracle, bool authorized) external onlyOwner {
        authorizedOracles[oracle] = authorized;
        emit OracleAuthorized(oracle, authorized);
    }
    
    function setMinUpdateInterval(uint256 interval) external onlyOwner {
        minUpdateInterval = interval;
    }
    
    function setMaxPriceAge(uint256 age) external onlyOwner {
        maxPriceAge = age;
    }
    
    /**
     * @notice Emergency price set (owner only, bypasses checks)
     */
    function emergencySetPrice(uint256 newPrice) external onlyOwner {
        ethUsdPrice = newPrice;
        lastUpdate = block.timestamp;
        emit PriceUpdated(newPrice, block.timestamp, msg.sender);
    }
}
