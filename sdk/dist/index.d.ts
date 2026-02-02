import { Chain, Address, PublicClient, WalletClient, Hash } from 'viem';
export { formatEther, parseEther } from 'viem';
import { PrivateKeyAccount } from 'viem/accounts';

/**
 * @thryx/sdk
 * TypeScript SDK for THRYX - AI-Native Blockchain
 * Chain ID: 77777
 *
 * @example
 * ```typescript
 * import { ThryxSDK, THRYX_CHAIN } from '@thryx/sdk';
 *
 * const sdk = new ThryxSDK({
 *   rpcUrl: 'https://rpc.thryx.mom',
 *   privateKey: '0x...'
 * });
 *
 * // Get block number
 * const blockNumber = await sdk.getBlockNumber();
 *
 * // Swap tokens
 * await sdk.swap('0xUSDC', '0xWETH', 100n * 10n**6n, 0n);
 * ```
 */

/**
 * THRYX Mainnet chain configuration
 */
declare const THRYX_CHAIN: Chain;
/**
 * Base Mainnet (L1 for THRYX)
 */
declare const BASE_CHAIN: Chain;
declare const ERC20_ABI: readonly [{
    readonly name: "name";
    readonly type: "function";
    readonly stateMutability: "view";
    readonly inputs: readonly [];
    readonly outputs: readonly [{
        readonly type: "string";
    }];
}, {
    readonly name: "symbol";
    readonly type: "function";
    readonly stateMutability: "view";
    readonly inputs: readonly [];
    readonly outputs: readonly [{
        readonly type: "string";
    }];
}, {
    readonly name: "decimals";
    readonly type: "function";
    readonly stateMutability: "view";
    readonly inputs: readonly [];
    readonly outputs: readonly [{
        readonly type: "uint8";
    }];
}, {
    readonly name: "totalSupply";
    readonly type: "function";
    readonly stateMutability: "view";
    readonly inputs: readonly [];
    readonly outputs: readonly [{
        readonly type: "uint256";
    }];
}, {
    readonly name: "balanceOf";
    readonly type: "function";
    readonly stateMutability: "view";
    readonly inputs: readonly [{
        readonly type: "address";
        readonly name: "owner";
    }];
    readonly outputs: readonly [{
        readonly type: "uint256";
    }];
}, {
    readonly name: "allowance";
    readonly type: "function";
    readonly stateMutability: "view";
    readonly inputs: readonly [{
        readonly type: "address";
        readonly name: "owner";
    }, {
        readonly type: "address";
        readonly name: "spender";
    }];
    readonly outputs: readonly [{
        readonly type: "uint256";
    }];
}, {
    readonly name: "approve";
    readonly type: "function";
    readonly stateMutability: "nonpayable";
    readonly inputs: readonly [{
        readonly type: "address";
        readonly name: "spender";
    }, {
        readonly type: "uint256";
        readonly name: "amount";
    }];
    readonly outputs: readonly [{
        readonly type: "bool";
    }];
}, {
    readonly name: "transfer";
    readonly type: "function";
    readonly stateMutability: "nonpayable";
    readonly inputs: readonly [{
        readonly type: "address";
        readonly name: "to";
    }, {
        readonly type: "uint256";
        readonly name: "amount";
    }];
    readonly outputs: readonly [{
        readonly type: "bool";
    }];
}, {
    readonly name: "transferFrom";
    readonly type: "function";
    readonly stateMutability: "nonpayable";
    readonly inputs: readonly [{
        readonly type: "address";
        readonly name: "from";
    }, {
        readonly type: "address";
        readonly name: "to";
    }, {
        readonly type: "uint256";
        readonly name: "amount";
    }];
    readonly outputs: readonly [{
        readonly type: "bool";
    }];
}, {
    readonly name: "Transfer";
    readonly type: "event";
    readonly inputs: readonly [{
        readonly type: "address";
        readonly name: "from";
        readonly indexed: true;
    }, {
        readonly type: "address";
        readonly name: "to";
        readonly indexed: true;
    }, {
        readonly type: "uint256";
        readonly name: "value";
    }];
}, {
    readonly name: "Approval";
    readonly type: "event";
    readonly inputs: readonly [{
        readonly type: "address";
        readonly name: "owner";
        readonly indexed: true;
    }, {
        readonly type: "address";
        readonly name: "spender";
        readonly indexed: true;
    }, {
        readonly type: "uint256";
        readonly name: "value";
    }];
}];
declare const AMM_ABI: readonly [{
    readonly name: "tokenA";
    readonly type: "function";
    readonly stateMutability: "view";
    readonly inputs: readonly [];
    readonly outputs: readonly [{
        readonly type: "address";
    }];
}, {
    readonly name: "tokenB";
    readonly type: "function";
    readonly stateMutability: "view";
    readonly inputs: readonly [];
    readonly outputs: readonly [{
        readonly type: "address";
    }];
}, {
    readonly name: "reserveA";
    readonly type: "function";
    readonly stateMutability: "view";
    readonly inputs: readonly [];
    readonly outputs: readonly [{
        readonly type: "uint256";
    }];
}, {
    readonly name: "reserveB";
    readonly type: "function";
    readonly stateMutability: "view";
    readonly inputs: readonly [];
    readonly outputs: readonly [{
        readonly type: "uint256";
    }];
}, {
    readonly name: "getPrice";
    readonly type: "function";
    readonly stateMutability: "view";
    readonly inputs: readonly [];
    readonly outputs: readonly [{
        readonly type: "uint256";
    }];
}, {
    readonly name: "getAmountOut";
    readonly type: "function";
    readonly stateMutability: "view";
    readonly inputs: readonly [{
        readonly type: "address";
        readonly name: "tokenIn";
    }, {
        readonly type: "uint256";
        readonly name: "amountIn";
    }];
    readonly outputs: readonly [{
        readonly type: "uint256";
    }];
}, {
    readonly name: "swap";
    readonly type: "function";
    readonly stateMutability: "nonpayable";
    readonly inputs: readonly [{
        readonly type: "address";
        readonly name: "tokenIn";
    }, {
        readonly type: "uint256";
        readonly name: "amountIn";
    }, {
        readonly type: "uint256";
        readonly name: "minAmountOut";
    }];
    readonly outputs: readonly [{
        readonly type: "uint256";
    }];
}, {
    readonly name: "addLiquidity";
    readonly type: "function";
    readonly stateMutability: "nonpayable";
    readonly inputs: readonly [{
        readonly type: "uint256";
        readonly name: "amountA";
    }, {
        readonly type: "uint256";
        readonly name: "amountB";
    }];
    readonly outputs: readonly [{
        readonly type: "uint256";
    }];
}, {
    readonly name: "removeLiquidity";
    readonly type: "function";
    readonly stateMutability: "nonpayable";
    readonly inputs: readonly [{
        readonly type: "uint256";
        readonly name: "lpAmount";
    }];
    readonly outputs: readonly [{
        readonly type: "uint256";
    }, {
        readonly type: "uint256";
    }];
}, {
    readonly name: "balanceOf";
    readonly type: "function";
    readonly stateMutability: "view";
    readonly inputs: readonly [{
        readonly type: "address";
        readonly name: "owner";
    }];
    readonly outputs: readonly [{
        readonly type: "uint256";
    }];
}, {
    readonly name: "Swap";
    readonly type: "event";
    readonly inputs: readonly [{
        readonly type: "address";
        readonly name: "user";
        readonly indexed: true;
    }, {
        readonly type: "address";
        readonly name: "tokenIn";
    }, {
        readonly type: "uint256";
        readonly name: "amountIn";
    }, {
        readonly type: "uint256";
        readonly name: "amountOut";
    }];
}, {
    readonly name: "LiquidityAdded";
    readonly type: "event";
    readonly inputs: readonly [{
        readonly type: "address";
        readonly name: "user";
        readonly indexed: true;
    }, {
        readonly type: "uint256";
        readonly name: "amountA";
    }, {
        readonly type: "uint256";
        readonly name: "amountB";
    }, {
        readonly type: "uint256";
        readonly name: "liquidity";
    }];
}];
declare const ORACLE_ABI: readonly [{
    readonly name: "getPrice";
    readonly type: "function";
    readonly stateMutability: "view";
    readonly inputs: readonly [{
        readonly type: "bytes32";
        readonly name: "pair";
    }];
    readonly outputs: readonly [{
        readonly type: "uint256";
        readonly name: "price";
    }, {
        readonly type: "uint256";
        readonly name: "timestamp";
    }, {
        readonly type: "bool";
        readonly name: "isStale";
    }];
}, {
    readonly name: "submitPrice";
    readonly type: "function";
    readonly stateMutability: "nonpayable";
    readonly inputs: readonly [{
        readonly type: "bytes32";
        readonly name: "pair";
    }, {
        readonly type: "uint256";
        readonly name: "price";
    }];
    readonly outputs: readonly [];
}, {
    readonly name: "getSubmissionCount";
    readonly type: "function";
    readonly stateMutability: "view";
    readonly inputs: readonly [{
        readonly type: "bytes32";
        readonly name: "pair";
    }];
    readonly outputs: readonly [{
        readonly type: "uint256";
    }];
}];
declare const AGENT_REGISTRY_ABI: readonly [{
    readonly name: "getAgentCount";
    readonly type: "function";
    readonly stateMutability: "view";
    readonly inputs: readonly [];
    readonly outputs: readonly [{
        readonly type: "uint256";
    }];
}, {
    readonly name: "getActiveAgents";
    readonly type: "function";
    readonly stateMutability: "view";
    readonly inputs: readonly [];
    readonly outputs: readonly [{
        readonly type: "address[]";
    }];
}, {
    readonly name: "validateAgent";
    readonly type: "function";
    readonly stateMutability: "view";
    readonly inputs: readonly [{
        readonly type: "address";
        readonly name: "agent";
    }];
    readonly outputs: readonly [{
        readonly type: "bool";
    }];
}, {
    readonly name: "getRemainingBudget";
    readonly type: "function";
    readonly stateMutability: "view";
    readonly inputs: readonly [{
        readonly type: "address";
        readonly name: "agent";
    }];
    readonly outputs: readonly [{
        readonly type: "uint256";
    }];
}];
declare const WELCOME_BONUS_ABI: readonly [{
    readonly name: "claim";
    readonly type: "function";
    readonly stateMutability: "nonpayable";
    readonly inputs: readonly [];
    readonly outputs: readonly [];
}, {
    readonly name: "claimFor";
    readonly type: "function";
    readonly stateMutability: "nonpayable";
    readonly inputs: readonly [{
        readonly type: "address";
        readonly name: "beneficiary";
    }];
    readonly outputs: readonly [];
}, {
    readonly name: "canClaim";
    readonly type: "function";
    readonly stateMutability: "view";
    readonly inputs: readonly [{
        readonly type: "address";
        readonly name: "user";
    }];
    readonly outputs: readonly [{
        readonly type: "bool";
        readonly name: "canClaimResult";
    }, {
        readonly type: "uint256";
        readonly name: "amount";
    }];
}, {
    readonly name: "claimed";
    readonly type: "function";
    readonly stateMutability: "view";
    readonly inputs: readonly [{
        readonly type: "address";
        readonly name: "user";
    }];
    readonly outputs: readonly [{
        readonly type: "bool";
    }];
}, {
    readonly name: "bonusAmount";
    readonly type: "function";
    readonly stateMutability: "view";
    readonly inputs: readonly [];
    readonly outputs: readonly [{
        readonly type: "uint256";
    }];
}, {
    readonly name: "totalClaims";
    readonly type: "function";
    readonly stateMutability: "view";
    readonly inputs: readonly [];
    readonly outputs: readonly [{
        readonly type: "uint256";
    }];
}];
declare const THRYX_TOKEN_ABI: readonly [{
    readonly name: "name";
    readonly type: "function";
    readonly stateMutability: "view";
    readonly inputs: readonly [];
    readonly outputs: readonly [{
        readonly type: "string";
    }];
}, {
    readonly name: "symbol";
    readonly type: "function";
    readonly stateMutability: "view";
    readonly inputs: readonly [];
    readonly outputs: readonly [{
        readonly type: "string";
    }];
}, {
    readonly name: "decimals";
    readonly type: "function";
    readonly stateMutability: "view";
    readonly inputs: readonly [];
    readonly outputs: readonly [{
        readonly type: "uint8";
    }];
}, {
    readonly name: "totalSupply";
    readonly type: "function";
    readonly stateMutability: "view";
    readonly inputs: readonly [];
    readonly outputs: readonly [{
        readonly type: "uint256";
    }];
}, {
    readonly name: "balanceOf";
    readonly type: "function";
    readonly stateMutability: "view";
    readonly inputs: readonly [{
        readonly type: "address";
        readonly name: "owner";
    }];
    readonly outputs: readonly [{
        readonly type: "uint256";
    }];
}, {
    readonly name: "transfer";
    readonly type: "function";
    readonly stateMutability: "nonpayable";
    readonly inputs: readonly [{
        readonly type: "address";
        readonly name: "to";
    }, {
        readonly type: "uint256";
        readonly name: "amount";
    }];
    readonly outputs: readonly [{
        readonly type: "bool";
    }];
}, {
    readonly name: "approve";
    readonly type: "function";
    readonly stateMutability: "nonpayable";
    readonly inputs: readonly [{
        readonly type: "address";
        readonly name: "spender";
    }, {
        readonly type: "uint256";
        readonly name: "amount";
    }];
    readonly outputs: readonly [{
        readonly type: "bool";
    }];
}];
interface ThryxSDKConfig {
    rpcUrl?: string;
    privateKey?: string;
    contracts?: ContractAddresses;
}
interface ContractAddresses {
    usdc?: Address;
    weth?: Address;
    amm?: Address;
    oracle?: Address;
    registry?: Address;
    thryxToken?: Address;
    welcomeBonus?: Address;
}
interface PoolState {
    reserveA: bigint;
    reserveB: bigint;
    price: bigint;
}
interface PriceData {
    price: bigint;
    timestamp: number;
    isStale: boolean;
}
/**
 * Bridge wallet address on Base mainnet
 * Send ETH to this address on Base to receive ETH on THRYX
 */
declare const BRIDGE_WALLET: Address;
/**
 * Base USDC contract address
 */
declare const BASE_USDC: Address;
declare const DEFAULT_CONTRACTS: ContractAddresses;
declare class ThryxSDK {
    readonly publicClient: PublicClient;
    readonly walletClient: WalletClient | null;
    readonly account: PrivateKeyAccount | null;
    readonly contracts: ContractAddresses;
    readonly chainId = 77777;
    constructor(config?: ThryxSDKConfig);
    get address(): Address | null;
    getBlockNumber(): Promise<bigint>;
    getBalance(address?: Address): Promise<bigint>;
    getChainId(): Promise<number>;
    getTokenBalance(tokenAddress: Address, owner?: Address): Promise<bigint>;
    getUsdcBalance(owner?: Address): Promise<bigint>;
    getWethBalance(owner?: Address): Promise<bigint>;
    getThryxBalance(owner?: Address): Promise<bigint>;
    approve(tokenAddress: Address, spender: Address, amount: bigint): Promise<Hash>;
    getPoolState(): Promise<PoolState>;
    getAmountOut(tokenIn: Address, amountIn: bigint): Promise<bigint>;
    swap(tokenIn: Address, amountIn: bigint, minAmountOut: bigint): Promise<Hash>;
    getPrice(pair: string): Promise<PriceData>;
    canClaimBonus(address?: Address): Promise<{
        canClaim: boolean;
        amount: bigint;
    }>;
    claimBonus(): Promise<Hash>;
    getAgentCount(): Promise<bigint>;
    getActiveAgents(): Promise<readonly Address[]>;
    isAgentValid(agent: Address): Promise<boolean>;
    /**
     * Get a bridge client for Base -> THRYX bridging
     * @param baseRpcUrl - RPC URL for Base mainnet
     * @param privateKey - Private key for signing transactions on Base
     */
    createBridgeClient(baseRpcUrl?: string, privateKey?: string): BridgeClient;
    private hashPair;
    formatEther(wei: bigint): string;
    parseEther(ether: string): bigint;
}
interface BridgeResult {
    success: boolean;
    txHash?: Hash;
    error?: string;
    amount?: string;
}
/**
 * Bridge client for Base -> THRYX transfers
 *
 * @example
 * ```typescript
 * const bridge = new BridgeClient('https://mainnet.base.org', '0xprivatekey');
 *
 * // Bridge 0.01 ETH from Base to THRYX
 * const result = await bridge.bridgeETH('0.01');
 * console.log('Bridge tx:', result.txHash);
 * ```
 */
declare class BridgeClient {
    readonly publicClient: PublicClient;
    readonly walletClient: WalletClient | null;
    readonly account: PrivateKeyAccount | null;
    constructor(baseRpcUrl?: string, privateKey?: string);
    get address(): Address | null;
    /**
     * Get ETH balance on Base
     */
    getBaseBalance(address?: Address): Promise<bigint>;
    /**
     * Get USDC balance on Base
     */
    getBaseUsdcBalance(address?: Address): Promise<bigint>;
    /**
     * Bridge ETH from Base to THRYX
     * Sends ETH to the bridge wallet on Base, which triggers automatic minting on THRYX
     *
     * @param amount - Amount of ETH to bridge (e.g., "0.01")
     * @returns Bridge result with transaction hash
     */
    bridgeETH(amount: string): Promise<BridgeResult>;
    /**
     * Bridge USDC from Base to THRYX
     * Sends USDC to the bridge wallet on Base, which triggers automatic minting on THRYX
     *
     * @param amount - Amount of USDC to bridge (e.g., "100" for 100 USDC)
     * @returns Bridge result with transaction hash
     */
    bridgeUSDC(amount: string): Promise<BridgeResult>;
    /**
     * Get the bridge wallet address
     */
    getBridgeWallet(): Address;
}

export { AGENT_REGISTRY_ABI, AMM_ABI, BASE_CHAIN, BASE_USDC, BRIDGE_WALLET, BridgeClient, type BridgeResult, type ContractAddresses, DEFAULT_CONTRACTS, ERC20_ABI, ORACLE_ABI, type PoolState, type PriceData, THRYX_CHAIN, THRYX_TOKEN_ABI, ThryxSDK, type ThryxSDKConfig, WELCOME_BONUS_ABI, ThryxSDK as default };
