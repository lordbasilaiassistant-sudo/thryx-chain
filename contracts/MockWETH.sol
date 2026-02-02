// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title MockWETH
 * @dev Mock wrapped ETH for AMM trading pairs
 */
contract MockWETH is ERC20, Ownable {
    constructor() ERC20("Wrapped ETH", "WETH") Ownable(msg.sender) {
        // Mint 10000 WETH to deployer
        _mint(msg.sender, 10000 * 10**18);
    }

    function mint(address to, uint256 amount) external onlyOwner {
        _mint(to, amount);
    }

    function batchMint(address[] calldata recipients, uint256[] calldata amounts) external onlyOwner {
        require(recipients.length == amounts.length, "Length mismatch");
        for (uint256 i = 0; i < recipients.length; i++) {
            _mint(recipients[i], amounts[i]);
        }
    }
}
