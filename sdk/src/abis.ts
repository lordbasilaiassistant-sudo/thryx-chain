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

  // ==================== Creator Coins (Like Zora) ====================
  
  CreatorCoin: [
    // ERC20
    'function name() view returns (string)',
    'function symbol() view returns (string)',
    'function decimals() view returns (uint8)',
    'function totalSupply() view returns (uint256)',
    'function balanceOf(address account) view returns (uint256)',
    'function transfer(address to, uint256 amount) returns (bool)',
    'function approve(address spender, uint256 amount) returns (bool)',
    
    // Bonding Curve Trading
    'function buy(uint256 minTokensOut) payable returns (uint256)',
    'function sell(uint256 tokenAmount, uint256 minEthOut) returns (uint256)',
    'function getCurrentPrice() view returns (uint256)',
    'function getTokensForEth(uint256 ethAmount) view returns (uint256)',
    'function getEthForTokens(uint256 tokenAmount) view returns (uint256)',
    
    // Stats & Info
    'function creator() view returns (address)',
    'function profileUri() view returns (string)',
    'function createdAt() view returns (uint256)',
    'function totalEthLocked() view returns (uint256)',
    'function totalVolume() view returns (uint256)',
    'function totalTrades() view returns (uint256)',
    'function getStats() view returns (uint256 price, uint256 supply, uint256 ethLocked, uint256 volume, uint256 trades, uint256 marketCap)',
    
    // Owner
    'function setProfileUri(string newUri)',
    
    // Events
    'event Buy(address indexed buyer, uint256 ethIn, uint256 tokensOut, uint256 newPrice)',
    'event Sell(address indexed seller, uint256 tokensIn, uint256 ethOut, uint256 newPrice)',
  ],

  CreatorCoinFactory: [
    'function createCoin(string name, string symbol, string profileUri) returns (address)',
    'function totalCoins() view returns (uint256)',
    'function allCoins(uint256 index) view returns (address)',
    'function coinsByCreator(address creator, uint256 index) view returns (address)',
    'function coinBySymbol(string symbol) view returns (address)',
    'function getCoinsByCreator(address creator) view returns (address[])',
    'function getCoins(uint256 offset, uint256 limit) view returns (address[])',
    'function protocolTreasury() view returns (address)',
    
    // Events
    'event CoinCreated(address indexed coin, address indexed creator, string name, string symbol, string profileUri)',
  ],
};

export default ABIS;
