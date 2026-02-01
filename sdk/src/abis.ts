/**
 * Contract ABIs for Thryx SDK
 */

export const ABIS = {
  ERC20: [
    'function approve(address spender, uint256 amount) returns (bool)',
    'function balanceOf(address account) view returns (uint256)',
    'function decimals() view returns (uint8)',
    'function transfer(address to, uint256 amount) returns (bool)',
    'function transferFrom(address from, address to, uint256 amount) returns (bool)',
    'function allowance(address owner, address spender) view returns (uint256)',
  ],

  AgentRegistry: [
    'function registerAgent(address agentAddress, uint256 dailyBudget, bytes32 permissions, string metadata)',
    'function validateAgent(address agentAddress) view returns (bool)',
    'function hasPermission(address agentAddress, bytes32 permission) view returns (bool)',
    'function recordSpending(address agentAddress, uint256 amount)',
    'function getRemainingBudget(address agentAddress) view returns (uint256)',
    'function deactivateAgent(address agentAddress)',
    'function updateBudget(address agentAddress, uint256 newBudget)',
    'function getAgentCount() view returns (uint256)',
    'function getActiveAgents() view returns (address[])',
    'function agents(address) view returns (address owner, uint256 dailyBudget, uint256 spentToday, uint256 lastResetTimestamp, bytes32 permissions, bool isActive, string metadata)',
  ],

  SimpleAMM: [
    'function addLiquidity(uint256 amountA, uint256 amountB) returns (uint256 liquidity)',
    'function removeLiquidity(uint256 liquidity) returns (uint256 amountA, uint256 amountB)',
    'function swap(address tokenIn, uint256 amountIn, uint256 minAmountOut) returns (uint256 amountOut)',
    'function getAmountOut(address tokenIn, uint256 amountIn) view returns (uint256)',
    'function getPrice() view returns (uint256)',
    'function reserveA() view returns (uint256)',
    'function reserveB() view returns (uint256)',
    'function totalSupply() view returns (uint256)',
    'function balanceOf(address account) view returns (uint256)',
  ],

  AgentOracle: [
    'function submitPrice(bytes32 pair, uint256 price)',
    'function getPrice(bytes32 pair) view returns (uint256 price, uint256 timestamp, bool isStale)',
    'function getActivePairCount() view returns (uint256)',
    'function getSubmissionCount(bytes32 pair) view returns (uint256)',
    'function getSubmitters(bytes32 pair) view returns (address[])',
  ],

  IntentMempool: [
    'function submitIntent(bytes32 goal, bytes constraints, uint256 maxCost, uint256 deadlineSeconds) returns (uint256 intentId)',
    'function fulfillIntent(uint256 intentId, bytes solution, uint256 actualCost)',
    'function cancelIntent(uint256 intentId)',
    'function cleanupExpired()',
    'function getPendingIntents() view returns (uint256[])',
    'function getIntent(uint256 intentId) view returns (tuple(uint256 id, address creator, bytes32 goal, bytes constraints, uint256 maxCost, uint256 deadline, uint8 status, address solver, bytes solution, uint256 actualCost))',
  ],

  StablecoinGas: [
    'function depositGas(uint256 amount)',
    'function payForGas(address agent, uint256 gasUsed) returns (uint256)',
    'function withdrawGas(uint256 amount)',
    'function distributeFees()',
    'function getGasBalance(address account) view returns (uint256)',
    'function gasPriceUsdc() view returns (uint256)',
    'function totalFeesCollected() view returns (uint256)',
    'function humanFeesAccrued() view returns (uint256)',
  ],
};

export default ABIS;
