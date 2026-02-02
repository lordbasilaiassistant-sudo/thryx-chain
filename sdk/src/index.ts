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

import {
  createPublicClient,
  createWalletClient,
  http,
  parseAbi,
  formatEther,
  parseEther,
  type PublicClient,
  type WalletClient,
  type Address,
  type Hash,
  type Chain,
} from 'viem';
import { privateKeyToAccount, type PrivateKeyAccount } from 'viem/accounts';

// ==================== Chain Configuration ====================

/**
 * THRYX Mainnet chain configuration
 */
export const THRYX_CHAIN: Chain = {
  id: 77777,
  name: 'THRYX Mainnet',
  nativeCurrency: {
    decimals: 18,
    name: 'Ether',
    symbol: 'ETH',
  },
  rpcUrls: {
    default: { http: ['https://crispy-goggles-v6jg77gvqwqv3pxpg-8545.app.github.dev'] },
    public: { http: ['https://crispy-goggles-v6jg77gvqwqv3pxpg-8545.app.github.dev'] },
  },
  blockExplorers: {
    default: { name: 'THRYX Explorer', url: 'https://thryx.mom' },
  },
};

/**
 * Base Mainnet (L1 for THRYX)
 */
export const BASE_CHAIN: Chain = {
  id: 8453,
  name: 'Base',
  nativeCurrency: {
    decimals: 18,
    name: 'Ether',
    symbol: 'ETH',
  },
  rpcUrls: {
    default: { http: ['https://mainnet.base.org'] },
    public: { http: ['https://mainnet.base.org'] },
  },
  blockExplorers: {
    default: { name: 'Basescan', url: 'https://basescan.org' },
  },
};

// ==================== ABIs ====================

export const ERC20_ABI = parseAbi([
  'function name() view returns (string)',
  'function symbol() view returns (string)',
  'function decimals() view returns (uint8)',
  'function totalSupply() view returns (uint256)',
  'function balanceOf(address owner) view returns (uint256)',
  'function allowance(address owner, address spender) view returns (uint256)',
  'function approve(address spender, uint256 amount) returns (bool)',
  'function transfer(address to, uint256 amount) returns (bool)',
  'function transferFrom(address from, address to, uint256 amount) returns (bool)',
  'event Transfer(address indexed from, address indexed to, uint256 value)',
  'event Approval(address indexed owner, address indexed spender, uint256 value)',
]);

export const AMM_ABI = parseAbi([
  'function tokenA() view returns (address)',
  'function tokenB() view returns (address)',
  'function reserveA() view returns (uint256)',
  'function reserveB() view returns (uint256)',
  'function getPrice() view returns (uint256)',
  'function getAmountOut(address tokenIn, uint256 amountIn) view returns (uint256)',
  'function swap(address tokenIn, uint256 amountIn, uint256 minAmountOut) returns (uint256)',
  'function addLiquidity(uint256 amountA, uint256 amountB) returns (uint256)',
  'function removeLiquidity(uint256 lpAmount) returns (uint256, uint256)',
  'function balanceOf(address owner) view returns (uint256)',
  'event Swap(address indexed user, address tokenIn, uint256 amountIn, uint256 amountOut)',
  'event LiquidityAdded(address indexed user, uint256 amountA, uint256 amountB, uint256 liquidity)',
]);

export const ORACLE_ABI = parseAbi([
  'function getPrice(bytes32 pair) view returns (uint256 price, uint256 timestamp, bool isStale)',
  'function submitPrice(bytes32 pair, uint256 price)',
  'function getSubmissionCount(bytes32 pair) view returns (uint256)',
]);

export const AGENT_REGISTRY_ABI = parseAbi([
  'function getAgentCount() view returns (uint256)',
  'function getActiveAgents() view returns (address[])',
  'function validateAgent(address agent) view returns (bool)',
  'function getRemainingBudget(address agent) view returns (uint256)',
]);

export const WELCOME_BONUS_ABI = parseAbi([
  'function claim()',
  'function claimFor(address beneficiary)',
  'function canClaim(address user) view returns (bool canClaimResult, uint256 amount)',
  'function claimed(address user) view returns (bool)',
  'function bonusAmount() view returns (uint256)',
  'function totalClaims() view returns (uint256)',
]);

export const THRYX_TOKEN_ABI = parseAbi([
  'function name() view returns (string)',
  'function symbol() view returns (string)',
  'function decimals() view returns (uint8)',
  'function totalSupply() view returns (uint256)',
  'function balanceOf(address owner) view returns (uint256)',
  'function transfer(address to, uint256 amount) returns (bool)',
  'function approve(address spender, uint256 amount) returns (bool)',
]);

// ==================== Types ====================

export interface ThryxSDKConfig {
  rpcUrl?: string;
  privateKey?: string;
  contracts?: ContractAddresses;
}

export interface ContractAddresses {
  usdc?: Address;
  weth?: Address;
  amm?: Address;
  oracle?: Address;
  registry?: Address;
  thryxToken?: Address;
  welcomeBonus?: Address;
}

export interface PoolState {
  reserveA: bigint;
  reserveB: bigint;
  price: bigint;
}

export interface PriceData {
  price: bigint;
  timestamp: number;
  isStale: boolean;
}

// ==================== Bridge Configuration ====================

/**
 * Bridge wallet address on Base mainnet
 * Send ETH to this address on Base to receive ETH on THRYX
 */
export const BRIDGE_WALLET: Address = '0x338304e35841d2Fa6849EF855f6beBD8988C65B8';

/**
 * Base USDC contract address
 */
export const BASE_USDC: Address = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913';

// ==================== Default Contract Addresses ====================

export const DEFAULT_CONTRACTS: ContractAddresses = {
  usdc: '0x5f3f1dBD7B74C6B46e8c44f98792A1dAf8d69154',
  weth: '0xb7278A61aa25c888815aFC32Ad3cC52fF24fE575',
  amm: '0x2bdCC0de6bE1f7D2ee689a0342D76F52E8EFABa3',
  oracle: '0x7969c5eD335650692Bc04293B07F5BF2e7A673C0',
  registry: '0xCD8a1C3ba11CF5ECfa6267617243239504a98d90',
  thryxToken: '0x2B0d36FACD61B71CC05ab8F3D2355ec3631C0dd5',
  welcomeBonus: '0xCace1b78160AE76398F486c8a18044da0d66d86D',
};

// ==================== SDK Class ====================

export class ThryxSDK {
  public readonly publicClient: PublicClient;
  public readonly walletClient: WalletClient | null;
  public readonly account: PrivateKeyAccount | null;
  public readonly contracts: ContractAddresses;
  public readonly chainId = 77777;

  constructor(config: ThryxSDKConfig = {}) {
    const rpcUrl = config.rpcUrl || 'http://localhost:8545';
    this.contracts = { ...DEFAULT_CONTRACTS, ...config.contracts };

    // Create public client (read-only)
    this.publicClient = createPublicClient({
      chain: THRYX_CHAIN,
      transport: http(rpcUrl),
    });

    // Create wallet client if private key provided
    if (config.privateKey) {
      this.account = privateKeyToAccount(config.privateKey as `0x${string}`);
      this.walletClient = createWalletClient({
        account: this.account,
        chain: THRYX_CHAIN,
        transport: http(rpcUrl),
      });
    } else {
      this.account = null;
      this.walletClient = null;
    }
  }

  // ==================== Connection ====================

  get address(): Address | null {
    return this.account?.address || null;
  }

  async getBlockNumber(): Promise<bigint> {
    return this.publicClient.getBlockNumber();
  }

  async getBalance(address?: Address): Promise<bigint> {
    const addr = address || this.address;
    if (!addr) throw new Error('No address provided');
    return this.publicClient.getBalance({ address: addr });
  }

  async getChainId(): Promise<number> {
    return this.publicClient.getChainId();
  }

  // ==================== Token Operations ====================

  async getTokenBalance(tokenAddress: Address, owner?: Address): Promise<bigint> {
    const addr = owner || this.address;
    if (!addr) throw new Error('No address provided');

    return this.publicClient.readContract({
      address: tokenAddress,
      abi: ERC20_ABI,
      functionName: 'balanceOf',
      args: [addr],
    });
  }

  async getUsdcBalance(owner?: Address): Promise<bigint> {
    if (!this.contracts.usdc) throw new Error('USDC address not configured');
    return this.getTokenBalance(this.contracts.usdc, owner);
  }

  async getWethBalance(owner?: Address): Promise<bigint> {
    if (!this.contracts.weth) throw new Error('WETH address not configured');
    return this.getTokenBalance(this.contracts.weth, owner);
  }

  async getThryxBalance(owner?: Address): Promise<bigint> {
    if (!this.contracts.thryxToken) throw new Error('THRYX Token address not configured');
    return this.getTokenBalance(this.contracts.thryxToken, owner);
  }

  async approve(tokenAddress: Address, spender: Address, amount: bigint): Promise<Hash> {
    if (!this.walletClient || !this.account) throw new Error('Wallet not connected');

    return this.walletClient.writeContract({
      address: tokenAddress,
      abi: ERC20_ABI,
      functionName: 'approve',
      args: [spender, amount],
      chain: THRYX_CHAIN,
      account: this.account,
    });
  }

  // ==================== AMM Operations ====================

  async getPoolState(): Promise<PoolState> {
    if (!this.contracts.amm) throw new Error('AMM address not configured');

    const [reserveA, reserveB, price] = await Promise.all([
      this.publicClient.readContract({
        address: this.contracts.amm,
        abi: AMM_ABI,
        functionName: 'reserveA',
      }),
      this.publicClient.readContract({
        address: this.contracts.amm,
        abi: AMM_ABI,
        functionName: 'reserveB',
      }),
      this.publicClient.readContract({
        address: this.contracts.amm,
        abi: AMM_ABI,
        functionName: 'getPrice',
      }),
    ]);

    return { reserveA, reserveB, price };
  }

  async getAmountOut(tokenIn: Address, amountIn: bigint): Promise<bigint> {
    if (!this.contracts.amm) throw new Error('AMM address not configured');

    return this.publicClient.readContract({
      address: this.contracts.amm,
      abi: AMM_ABI,
      functionName: 'getAmountOut',
      args: [tokenIn, amountIn],
    });
  }

  async swap(tokenIn: Address, amountIn: bigint, minAmountOut: bigint): Promise<Hash> {
    if (!this.walletClient || !this.account) throw new Error('Wallet not connected');
    if (!this.contracts.amm) throw new Error('AMM address not configured');

    // First approve
    await this.approve(tokenIn, this.contracts.amm, amountIn);

    // Then swap
    return this.walletClient.writeContract({
      address: this.contracts.amm,
      abi: AMM_ABI,
      functionName: 'swap',
      args: [tokenIn, amountIn, minAmountOut],
      chain: THRYX_CHAIN,
      account: this.account,
    });
  }

  // ==================== Oracle Operations ====================

  async getPrice(pair: string): Promise<PriceData> {
    if (!this.contracts.oracle) throw new Error('Oracle address not configured');

    const pairHash = this.hashPair(pair);
    const [price, timestamp, isStale] = await this.publicClient.readContract({
      address: this.contracts.oracle,
      abi: ORACLE_ABI,
      functionName: 'getPrice',
      args: [pairHash],
    });

    return {
      price,
      timestamp: Number(timestamp),
      isStale,
    };
  }

  // ==================== Welcome Bonus ====================

  async canClaimBonus(address?: Address): Promise<{ canClaim: boolean; amount: bigint }> {
    if (!this.contracts.welcomeBonus) throw new Error('WelcomeBonus address not configured');
    const addr = address || this.address;
    if (!addr) throw new Error('No address provided');

    const [canClaim, amount] = await this.publicClient.readContract({
      address: this.contracts.welcomeBonus,
      abi: WELCOME_BONUS_ABI,
      functionName: 'canClaim',
      args: [addr],
    });

    return { canClaim, amount };
  }

  async claimBonus(): Promise<Hash> {
    if (!this.walletClient || !this.account) throw new Error('Wallet not connected');
    if (!this.contracts.welcomeBonus) throw new Error('WelcomeBonus address not configured');

    return this.walletClient.writeContract({
      address: this.contracts.welcomeBonus,
      abi: WELCOME_BONUS_ABI,
      functionName: 'claim',
      chain: THRYX_CHAIN,
      account: this.account,
    });
  }

  // ==================== Agent Registry ====================

  async getAgentCount(): Promise<bigint> {
    if (!this.contracts.registry) throw new Error('Registry address not configured');

    return this.publicClient.readContract({
      address: this.contracts.registry,
      abi: AGENT_REGISTRY_ABI,
      functionName: 'getAgentCount',
    });
  }

  async getActiveAgents(): Promise<readonly Address[]> {
    if (!this.contracts.registry) throw new Error('Registry address not configured');

    return this.publicClient.readContract({
      address: this.contracts.registry,
      abi: AGENT_REGISTRY_ABI,
      functionName: 'getActiveAgents',
    });
  }

  async isAgentValid(agent: Address): Promise<boolean> {
    if (!this.contracts.registry) throw new Error('Registry address not configured');

    return this.publicClient.readContract({
      address: this.contracts.registry,
      abi: AGENT_REGISTRY_ABI,
      functionName: 'validateAgent',
      args: [agent],
    });
  }

  // ==================== Bridge Operations ====================

  /**
   * Get a bridge client for Base -> THRYX bridging
   * @param baseRpcUrl - RPC URL for Base mainnet
   * @param privateKey - Private key for signing transactions on Base
   */
  createBridgeClient(baseRpcUrl: string = 'https://mainnet.base.org', privateKey?: string): BridgeClient {
    return new BridgeClient(baseRpcUrl, privateKey);
  }

  // ==================== Utilities ====================

  private hashPair(pair: string): `0x${string}` {
    // Simple keccak256 hash
    const encoder = new TextEncoder();
    const data = encoder.encode(pair);
    // In a real implementation, use proper keccak256
    return `0x${Buffer.from(data).toString('hex').padEnd(64, '0')}` as `0x${string}`;
  }

  formatEther(wei: bigint): string {
    return formatEther(wei);
  }

  parseEther(ether: string): bigint {
    return parseEther(ether);
  }
}

// ==================== Bridge Client ====================

export interface BridgeResult {
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
export class BridgeClient {
  public readonly publicClient: PublicClient;
  public readonly walletClient: WalletClient | null;
  public readonly account: PrivateKeyAccount | null;

  constructor(baseRpcUrl: string = 'https://mainnet.base.org', privateKey?: string) {
    // Create public client for Base
    this.publicClient = createPublicClient({
      chain: BASE_CHAIN,
      transport: http(baseRpcUrl),
    });

    // Create wallet client if private key provided
    if (privateKey) {
      this.account = privateKeyToAccount(privateKey as `0x${string}`);
      this.walletClient = createWalletClient({
        account: this.account,
        chain: BASE_CHAIN,
        transport: http(baseRpcUrl),
      });
    } else {
      this.account = null;
      this.walletClient = null;
    }
  }

  get address(): Address | null {
    return this.account?.address || null;
  }

  /**
   * Get ETH balance on Base
   */
  async getBaseBalance(address?: Address): Promise<bigint> {
    const addr = address || this.address;
    if (!addr) throw new Error('No address provided');
    return this.publicClient.getBalance({ address: addr });
  }

  /**
   * Get USDC balance on Base
   */
  async getBaseUsdcBalance(address?: Address): Promise<bigint> {
    const addr = address || this.address;
    if (!addr) throw new Error('No address provided');

    return this.publicClient.readContract({
      address: BASE_USDC,
      abi: ERC20_ABI,
      functionName: 'balanceOf',
      args: [addr],
    });
  }

  /**
   * Bridge ETH from Base to THRYX
   * Sends ETH to the bridge wallet on Base, which triggers automatic minting on THRYX
   * 
   * @param amount - Amount of ETH to bridge (e.g., "0.01")
   * @returns Bridge result with transaction hash
   */
  async bridgeETH(amount: string): Promise<BridgeResult> {
    if (!this.walletClient || !this.account) {
      return { success: false, error: 'Wallet not connected - provide privateKey in constructor' };
    }

    try {
      const amountWei = parseEther(amount);
      
      // Check balance
      const balance = await this.getBaseBalance();
      if (balance < amountWei) {
        return { 
          success: false, 
          error: `Insufficient balance. Have ${formatEther(balance)} ETH, need ${amount} ETH` 
        };
      }

      // Send to bridge wallet
      const txHash = await this.walletClient.sendTransaction({
        to: BRIDGE_WALLET,
        value: amountWei,
        chain: BASE_CHAIN,
        account: this.account,
      });

      return {
        success: true,
        txHash,
        amount,
      };
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : String(error),
      };
    }
  }

  /**
   * Bridge USDC from Base to THRYX
   * Sends USDC to the bridge wallet on Base, which triggers automatic minting on THRYX
   * 
   * @param amount - Amount of USDC to bridge (e.g., "100" for 100 USDC)
   * @returns Bridge result with transaction hash
   */
  async bridgeUSDC(amount: string): Promise<BridgeResult> {
    if (!this.walletClient || !this.account) {
      return { success: false, error: 'Wallet not connected - provide privateKey in constructor' };
    }

    try {
      const amountUnits = BigInt(Math.floor(parseFloat(amount) * 1e6)); // USDC has 6 decimals
      
      // Check balance
      const balance = await this.getBaseUsdcBalance();
      if (balance < amountUnits) {
        return { 
          success: false, 
          error: `Insufficient USDC balance. Have ${Number(balance) / 1e6} USDC, need ${amount} USDC` 
        };
      }

      // Transfer USDC to bridge wallet
      const txHash = await this.walletClient.writeContract({
        address: BASE_USDC,
        abi: ERC20_ABI,
        functionName: 'transfer',
        args: [BRIDGE_WALLET, amountUnits],
        chain: BASE_CHAIN,
        account: this.account,
      });

      return {
        success: true,
        txHash,
        amount,
      };
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : String(error),
      };
    }
  }

  /**
   * Get the bridge wallet address
   */
  getBridgeWallet(): Address {
    return BRIDGE_WALLET;
  }
}

// ==================== Exports ====================

export default ThryxSDK;
export { formatEther, parseEther } from 'viem';
