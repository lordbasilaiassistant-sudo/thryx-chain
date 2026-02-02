// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/cryptography/MerkleProof.sol";

/**
 * @title L2WithdrawalContract
 * @dev Deployed on Thryx L2 to handle withdrawals to L1
 * Users burn L2 tokens here, claim on L1 after challenge period
 */
contract L2WithdrawalContract is Ownable, ReentrancyGuard {
    // Withdrawal tracking
    struct Withdrawal {
        address initiator;
        address l1Recipient;
        address token; // L2 token address
        uint256 amount;
        uint256 timestamp;
        uint256 l2BlockNumber;
        bool finalized;
    }
    
    uint256 public withdrawalCount;
    mapping(uint256 => Withdrawal) public withdrawals;
    mapping(address => uint256[]) public userWithdrawals;
    
    // Token mappings (L2 -> L1)
    mapping(address => address) public l2ToL1Token;
    
    // Merkle tree for withdrawal proofs
    bytes32 public withdrawalRoot;
    uint256 public lastUpdateBlock;
    
    // Events
    event WithdrawalInitiated(
        uint256 indexed withdrawalId,
        address indexed initiator,
        address l1Recipient,
        address l2Token,
        uint256 amount
    );
    event WithdrawalRootUpdated(bytes32 root, uint256 blockNumber);
    event TokenMappingSet(address l2Token, address l1Token);

    constructor() Ownable(msg.sender) {}

    /**
     * @dev Initiate withdrawal to L1 (burns L2 tokens)
     */
    function initiateWithdrawal(
        address l2Token,
        uint256 amount,
        address l1Recipient
    ) external nonReentrant returns (uint256 withdrawalId) {
        require(amount > 0, "Amount must be > 0");
        require(l2ToL1Token[l2Token] != address(0), "Token not bridgeable");
        
        // Burn L2 tokens (transfer to this contract for accounting)
        IERC20(l2Token).transferFrom(msg.sender, address(this), amount);
        
        withdrawalId = withdrawalCount++;
        
        withdrawals[withdrawalId] = Withdrawal({
            initiator: msg.sender,
            l1Recipient: l1Recipient == address(0) ? msg.sender : l1Recipient,
            token: l2Token,
            amount: amount,
            timestamp: block.timestamp,
            l2BlockNumber: block.number,
            finalized: false
        });
        
        userWithdrawals[msg.sender].push(withdrawalId);
        
        emit WithdrawalInitiated(
            withdrawalId,
            msg.sender,
            withdrawals[withdrawalId].l1Recipient,
            l2Token,
            amount
        );
    }

    /**
     * @dev Initiate ETH withdrawal to L1
     */
    function initiateETHWithdrawal(address l1Recipient) external payable nonReentrant returns (uint256 withdrawalId) {
        require(msg.value > 0, "Amount must be > 0");
        
        withdrawalId = withdrawalCount++;
        
        withdrawals[withdrawalId] = Withdrawal({
            initiator: msg.sender,
            l1Recipient: l1Recipient == address(0) ? msg.sender : l1Recipient,
            token: address(0),
            amount: msg.value,
            timestamp: block.timestamp,
            l2BlockNumber: block.number,
            finalized: false
        });
        
        userWithdrawals[msg.sender].push(withdrawalId);
        
        emit WithdrawalInitiated(
            withdrawalId,
            msg.sender,
            withdrawals[withdrawalId].l1Recipient,
            address(0),
            msg.value
        );
    }

    /**
     * @dev Update withdrawal Merkle root (called by sequencer)
     */
    function updateWithdrawalRoot(bytes32 newRoot) external onlyOwner {
        withdrawalRoot = newRoot;
        lastUpdateBlock = block.number;
        emit WithdrawalRootUpdated(newRoot, block.number);
    }

    /**
     * @dev Set token mapping (L2 -> L1)
     */
    function setTokenMapping(address l2Token, address l1Token) external onlyOwner {
        l2ToL1Token[l2Token] = l1Token;
        emit TokenMappingSet(l2Token, l1Token);
    }

    /**
     * @dev Get withdrawal hash for proof generation
     */
    function getWithdrawalHash(uint256 withdrawalId) external view returns (bytes32) {
        Withdrawal memory w = withdrawals[withdrawalId];
        address l1Token = w.token == address(0) ? address(0) : l2ToL1Token[w.token];
        
        return keccak256(abi.encodePacked(
            w.l1Recipient,
            l1Token,
            w.amount,
            w.l2BlockNumber,
            withdrawalId
        ));
    }

    /**
     * @dev Get user's withdrawal IDs
     */
    function getUserWithdrawals(address user) external view returns (uint256[] memory) {
        return userWithdrawals[user];
    }

    /**
     * @dev Get withdrawal details
     */
    function getWithdrawal(uint256 withdrawalId) external view returns (Withdrawal memory) {
        return withdrawals[withdrawalId];
    }

    /**
     * @dev Get L1 token address for L2 token
     */
    function getL1Token(address l2Token) external view returns (address) {
        return l2ToL1Token[l2Token];
    }
}
