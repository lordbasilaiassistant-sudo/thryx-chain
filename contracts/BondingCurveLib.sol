// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/**
 * @title THRYX Bonding Curve Library
 * @notice Advanced bonding curve math for creator coins
 * @dev Provides multiple curve types with floor protection
 */
library BondingCurveLib {
    // Curve types
    uint8 public constant CURVE_LINEAR = 0;
    uint8 public constant CURVE_QUADRATIC = 1;
    uint8 public constant CURVE_EXPONENTIAL = 2;
    uint8 public constant CURVE_SIGMOID = 3;
    
    /**
     * @notice Calculate price based on curve type and supply
     * @param curveType Type of bonding curve
     * @param supply Current token supply (18 decimals)
     * @param basePrice Starting price (wei)
     * @param growthFactor How aggressively price grows
     * @param priceFloor Minimum price (cannot go below)
     * @return price Current price in wei
     */
    function calculatePrice(
        uint8 curveType,
        uint256 supply,
        uint256 basePrice,
        uint256 growthFactor,
        uint256 priceFloor
    ) internal pure returns (uint256 price) {
        if (supply == 0) {
            return basePrice > priceFloor ? basePrice : priceFloor;
        }
        
        uint256 normalizedSupply = supply / 1e15; // Scale for math
        
        if (curveType == CURVE_LINEAR) {
            // Linear: price = base + (supply * factor)
            price = basePrice + (normalizedSupply * growthFactor / 1e3);
        } 
        else if (curveType == CURVE_QUADRATIC) {
            // Quadratic: price = base + (supply² * factor)
            // More aggressive than linear
            price = basePrice + (normalizedSupply * normalizedSupply * growthFactor / 1e9);
        }
        else if (curveType == CURVE_EXPONENTIAL) {
            // Exponential: price = base * (1 + factor)^(supply/scale)
            // Very aggressive growth
            uint256 exponent = normalizedSupply / 1e6;
            if (exponent > 10) exponent = 10; // Cap at 10x base
            price = basePrice;
            for (uint256 i = 0; i < exponent; i++) {
                price = price + (price * growthFactor / 10000);
            }
        }
        else if (curveType == CURVE_SIGMOID) {
            // Sigmoid: S-curve, slow start, fast middle, slow end
            // Good for capped supplies
            uint256 midpoint = 1e9; // 1B tokens midpoint
            if (normalizedSupply < midpoint) {
                // Below midpoint: quadratic growth
                price = basePrice + (normalizedSupply * normalizedSupply * growthFactor / 1e12);
            } else {
                // Above midpoint: slower growth (approaching cap)
                uint256 excess = normalizedSupply - midpoint;
                uint256 midPrice = basePrice + (midpoint * midpoint * growthFactor / 1e12);
                price = midPrice + (excess * growthFactor / 1e6);
            }
        }
        else {
            // Default to quadratic
            price = basePrice + (normalizedSupply * normalizedSupply * growthFactor / 1e9);
        }
        
        // Enforce price floor
        return price > priceFloor ? price : priceFloor;
    }
    
    /**
     * @notice Calculate tokens received for ETH at current supply
     * @param ethAmount ETH being spent
     * @param currentPrice Current token price
     * @return tokens Amount of tokens to mint
     */
    function calculateTokensForEth(
        uint256 ethAmount,
        uint256 currentPrice
    ) internal pure returns (uint256) {
        require(currentPrice > 0, "Invalid price");
        return (ethAmount * 1e18) / currentPrice;
    }
    
    /**
     * @notice Calculate ETH received for tokens at current price
     * @param tokenAmount Tokens being sold
     * @param currentPrice Current token price  
     * @return eth Amount of ETH to return
     */
    function calculateEthForTokens(
        uint256 tokenAmount,
        uint256 currentPrice
    ) internal pure returns (uint256) {
        return (tokenAmount * currentPrice) / 1e18;
    }
    
    /**
     * @notice Calculate integral for exact bonding curve math
     * @dev For precise buy/sell with large amounts
     */
    function calculateIntegral(
        uint8 curveType,
        uint256 supplyStart,
        uint256 supplyEnd,
        uint256 basePrice,
        uint256 growthFactor
    ) internal pure returns (uint256) {
        if (supplyEnd <= supplyStart) return 0;
        
        uint256 s0 = supplyStart / 1e15;
        uint256 s1 = supplyEnd / 1e15;
        uint256 diff = s1 - s0;
        
        if (curveType == CURVE_LINEAR) {
            // Integral of (base + k*x) = base*x + k*x²/2
            uint256 basePart = basePrice * diff / 1e3;
            uint256 growthPart = growthFactor * (s1*s1 - s0*s0) / (2 * 1e6);
            return basePart + growthPart;
        }
        else if (curveType == CURVE_QUADRATIC) {
            // Integral of (base + k*x²) = base*x + k*x³/3
            uint256 basePart = basePrice * diff / 1e3;
            uint256 growthPart = growthFactor * (s1*s1*s1 - s0*s0*s0) / (3 * 1e12);
            return basePart + growthPart;
        }
        
        // Default: use average price approximation
        uint256 priceStart = calculatePrice(curveType, supplyStart, basePrice, growthFactor, 0);
        uint256 priceEnd = calculatePrice(curveType, supplyEnd, basePrice, growthFactor, 0);
        return ((priceStart + priceEnd) / 2) * diff / 1e3;
    }
}
