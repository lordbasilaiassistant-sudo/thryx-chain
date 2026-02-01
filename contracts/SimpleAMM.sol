// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title SimpleAMM
 * @dev Uniswap V2 style constant product AMM for AI agent trading
 */
contract SimpleAMM is ERC20, Ownable {
    IERC20 public tokenA; // e.g., USDC
    IERC20 public tokenB; // e.g., wrapped ETH representation
    
    uint256 public reserveA;
    uint256 public reserveB;
    
    uint256 public constant FEE_NUMERATOR = 3;
    uint256 public constant FEE_DENOMINATOR = 1000; // 0.3% fee
    
    uint256 public totalFeesA;
    uint256 public totalFeesB;

    event LiquidityAdded(address indexed provider, uint256 amountA, uint256 amountB, uint256 liquidity);
    event LiquidityRemoved(address indexed provider, uint256 amountA, uint256 amountB, uint256 liquidity);
    event Swap(address indexed trader, address tokenIn, uint256 amountIn, uint256 amountOut);

    constructor(address _tokenA, address _tokenB) ERC20("Thryx LP Token", "TLP") Ownable(msg.sender) {
        tokenA = IERC20(_tokenA);
        tokenB = IERC20(_tokenB);
    }

    /**
     * @dev Add liquidity to the pool
     */
    function addLiquidity(uint256 amountA, uint256 amountB) external returns (uint256 liquidity) {
        require(amountA > 0 && amountB > 0, "Amounts must be > 0");
        
        require(tokenA.transferFrom(msg.sender, address(this), amountA), "Transfer A failed");
        require(tokenB.transferFrom(msg.sender, address(this), amountB), "Transfer B failed");
        
        if (totalSupply() == 0) {
            // Initial liquidity
            liquidity = sqrt(amountA * amountB);
        } else {
            // Proportional liquidity
            liquidity = min(
                (amountA * totalSupply()) / reserveA,
                (amountB * totalSupply()) / reserveB
            );
        }
        
        require(liquidity > 0, "Insufficient liquidity minted");
        _mint(msg.sender, liquidity);
        
        reserveA += amountA;
        reserveB += amountB;
        
        emit LiquidityAdded(msg.sender, amountA, amountB, liquidity);
    }

    /**
     * @dev Remove liquidity from the pool
     */
    function removeLiquidity(uint256 liquidity) external returns (uint256 amountA, uint256 amountB) {
        require(liquidity > 0, "Liquidity must be > 0");
        require(balanceOf(msg.sender) >= liquidity, "Insufficient LP tokens");
        
        amountA = (liquidity * reserveA) / totalSupply();
        amountB = (liquidity * reserveB) / totalSupply();
        
        require(amountA > 0 && amountB > 0, "Insufficient liquidity burned");
        
        _burn(msg.sender, liquidity);
        
        reserveA -= amountA;
        reserveB -= amountB;
        
        require(tokenA.transfer(msg.sender, amountA), "Transfer A failed");
        require(tokenB.transfer(msg.sender, amountB), "Transfer B failed");
        
        emit LiquidityRemoved(msg.sender, amountA, amountB, liquidity);
    }

    /**
     * @dev Swap tokenA for tokenB or vice versa
     */
    function swap(address tokenIn, uint256 amountIn, uint256 minAmountOut) external returns (uint256 amountOut) {
        require(amountIn > 0, "Amount must be > 0");
        require(tokenIn == address(tokenA) || tokenIn == address(tokenB), "Invalid token");
        
        bool isAtoB = tokenIn == address(tokenA);
        
        (IERC20 inputToken, IERC20 outputToken, uint256 reserveIn, uint256 reserveOut) = isAtoB
            ? (tokenA, tokenB, reserveA, reserveB)
            : (tokenB, tokenA, reserveB, reserveA);
        
        require(inputToken.transferFrom(msg.sender, address(this), amountIn), "Transfer failed");
        
        // Calculate output with fee
        uint256 amountInWithFee = amountIn * (FEE_DENOMINATOR - FEE_NUMERATOR);
        amountOut = (amountInWithFee * reserveOut) / (reserveIn * FEE_DENOMINATOR + amountInWithFee);
        
        require(amountOut >= minAmountOut, "Slippage exceeded");
        require(amountOut < reserveOut, "Insufficient liquidity");
        
        // Update reserves
        if (isAtoB) {
            reserveA += amountIn;
            reserveB -= amountOut;
            totalFeesA += (amountIn * FEE_NUMERATOR) / FEE_DENOMINATOR;
        } else {
            reserveB += amountIn;
            reserveA -= amountOut;
            totalFeesB += (amountIn * FEE_NUMERATOR) / FEE_DENOMINATOR;
        }
        
        require(outputToken.transfer(msg.sender, amountOut), "Transfer out failed");
        
        emit Swap(msg.sender, tokenIn, amountIn, amountOut);
    }

    /**
     * @dev Get expected output for a swap
     */
    function getAmountOut(address tokenIn, uint256 amountIn) external view returns (uint256) {
        bool isAtoB = tokenIn == address(tokenA);
        (uint256 reserveIn, uint256 reserveOut) = isAtoB
            ? (reserveA, reserveB)
            : (reserveB, reserveA);
        
        uint256 amountInWithFee = amountIn * (FEE_DENOMINATOR - FEE_NUMERATOR);
        return (amountInWithFee * reserveOut) / (reserveIn * FEE_DENOMINATOR + amountInWithFee);
    }

    /**
     * @dev Get current price of tokenA in terms of tokenB
     */
    function getPrice() external view returns (uint256) {
        if (reserveA == 0) return 0;
        return (reserveB * 1e18) / reserveA;
    }

    // Math helpers
    function sqrt(uint256 y) internal pure returns (uint256 z) {
        if (y > 3) {
            z = y;
            uint256 x = y / 2 + 1;
            while (x < z) {
                z = x;
                x = (y / x + x) / 2;
            }
        } else if (y != 0) {
            z = 1;
        }
    }

    function min(uint256 a, uint256 b) internal pure returns (uint256) {
        return a < b ? a : b;
    }
}
