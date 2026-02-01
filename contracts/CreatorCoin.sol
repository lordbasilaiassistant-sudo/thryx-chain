// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/**
 * @title CreatorCoin
 * @dev Social token with bonding curve pricing (like Zora creator coins)
 * 
 * Features:
 * - Bonding curve: price increases with supply (quadratic)
 * - Price floor: AI agents ensure value never drops below floor
 * - Creator fee: creator earns % on every trade
 * - Protocol fee: THRYX treasury earns % on every trade
 * - Automatic liquidity: ETH locked in contract
 */
contract CreatorCoin is ERC20, Ownable, ReentrancyGuard {
    // Bonding curve parameters (more aggressive for value growth)
    uint256 public constant BASE_PRICE = 1e14;           // Starting price: 0.0001 ETH
    uint256 public constant GROWTH_FACTOR = 1e12;        // Quadratic growth factor
    uint256 public priceFloor;                           // Minimum price (set by AI agents)
    uint256 public allTimeHigh;                          // Track ATH
    
    // Fees
    uint256 public constant CREATOR_FEE_BPS = 500; // 5% to creator
    uint256 public constant PROTOCOL_FEE_BPS = 100; // 1% to protocol
    uint256 public constant BPS_DENOMINATOR = 10000;
    
    // Addresses
    address public immutable creator;
    address public protocolTreasury;
    
    // Metadata
    string public profileUri; // IPFS or URL to creator profile
    uint256 public createdAt;
    
    // Stats
    uint256 public totalEthLocked;
    uint256 public totalVolume;
    uint256 public totalTrades;
    
    // Events
    event Buy(address indexed buyer, uint256 ethIn, uint256 tokensOut, uint256 newPrice);
    event Sell(address indexed seller, uint256 tokensIn, uint256 ethOut, uint256 newPrice);
    event CreatorFeeCollected(uint256 amount);
    event ProtocolFeeCollected(uint256 amount);
    event ProfileUpdated(string newUri);
    
    constructor(
        string memory name_,
        string memory symbol_,
        address creator_,
        address protocolTreasury_,
        string memory profileUri_
    ) ERC20(name_, symbol_) Ownable(creator_) {
        creator = creator_;
        protocolTreasury = protocolTreasury_;
        profileUri = profileUri_;
        createdAt = block.timestamp;
    }
    
    /**
     * @dev Get current price based on quadratic bonding curve
     * Price = BASE_PRICE + (supply² * GROWTH_FACTOR)
     * Price can NEVER go below priceFloor (enforced by AI agents)
     */
    function getCurrentPrice() public view returns (uint256) {
        uint256 supply = totalSupply();
        uint256 calculatedPrice;
        
        if (supply == 0) {
            calculatedPrice = BASE_PRICE;
        } else {
            // Quadratic curve: price grows with square of supply
            // More aggressive growth for sustained value increase
            uint256 normalized = supply / 1e15; // Scale for math
            calculatedPrice = BASE_PRICE + (normalized * normalized * GROWTH_FACTOR / 1e9);
        }
        
        // Enforce price floor (AI agents maintain this)
        if (priceFloor > 0 && calculatedPrice < priceFloor) {
            return priceFloor;
        }
        
        return calculatedPrice;
    }
    
    /**
     * @dev Set price floor (only owner/creator or authorized)
     */
    function setPriceFloor(uint256 floor) external onlyOwner {
        priceFloor = floor;
    }
    
    /**
     * @dev Calculate tokens received for ETH input
     */
    function getTokensForEth(uint256 ethAmount) public view returns (uint256) {
        uint256 price = getCurrentPrice();
        // tokens = ethAmount * 1e18 / price
        return (ethAmount * 1e18) / price;
    }
    
    /**
     * @dev Calculate ETH received for token input
     */
    function getEthForTokens(uint256 tokenAmount) public view returns (uint256) {
        uint256 price = getCurrentPrice();
        // eth = tokenAmount * price / 1e18
        return (tokenAmount * price) / 1e18;
    }
    
    /**
     * @dev Buy tokens with ETH
     */
    function buy(uint256 minTokensOut) external payable nonReentrant returns (uint256) {
        require(msg.value > 0, "Must send ETH");
        
        // Calculate fees
        uint256 creatorFee = (msg.value * CREATOR_FEE_BPS) / BPS_DENOMINATOR;
        uint256 protocolFee = (msg.value * PROTOCOL_FEE_BPS) / BPS_DENOMINATOR;
        uint256 ethForTokens = msg.value - creatorFee - protocolFee;
        
        // Calculate tokens
        uint256 tokensOut = getTokensForEth(ethForTokens);
        require(tokensOut >= minTokensOut, "Slippage exceeded");
        
        // Mint tokens
        _mint(msg.sender, tokensOut);
        
        // Update stats
        totalEthLocked += ethForTokens;
        totalVolume += msg.value;
        totalTrades++;
        
        // Pay fees
        if (creatorFee > 0) {
            (bool success1, ) = creator.call{value: creatorFee}("");
            require(success1, "Creator fee failed");
            emit CreatorFeeCollected(creatorFee);
        }
        
        if (protocolFee > 0 && protocolTreasury != address(0)) {
            (bool success2, ) = protocolTreasury.call{value: protocolFee}("");
            require(success2, "Protocol fee failed");
            emit ProtocolFeeCollected(protocolFee);
        }
        
        uint256 newPrice = getCurrentPrice();
        
        // Track all-time high
        if (newPrice > allTimeHigh) {
            allTimeHigh = newPrice;
        }
        
        emit Buy(msg.sender, msg.value, tokensOut, newPrice);
        return tokensOut;
    }
    
    /**
     * @dev Sell tokens for ETH
     */
    function sell(uint256 tokenAmount, uint256 minEthOut) external nonReentrant returns (uint256) {
        require(tokenAmount > 0, "Must sell tokens");
        require(balanceOf(msg.sender) >= tokenAmount, "Insufficient balance");
        
        // Calculate ETH before fees
        uint256 ethBeforeFees = getEthForTokens(tokenAmount);
        require(ethBeforeFees <= totalEthLocked, "Insufficient liquidity");
        
        // Calculate fees
        uint256 creatorFee = (ethBeforeFees * CREATOR_FEE_BPS) / BPS_DENOMINATOR;
        uint256 protocolFee = (ethBeforeFees * PROTOCOL_FEE_BPS) / BPS_DENOMINATOR;
        uint256 ethOut = ethBeforeFees - creatorFee - protocolFee;
        
        require(ethOut >= minEthOut, "Slippage exceeded");
        
        // Burn tokens
        _burn(msg.sender, tokenAmount);
        
        // Update stats
        totalEthLocked -= ethBeforeFees;
        totalVolume += ethBeforeFees;
        totalTrades++;
        
        // Pay seller
        (bool success, ) = msg.sender.call{value: ethOut}("");
        require(success, "ETH transfer failed");
        
        // Pay fees
        if (creatorFee > 0) {
            (bool success1, ) = creator.call{value: creatorFee}("");
            require(success1, "Creator fee failed");
            emit CreatorFeeCollected(creatorFee);
        }
        
        if (protocolFee > 0 && protocolTreasury != address(0)) {
            (bool success2, ) = protocolTreasury.call{value: protocolFee}("");
            require(success2, "Protocol fee failed");
            emit ProtocolFeeCollected(protocolFee);
        }
        
        emit Sell(msg.sender, tokenAmount, ethOut, getCurrentPrice());
        return ethOut;
    }
    
    /**
     * @dev Update creator profile URI
     */
    function setProfileUri(string memory newUri) external onlyOwner {
        profileUri = newUri;
        emit ProfileUpdated(newUri);
    }
    
    /**
     * @dev Get coin stats including bonding curve data
     */
    function getStats() external view returns (
        uint256 price,
        uint256 supply,
        uint256 ethLocked,
        uint256 volume,
        uint256 trades,
        uint256 marketCap,
        uint256 floor,
        uint256 ath
    ) {
        price = getCurrentPrice();
        supply = totalSupply();
        ethLocked = totalEthLocked;
        volume = totalVolume;
        trades = totalTrades;
        marketCap = (supply * price) / 1e18;
        floor = priceFloor;
        ath = allTimeHigh;
    }
    
    /**
     * @dev Get bonding curve info
     */
    function getCurveInfo() external view returns (
        uint256 basePrice,
        uint256 growthFactor,
        uint256 currentPrice,
        uint256 floor,
        uint256 ath,
        uint256 supply
    ) {
        return (
            BASE_PRICE,
            GROWTH_FACTOR,
            getCurrentPrice(),
            priceFloor,
            allTimeHigh,
            totalSupply()
        );
    }
    
    // Allow contract to receive ETH
    receive() external payable {}
}
