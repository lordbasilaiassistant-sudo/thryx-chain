// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts-upgradeable/token/ERC20/ERC20Upgradeable.sol";
import "@openzeppelin/contracts-upgradeable/access/OwnableUpgradeable.sol";
import "@openzeppelin/contracts-upgradeable/proxy/utils/Initializable.sol";
import "@openzeppelin/contracts-upgradeable/proxy/utils/UUPSUpgradeable.sol";

/**
 * @title ThryxTokenV2
 * @notice Upgradeable version of THRYX Token using UUPS proxy pattern
 * @dev This is an example of how to make contracts upgradeable
 * 
 * Deployment:
 * 1. Deploy implementation: ThryxTokenV2
 * 2. Deploy proxy: ERC1967Proxy(implementation, initData)
 * 3. Interact via proxy address
 * 
 * Upgrade:
 * 1. Deploy new implementation: ThryxTokenV3
 * 2. Call proxy.upgradeTo(newImplementation)
 */
contract ThryxTokenV2 is 
    Initializable, 
    ERC20Upgradeable, 
    OwnableUpgradeable, 
    UUPSUpgradeable 
{
    /// @notice Mapping of authorized minters
    mapping(address => bool) public minters;
    
    /// @notice Version of this implementation
    uint256 public constant VERSION = 2;
    
    /// @notice Gap for future storage variables
    uint256[50] private __gap;
    
    /// @custom:oz-upgrades-unsafe-allow constructor
    constructor() {
        _disableInitializers();
    }
    
    /**
     * @notice Initialize the token (replaces constructor)
     * @dev Can only be called once
     */
    function initialize() public initializer {
        __ERC20_init("THRYX", "THRYX");
        __Ownable_init(msg.sender);
        __UUPSUpgradeable_init();
    }
    
    /**
     * @notice Authorize an address to mint tokens
     * @param minter Address to authorize
     * @param authorized Whether to authorize or revoke
     */
    function setMinter(address minter, bool authorized) external onlyOwner {
        minters[minter] = authorized;
    }
    
    /**
     * @notice Mint tokens to an address
     * @param to Recipient address
     * @param amount Amount to mint
     */
    function mint(address to, uint256 amount) external {
        require(minters[msg.sender] || msg.sender == owner(), "ThryxToken: not authorized to mint");
        _mint(to, amount);
    }
    
    /**
     * @notice Burn tokens from sender
     * @param amount Amount to burn
     */
    function burn(uint256 amount) external {
        _burn(msg.sender, amount);
    }
    
    // ==================== V2 Features ====================
    
    /// @notice Maximum supply cap (new in V2)
    uint256 public maxSupply;
    
    /**
     * @notice Set maximum supply cap (V2 feature)
     * @param _maxSupply New max supply (0 = unlimited)
     */
    function setMaxSupply(uint256 _maxSupply) external onlyOwner {
        require(_maxSupply == 0 || _maxSupply >= totalSupply(), "Max supply below current");
        maxSupply = _maxSupply;
    }
    
    /**
     * @notice Override mint to check max supply (V2 feature)
     */
    function _update(address from, address to, uint256 value) internal virtual override {
        if (from == address(0) && maxSupply > 0) {
            require(totalSupply() + value <= maxSupply, "Would exceed max supply");
        }
        super._update(from, to, value);
    }
    
    // ==================== UUPS Required ====================
    
    /**
     * @notice Authorize upgrade to new implementation
     * @dev Only owner can upgrade
     */
    function _authorizeUpgrade(address newImplementation) internal override onlyOwner {}
    
    /**
     * @notice Get implementation version
     */
    function version() external pure returns (uint256) {
        return VERSION;
    }
}
