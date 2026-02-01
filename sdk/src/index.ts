/**
 * Thryx SDK
 * TypeScript SDK for interacting with the Thryx AI-native blockchain
 */

import { ethers, Contract, Wallet, JsonRpcProvider, TransactionReceipt } from 'ethers';
import { ABIS } from './abis';

export interface AgentInfo {
  address: string;
  owner: string;
  dailyBudget: bigint;
  spentToday: bigint;
  permissions: string;
  isActive: boolean;
  metadata: string;
}

export interface PriceData {
  price: bigint;
  timestamp: number;
  isStale: boolean;
}

export interface PoolState {
  reserveA: bigint;
  reserveB: bigint;
  price: bigint;
  tvl: bigint;
}

export interface ThryxContracts {
  usdc: string;
  weth: string;
  registry: string;
  gasContract: string;
  amm: string;
  oracle: string;
  intentMempool: string;
}

export class ThryxSDK {
  private provider: JsonRpcProvider;
  private signer: Wallet | null = null;
  private contracts: ThryxContracts;

  // Contract instances
  private usdc: Contract | null = null;
  private weth: Contract | null = null;
  private registry: Contract | null = null;
  private amm: Contract | null = null;
  private oracle: Contract | null = null;
  private intentMempool: Contract | null = null;

  constructor(rpcUrl: string, contracts: ThryxContracts, privateKey?: string) {
    this.provider = new JsonRpcProvider(rpcUrl);
    this.contracts = contracts;

    if (privateKey) {
      this.signer = new Wallet(privateKey, this.provider);
    }

    this._initContracts();
  }

  private _initContracts(): void {
    const signerOrProvider = this.signer || this.provider;

    this.usdc = new Contract(this.contracts.usdc, ABIS.ERC20, signerOrProvider);
    this.weth = new Contract(this.contracts.weth, ABIS.ERC20, signerOrProvider);
    this.registry = new Contract(this.contracts.registry, ABIS.AgentRegistry, signerOrProvider);
    this.amm = new Contract(this.contracts.amm, ABIS.SimpleAMM, signerOrProvider);
    this.oracle = new Contract(this.contracts.oracle, ABIS.AgentOracle, signerOrProvider);
    this.intentMempool = new Contract(this.contracts.intentMempool, ABIS.IntentMempool, signerOrProvider);
  }

  // ==================== Connection ====================

  async connect(privateKey: string): Promise<string> {
    this.signer = new Wallet(privateKey, this.provider);
    this._initContracts();
    return this.signer.address;
  }

  async getBlockNumber(): Promise<number> {
    return this.provider.getBlockNumber();
  }

  getAddress(): string | null {
    return this.signer?.address || null;
  }

  // ==================== Agent Management ====================

  async createAgent(
    dailyBudget: bigint,
    permissions: string,
    metadata: string
  ): Promise<TransactionReceipt | null> {
    if (!this.signer || !this.registry) throw new Error('Not connected');

    const permHash = ethers.keccak256(ethers.toUtf8Bytes(permissions));
    const tx = await this.registry.registerAgent(
      this.signer.address,
      dailyBudget,
      permHash,
      metadata
    );
    return tx.wait();
  }

  async getAgentInfo(address: string): Promise<AgentInfo | null> {
    if (!this.registry) return null;

    const agent = await this.registry.agents(address);
    if (agent.owner === ethers.ZeroAddress) return null;

    return {
      address,
      owner: agent.owner,
      dailyBudget: agent.dailyBudget,
      spentToday: agent.spentToday,
      permissions: agent.permissions,
      isActive: agent.isActive,
      metadata: agent.metadata,
    };
  }

  async getActiveAgents(): Promise<string[]> {
    if (!this.registry) return [];
    return this.registry.getActiveAgents();
  }

  async getRemainingBudget(address: string): Promise<bigint> {
    if (!this.registry) return 0n;
    return this.registry.getRemainingBudget(address);
  }

  // ==================== DEX Operations ====================

  async swap(
    tokenIn: string,
    amountIn: bigint,
    minAmountOut: bigint
  ): Promise<TransactionReceipt | null> {
    if (!this.signer || !this.amm) throw new Error('Not connected');

    // Approve token
    const token = new Contract(tokenIn, ABIS.ERC20, this.signer);
    const approveTx = await token.approve(this.contracts.amm, amountIn);
    await approveTx.wait();

    // Execute swap
    const swapTx = await this.amm.swap(tokenIn, amountIn, minAmountOut);
    return swapTx.wait();
  }

  async addLiquidity(amountA: bigint, amountB: bigint): Promise<TransactionReceipt | null> {
    if (!this.signer || !this.amm || !this.usdc || !this.weth) {
      throw new Error('Not connected');
    }

    // Approve both tokens
    const approveA = await this.usdc.approve(this.contracts.amm, amountA);
    await approveA.wait();
    const approveB = await this.weth.approve(this.contracts.amm, amountB);
    await approveB.wait();

    // Add liquidity
    const tx = await this.amm.addLiquidity(amountA, amountB);
    return tx.wait();
  }

  async getAmountOut(tokenIn: string, amountIn: bigint): Promise<bigint> {
    if (!this.amm) return 0n;
    return this.amm.getAmountOut(tokenIn, amountIn);
  }

  async getPoolState(): Promise<PoolState> {
    if (!this.amm) {
      return { reserveA: 0n, reserveB: 0n, price: 0n, tvl: 0n };
    }

    const [reserveA, reserveB, price] = await Promise.all([
      this.amm.reserveA(),
      this.amm.reserveB(),
      this.amm.getPrice(),
    ]);

    return {
      reserveA,
      reserveB,
      price,
      tvl: reserveA * 2n, // Approximate TVL in USDC terms
    };
  }

  // ==================== Oracle Operations ====================

  async submitPrice(pair: string, price: bigint): Promise<TransactionReceipt | null> {
    if (!this.signer || !this.oracle) throw new Error('Not connected');

    const pairHash = ethers.keccak256(ethers.toUtf8Bytes(pair));
    const tx = await this.oracle.submitPrice(pairHash, price);
    return tx.wait();
  }

  async getPrice(pair: string): Promise<PriceData> {
    if (!this.oracle) {
      return { price: 0n, timestamp: 0, isStale: true };
    }

    const pairHash = ethers.keccak256(ethers.toUtf8Bytes(pair));
    const [price, timestamp, isStale] = await this.oracle.getPrice(pairHash);

    return {
      price,
      timestamp: Number(timestamp),
      isStale,
    };
  }

  // ==================== Intent Operations ====================

  async submitIntent(
    goal: string,
    constraints: string,
    maxCost: bigint,
    deadlineSeconds: number
  ): Promise<{ intentId: bigint; receipt: TransactionReceipt | null }> {
    if (!this.signer || !this.intentMempool || !this.usdc) {
      throw new Error('Not connected');
    }

    // Approve USDC for max cost
    const approveTx = await this.usdc.approve(this.contracts.intentMempool, maxCost);
    await approveTx.wait();

    // Submit intent
    const goalHash = ethers.keccak256(ethers.toUtf8Bytes(goal));
    const constraintsBytes = ethers.toUtf8Bytes(constraints);

    const tx = await this.intentMempool.submitIntent(
      goalHash,
      constraintsBytes,
      maxCost,
      deadlineSeconds
    );
    const receipt = await tx.wait();

    // Parse intent ID from events
    const intentId = 0n; // Would parse from receipt logs

    return { intentId, receipt };
  }

  async fulfillIntent(
    intentId: bigint,
    solution: string,
    actualCost: bigint
  ): Promise<TransactionReceipt | null> {
    if (!this.signer || !this.intentMempool) throw new Error('Not connected');

    const solutionBytes = ethers.toUtf8Bytes(solution);
    const tx = await this.intentMempool.fulfillIntent(intentId, solutionBytes, actualCost);
    return tx.wait();
  }

  // ==================== Token Operations ====================

  async getUsdcBalance(address?: string): Promise<bigint> {
    if (!this.usdc) return 0n;
    return this.usdc.balanceOf(address || this.signer?.address);
  }

  async getWethBalance(address?: string): Promise<bigint> {
    if (!this.weth) return 0n;
    return this.weth.balanceOf(address || this.signer?.address);
  }
}

// Export types and utilities
export { ABIS } from './abis';
export default ThryxSDK;
