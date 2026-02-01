// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/**
 * @title L1DepositContract
 * @dev Deployed on Ethereum L1 (Sepolia testnet) to handle deposits for Thryx L2
 * Users deposit ETH or USDC here, receive minted tokens on L2
 */
contract L1DepositContract is Ownable, ReentrancyGuard {
    // Deposit tracking
    struct Deposit {
        address depositor;
        address token; // address(0) for ETH
        uint256 amount;
        uint256 l2Recipient; // Can be different from depositor
        uint256 timestamp;
        bool processed;
    }
    
    uint256 public depositCount;
    mapping(uint256 => Deposit) public deposits;
    mapping(address => uint256[]) public userDeposits;
    
    // Supported tokens
    mapping(address => bool) public supportedTokens;
    
    // L2 state roots (submitted by sequencer)
    struct StateRoot {
        bytes32 root;
        uint256 blockNumber;
        uint256 timestamp;
    }
    
    StateRoot[] public stateRoots;
    address public sequencer;
    
    // Withdrawal claims (for L2 -> L1)
    mapping(bytes32 => bool) public processedWithdrawals;
    uint256 public constant WITHDRAWAL_DELAY = 7 days; // Challenge period
    
    // Events
    event DepositInitiated(
        uint256 indexed depositId,
        address indexed depositor,
        address token,
        uint256 amount,
        uint256 l2Recipient
    );
    event StateRootSubmitted(uint256 indexed index, bytes32 root, uint256 l2BlockNumber);
    event WithdrawalProcessed(bytes32 indexed withdrawalHash, address recipient, uint256 amount);
    event TokenAdded(address token);
    event SequencerUpdated(address newSequencer);

    constructor() Ownable(msg.sender) {
        sequencer = msg.sender;
        // ETH is always supported (address(0))
        supportedTokens[address(0)] = true;
    }

    /**
     * @dev Deposit ETH to bridge to L2
     */
    function depositETH(uint256 l2Recipient) external payable nonReentrant {
        require(msg.value > 0, "Amount must be > 0");
        
        uint256 depositId = depositCount++;
        
        deposits[depositId] = Deposit({
            depositor: msg.sender,
            token: address(0),
            amount: msg.value,
            l2Recipient: l2Recipient == 0 ? uint256(uint160(msg.sender)) : l2Recipient,
            timestamp: block.timestamp,
            processed: false
        });
        
        userDeposits[msg.sender].push(depositId);
        
        emit DepositInitiated(
            depositId,
            msg.sender,
            address(0),
            msg.value,
            deposits[depositId].l2Recipient
        );
    }

    /**
     * @dev Deposit ERC20 tokens to bridge to L2
     */
    function depositToken(address token, uint256 amount, uint256 l2Recipient) external nonReentrant {
        require(supportedTokens[token], "Token not supported");
        require(amount > 0, "Amount must be > 0");
        
        // Transfer tokens to this contract
        IERC20(token).transferFrom(msg.sender, address(this), amount);
        
        uint256 depositId = depositCount++;
        
        deposits[depositId] = Deposit({
            depositor: msg.sender,
            token: token,
            amount: amount,
            l2Recipient: l2Recipient == 0 ? uint256(uint160(msg.sender)) : l2Recipient,
            timestamp: block.timestamp,
            processed: false
        });
        
        userDeposits[msg.sender].push(depositId);
        
        emit DepositInitiated(
            depositId,
            msg.sender,
            token,
            amount,
            deposits[depositId].l2Recipient
        );
    }

    /**
     * @dev Submit L2 state root (only sequencer)
     */
    function submitStateRoot(bytes32 root, uint256 l2BlockNumber) external {
        require(msg.sender == sequencer, "Only sequencer");
        
        stateRoots.push(StateRoot({
            root: root,
            blockNumber: l2BlockNumber,
            timestamp: block.timestamp
        }));
        
        emit StateRootSubmitted(stateRoots.length - 1, root, l2BlockNumber);
    }

    /**
     * @dev Process withdrawal from L2 (with Merkle proof)
     */
    function processWithdrawal(
        address recipient,
        address token,
        uint256 amount,
        uint256 l2BlockNumber,
        bytes32[] calldata proof,
        uint256 withdrawalIndex
    ) external nonReentrant {
        // Find the state root for this L2 block
        bytes32 stateRoot;
        uint256 rootTimestamp;
        bool found = false;
        
        for (uint256 i = stateRoots.length; i > 0; i--) {
            if (stateRoots[i-1].blockNumber <= l2BlockNumber) {
                stateRoot = stateRoots[i-1].root;
                rootTimestamp = stateRoots[i-1].timestamp;
                found = true;
                break;
            }
        }
        
        require(found, "No state root for block");
        require(block.timestamp >= rootTimestamp + WITHDRAWAL_DELAY, "Withdrawal delay not passed");
        
        // Compute withdrawal hash
        bytes32 withdrawalHash = keccak256(abi.encodePacked(
            recipient,
            token,
            amount,
            l2BlockNumber,
            withdrawalIndex
        ));
        
        require(!processedWithdrawals[withdrawalHash], "Already processed");
        
        // Verify Merkle proof
        require(_verifyProof(proof, stateRoot, withdrawalHash), "Invalid proof");
        
        processedWithdrawals[withdrawalHash] = true;
        
        // Transfer funds
        if (token == address(0)) {
            (bool success, ) = recipient.call{value: amount}("");
            require(success, "ETH transfer failed");
        } else {
            IERC20(token).transfer(recipient, amount);
        }
        
        emit WithdrawalProcessed(withdrawalHash, recipient, amount);
    }

    /**
     * @dev Verify Merkle proof
     */
    function _verifyProof(
        bytes32[] calldata proof,
        bytes32 root,
        bytes32 leaf
    ) internal pure returns (bool) {
        bytes32 computedHash = leaf;
        
        for (uint256 i = 0; i < proof.length; i++) {
            bytes32 proofElement = proof[i];
            
            if (computedHash <= proofElement) {
                computedHash = keccak256(abi.encodePacked(computedHash, proofElement));
            } else {
                computedHash = keccak256(abi.encodePacked(proofElement, computedHash));
            }
        }
        
        return computedHash == root;
    }

    /**
     * @dev Add supported token (only owner)
     */
    function addSupportedToken(address token) external onlyOwner {
        supportedTokens[token] = true;
        emit TokenAdded(token);
    }

    /**
     * @dev Update sequencer address (only owner)
     */
    function setSequencer(address newSequencer) external onlyOwner {
        sequencer = newSequencer;
        emit SequencerUpdated(newSequencer);
    }

    /**
     * @dev Get user's deposit IDs
     */
    function getUserDeposits(address user) external view returns (uint256[] memory) {
        return userDeposits[user];
    }

    /**
     * @dev Get latest state root
     */
    function getLatestStateRoot() external view returns (bytes32 root, uint256 blockNumber, uint256 timestamp) {
        require(stateRoots.length > 0, "No state roots");
        StateRoot memory latest = stateRoots[stateRoots.length - 1];
        return (latest.root, latest.blockNumber, latest.timestamp);
    }

    /**
     * @dev Get state root count
     */
    function getStateRootCount() external view returns (uint256) {
        return stateRoots.length;
    }

    // Allow contract to receive ETH
    receive() external payable {}
}
