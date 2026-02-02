// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title ThryxToken
 * @dev $THRYX Platform Token - ERC-20 with controlled minting
 * 
 * This is NOT backed by ETH - it's a separate utility/governance token.
 * Used for:
 * - Signup bonuses (100 $THRYX per new user)
 * - Governance voting
 * - Profile badges and levels
 * - Future platform features
 */
contract ThryxToken is ERC20, Ownable {
    /// @notice Addresses authorized to mint tokens
    mapping(address => bool) public minters;
    
    /// @notice Total tokens minted through signup bonuses
    uint256 public totalBonusesMinted;
    
    /// @notice Number of unique addresses that received bonuses
    uint256 public totalBonusRecipients;

    event MinterUpdated(address indexed minter, bool allowed);
    event BonusMinted(address indexed recipient, uint256 amount);

    constructor() ERC20("THRYX", "THRYX") Ownable(msg.sender) {
        // Mint initial supply to deployer (treasury)
        // 1 million tokens for future distributions, partnerships, etc.
        _mint(msg.sender, 1_000_000 * 10**18);
    }

    /**
     * @notice Add or remove a minter
     * @param minter Address to update
     * @param allowed Whether the address can mint
     */
    function setMinter(address minter, bool allowed) external onlyOwner {
        minters[minter] = allowed;
        emit MinterUpdated(minter, allowed);
    }

    /**
     * @notice Mint tokens to an address (only authorized minters)
     * @param to Recipient address
     * @param amount Amount to mint (in wei, 18 decimals)
     */
    function mint(address to, uint256 amount) external {
        require(minters[msg.sender], "ThryxToken: not authorized to mint");
        _mint(to, amount);
        
        // Track bonus statistics
        totalBonusesMinted += amount;
        totalBonusRecipients++;
        
        emit BonusMinted(to, amount);
    }

    /**
     * @notice Get token statistics
     * @return supply Total token supply
     * @return bonusesMinted Total minted through bonuses
     * @return bonusRecipients Number of bonus recipients
     */
    function getStats() external view returns (
        uint256 supply,
        uint256 bonusesMinted,
        uint256 bonusRecipients
    ) {
        return (totalSupply(), totalBonusesMinted, totalBonusRecipients);
    }
}
