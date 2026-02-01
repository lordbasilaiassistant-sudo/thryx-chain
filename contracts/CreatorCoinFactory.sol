// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "./CreatorCoin.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title CreatorCoinFactory
 * @dev Factory for deploying creator coins (like Zora's coin factory)
 * 
 * Anyone can create a creator coin for free!
 * - Coin is owned by the creator
 * - Creator earns 5% on all trades
 * - Protocol earns 1% on all trades
 */
contract CreatorCoinFactory is Ownable {
    // Protocol treasury
    address public protocolTreasury;
    
    // All created coins
    address[] public allCoins;
    mapping(address => address[]) public coinsByCreator;
    mapping(string => address) public coinBySymbol;
    
    // Events
    event CoinCreated(
        address indexed coin,
        address indexed creator,
        string name,
        string symbol,
        string profileUri
    );
    event TreasuryUpdated(address newTreasury);
    
    constructor(address treasury_) Ownable(msg.sender) {
        protocolTreasury = treasury_;
    }
    
    /**
     * @dev Create a new creator coin
     * @param name Token name (e.g., "Anthony Coin")
     * @param symbol Token symbol (e.g., "ANTHONY")
     * @param profileUri IPFS/URL to creator profile metadata
     */
    function createCoin(
        string memory name,
        string memory symbol,
        string memory profileUri
    ) external returns (address) {
        require(bytes(name).length > 0, "Name required");
        require(bytes(symbol).length > 0, "Symbol required");
        require(coinBySymbol[symbol] == address(0), "Symbol already exists");
        
        // Deploy new coin
        CreatorCoin coin = new CreatorCoin(
            name,
            symbol,
            msg.sender,
            protocolTreasury,
            profileUri
        );
        
        address coinAddress = address(coin);
        
        // Track coin
        allCoins.push(coinAddress);
        coinsByCreator[msg.sender].push(coinAddress);
        coinBySymbol[symbol] = coinAddress;
        
        emit CoinCreated(coinAddress, msg.sender, name, symbol, profileUri);
        
        return coinAddress;
    }
    
    /**
     * @dev Get total number of coins created
     */
    function totalCoins() external view returns (uint256) {
        return allCoins.length;
    }
    
    /**
     * @dev Get all coins by a creator
     */
    function getCoinsByCreator(address creator_) external view returns (address[] memory) {
        return coinsByCreator[creator_];
    }
    
    /**
     * @dev Get paginated list of all coins
     */
    function getCoins(uint256 offset, uint256 limit) external view returns (address[] memory) {
        uint256 total = allCoins.length;
        if (offset >= total) {
            return new address[](0);
        }
        
        uint256 end = offset + limit;
        if (end > total) {
            end = total;
        }
        
        address[] memory result = new address[](end - offset);
        for (uint256 i = offset; i < end; i++) {
            result[i - offset] = allCoins[i];
        }
        
        return result;
    }
    
    /**
     * @dev Update protocol treasury
     */
    function setTreasury(address newTreasury) external onlyOwner {
        require(newTreasury != address(0), "Invalid treasury");
        protocolTreasury = newTreasury;
        emit TreasuryUpdated(newTreasury);
    }
}
