// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/Ownable.sol";

interface IThryxToken {
    function mint(address to, uint256 amount) external;
}

/**
 * @title WelcomeBonus
 * @dev Distributes $THRYX signup bonuses to new users
 * 
 * Each address can only claim once.
 * Default bonus: 100 $THRYX
 */
contract WelcomeBonus is Ownable {
    /// @notice The $THRYX token contract
    IThryxToken public token;
    
    /// @notice Amount of $THRYX given per signup (18 decimals)
    uint256 public bonusAmount = 100 ether; // 100 THRYX
    
    /// @notice Track who has claimed
    mapping(address => bool) public claimed;
    
    /// @notice Total claims made
    uint256 public totalClaims;
    
    /// @notice Whether claiming is enabled
    bool public claimingEnabled = true;
    
    /// @notice Authorized relayer for gasless claims
    address public relayer;

    event WelcomeBonusClaimed(address indexed user, uint256 amount);
    event BonusAmountUpdated(uint256 oldAmount, uint256 newAmount);
    event ClaimingStatusUpdated(bool enabled);

    constructor(address _token) Ownable(msg.sender) {
        token = IThryxToken(_token);
    }

    /**
     * @notice Claim welcome bonus (one-time per address)
     */
    function claimWelcomeBonus() external {
        require(claimingEnabled, "WelcomeBonus: claiming is disabled");
        require(!claimed[msg.sender], "WelcomeBonus: already claimed");
        
        claimed[msg.sender] = true;
        totalClaims++;
        
        token.mint(msg.sender, bonusAmount);
        
        emit WelcomeBonusClaimed(msg.sender, bonusAmount);
    }

    /**
     * @notice Claim welcome bonus for another address (gasless claim via relayer)
     * @param beneficiary The address to receive the bonus
     */
    function claimFor(address beneficiary) external {
        require(msg.sender == relayer || msg.sender == owner(), "WelcomeBonus: not authorized");
        require(claimingEnabled, "WelcomeBonus: claiming is disabled");
        require(!claimed[beneficiary], "WelcomeBonus: already claimed");
        
        claimed[beneficiary] = true;
        totalClaims++;
        
        token.mint(beneficiary, bonusAmount);
        
        emit WelcomeBonusClaimed(beneficiary, bonusAmount);
    }

    /**
     * @notice Set the authorized relayer for gasless claims
     * @param _relayer Address of the relayer
     */
    function setRelayer(address _relayer) external onlyOwner {
        relayer = _relayer;
    }

    /**
     * @notice Check if an address has claimed
     * @param user Address to check
     * @return Whether the user has claimed
     */
    function hasClaimed(address user) external view returns (bool) {
        return claimed[user];
    }

    /**
     * @notice Check if an address can claim
     * @param user Address to check
     * @return canClaim Whether the user can claim
     * @return amount The bonus amount they would receive
     */
    function canClaim(address user) external view returns (bool canClaim, uint256 amount) {
        canClaim = claimingEnabled && !claimed[user];
        amount = bonusAmount;
    }

    // ============ Admin Functions ============

    /**
     * @notice Update the bonus amount
     * @param newAmount New bonus amount (in wei, 18 decimals)
     */
    function setBonusAmount(uint256 newAmount) external onlyOwner {
        uint256 oldAmount = bonusAmount;
        bonusAmount = newAmount;
        emit BonusAmountUpdated(oldAmount, newAmount);
    }

    /**
     * @notice Enable or disable claiming
     * @param enabled Whether claiming should be enabled
     */
    function setClaimingEnabled(bool enabled) external onlyOwner {
        claimingEnabled = enabled;
        emit ClaimingStatusUpdated(enabled);
    }

    /**
     * @notice Update the token contract address
     * @param newToken New token contract address
     */
    function setToken(address newToken) external onlyOwner {
        token = IThryxToken(newToken);
    }

    /**
     * @notice Get contract statistics
     * @return claims Total number of claims
     * @return amount Current bonus amount
     * @return enabled Whether claiming is enabled
     */
    function getStats() external view returns (
        uint256 claims,
        uint256 amount,
        bool enabled
    ) {
        return (totalClaims, bonusAmount, claimingEnabled);
    }
}
