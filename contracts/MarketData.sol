// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title THRYX Market Data
 * @notice Stores historical price data for all creator coins (for charts)
 * @dev Updated by agents, consumed by frontends for price charts
 */
contract MarketData is Ownable {
    // Price snapshot structure
    struct PricePoint {
        uint256 price;      // Price in wei per token (18 decimals)
        uint256 volume;     // Volume in that period
        uint256 timestamp;
    }
    
    // Coin stats
    struct CoinStats {
        uint256 currentPrice;
        uint256 high24h;
        uint256 low24h;
        uint256 volume24h;
        uint256 marketCap;
        uint256 totalTrades;
        uint256 holders;
        int256 priceChange24h;  // Basis points (can be negative)
        uint256 lastUpdate;
    }
    
    // Storage
    mapping(address => PricePoint[]) public priceHistory;  // coin => price points
    mapping(address => CoinStats) public coinStats;
    mapping(address => bool) public trackedCoins;
    address[] public allTrackedCoins;
    
    // Authorized updaters (agents)
    mapping(address => bool) public authorizedAgents;
    
    // Events
    event PriceRecorded(address indexed coin, uint256 price, uint256 volume, uint256 timestamp);
    event StatsUpdated(address indexed coin, uint256 price, int256 change24h);
    event CoinTracked(address indexed coin);
    
    constructor() Ownable(msg.sender) {}
    
    modifier onlyAuthorized() {
        require(msg.sender == owner() || authorizedAgents[msg.sender], "Not authorized");
        _;
    }
    
    /**
     * @notice Record a new price point for a coin
     * @param coin Creator coin address
     * @param price Current price in wei
     * @param volume Trade volume since last update
     */
    function recordPrice(address coin, uint256 price, uint256 volume) external onlyAuthorized {
        if (!trackedCoins[coin]) {
            trackedCoins[coin] = true;
            allTrackedCoins.push(coin);
            emit CoinTracked(coin);
        }
        
        priceHistory[coin].push(PricePoint({
            price: price,
            volume: volume,
            timestamp: block.timestamp
        }));
        
        emit PriceRecorded(coin, price, volume, block.timestamp);
    }
    
    /**
     * @notice Update full stats for a coin
     */
    function updateStats(
        address coin,
        uint256 currentPrice,
        uint256 high24h,
        uint256 low24h,
        uint256 volume24h,
        uint256 marketCap,
        uint256 totalTrades,
        uint256 holders,
        int256 priceChange24h
    ) external onlyAuthorized {
        if (!trackedCoins[coin]) {
            trackedCoins[coin] = true;
            allTrackedCoins.push(coin);
            emit CoinTracked(coin);
        }
        
        coinStats[coin] = CoinStats({
            currentPrice: currentPrice,
            high24h: high24h,
            low24h: low24h,
            volume24h: volume24h,
            marketCap: marketCap,
            totalTrades: totalTrades,
            holders: holders,
            priceChange24h: priceChange24h,
            lastUpdate: block.timestamp
        });
        
        emit StatsUpdated(coin, currentPrice, priceChange24h);
    }
    
    /**
     * @notice Get price history for charts (last N points)
     */
    function getPriceHistory(address coin, uint256 count) external view returns (
        uint256[] memory prices,
        uint256[] memory volumes,
        uint256[] memory timestamps
    ) {
        PricePoint[] storage history = priceHistory[coin];
        uint256 len = history.length;
        uint256 start = len > count ? len - count : 0;
        uint256 resultLen = len - start;
        
        prices = new uint256[](resultLen);
        volumes = new uint256[](resultLen);
        timestamps = new uint256[](resultLen);
        
        for (uint256 i = 0; i < resultLen; i++) {
            PricePoint storage point = history[start + i];
            prices[i] = point.price;
            volumes[i] = point.volume;
            timestamps[i] = point.timestamp;
        }
    }
    
    /**
     * @notice Get stats for a coin
     */
    function getStats(address coin) external view returns (CoinStats memory) {
        return coinStats[coin];
    }
    
    /**
     * @notice Get all tracked coins
     */
    function getAllCoins() external view returns (address[] memory) {
        return allTrackedCoins;
    }
    
    /**
     * @notice Get count of tracked coins
     */
    function getCoinCount() external view returns (uint256) {
        return allTrackedCoins.length;
    }
    
    // Admin
    function authorizeAgent(address agent, bool authorized) external onlyOwner {
        authorizedAgents[agent] = authorized;
    }
}
