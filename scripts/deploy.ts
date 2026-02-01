import { ethers } from "hardhat";
import * as fs from "fs";

async function main() {
  console.log("🚀 Deploying Thryx contracts...\n");

  const [deployer, treasury, ...agentSigners] = await ethers.getSigners();
  
  console.log("Deployer:", deployer.address);
  console.log("Treasury:", treasury.address);
  console.log("Agent accounts:", agentSigners.slice(0, 5).map(s => s.address));

  // Deploy MockUSDC
  console.log("\n📦 Deploying MockUSDC...");
  const MockUSDC = await ethers.getContractFactory("MockUSDC");
  const usdc = await MockUSDC.deploy();
  await usdc.waitForDeployment();
  console.log("MockUSDC deployed to:", await usdc.getAddress());

  // Deploy MockWETH
  console.log("\n📦 Deploying MockWETH...");
  const MockWETH = await ethers.getContractFactory("MockWETH");
  const weth = await MockWETH.deploy();
  await weth.waitForDeployment();
  console.log("MockWETH deployed to:", await weth.getAddress());

  // Deploy AgentRegistry
  console.log("\n📦 Deploying AgentRegistry...");
  const AgentRegistry = await ethers.getContractFactory("AgentRegistry");
  const registry = await AgentRegistry.deploy();
  await registry.waitForDeployment();
  console.log("AgentRegistry deployed to:", await registry.getAddress());

  // Deploy StablecoinGas
  console.log("\n📦 Deploying StablecoinGas...");
  const StablecoinGas = await ethers.getContractFactory("StablecoinGas");
  const gasContract = await StablecoinGas.deploy(
    await usdc.getAddress(),
    await registry.getAddress(),
    treasury.address
  );
  await gasContract.waitForDeployment();
  console.log("StablecoinGas deployed to:", await gasContract.getAddress());

  // Deploy SimpleAMM
  console.log("\n📦 Deploying SimpleAMM...");
  const SimpleAMM = await ethers.getContractFactory("SimpleAMM");
  const amm = await SimpleAMM.deploy(
    await usdc.getAddress(),
    await weth.getAddress()
  );
  await amm.waitForDeployment();
  console.log("SimpleAMM deployed to:", await amm.getAddress());

  // Deploy AgentOracle
  console.log("\n📦 Deploying AgentOracle...");
  const AgentOracle = await ethers.getContractFactory("AgentOracle");
  const oracle = await AgentOracle.deploy(await registry.getAddress());
  await oracle.waitForDeployment();
  console.log("AgentOracle deployed to:", await oracle.getAddress());

  // Deploy IntentMempool
  console.log("\n📦 Deploying IntentMempool...");
  const IntentMempool = await ethers.getContractFactory("IntentMempool");
  const intentMempool = await IntentMempool.deploy(
    await registry.getAddress(),
    await usdc.getAddress()
  );
  await intentMempool.waitForDeployment();
  console.log("IntentMempool deployed to:", await intentMempool.getAddress());

  // Deploy L2WithdrawalContract for secure withdrawals
  console.log("\n📦 Deploying L2WithdrawalContract...");
  let l2WithdrawalAddress = "";
  try {
    const L2Withdrawal = await ethers.getContractFactory("L2WithdrawalContract");
    const l2Withdrawal = await L2Withdrawal.deploy(
      await usdc.getAddress(),  // L2 USDC
      "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"  // Base USDC (L1)
    );
    await l2Withdrawal.waitForDeployment();
    l2WithdrawalAddress = await l2Withdrawal.getAddress();
    console.log("L2WithdrawalContract deployed to:", l2WithdrawalAddress);
  } catch (e) {
    console.log("L2WithdrawalContract deployment skipped (contract may not exist)");
  }

  // Deploy CreatorCoinFactory (Social Tokens like Zora)
  console.log("\n📦 Deploying CreatorCoinFactory (Zora-like social tokens)...");
  let creatorCoinFactoryAddress = "";
  try {
    const CreatorCoinFactory = await ethers.getContractFactory("CreatorCoinFactory");
    const creatorCoinFactory = await CreatorCoinFactory.deploy(treasury.address);
    await creatorCoinFactory.waitForDeployment();
    creatorCoinFactoryAddress = await creatorCoinFactory.getAddress();
    console.log("CreatorCoinFactory deployed to:", creatorCoinFactoryAddress);
  } catch (e) {
    console.log("CreatorCoinFactory deployment skipped:", e);
  }

  // Deploy BridgeBonus (Rewards for bridging from Base)
  console.log("\n📦 Deploying BridgeBonus (Bridge rewards token)...");
  let bridgeBonusAddress = "";
  try {
    const BridgeBonus = await ethers.getContractFactory("BridgeBonus");
    const bridgeBonus = await BridgeBonus.deploy();
    await bridgeBonus.waitForDeployment();
    bridgeBonusAddress = await bridgeBonus.getAddress();
    console.log("BridgeBonus deployed to:", bridgeBonusAddress);
    
    // Set bridge agent (account 8 will be bridge)
    if (agentSigners.length > 7) {
      await bridgeBonus.setBridgeAgent(agentSigners[7].address);
      console.log("  Bridge agent set to:", agentSigners[7].address);
    }
  } catch (e) {
    console.log("BridgeBonus deployment skipped:", e);
  }

  // Fund agents with USDC and WETH
  console.log("\n💰 Funding agent accounts...");
  const agentNames = ["Oracle", "Arbitrage", "Liquidity", "Governance", "Monitor", "Security", "Intent"];
  const usdcAmount = ethers.parseUnits("100000", 6); // 100k USDC each
  const wethAmount = ethers.parseEther("100"); // 100 WETH each

  for (let i = 0; i < Math.min(7, agentSigners.length); i++) {
    const agent = agentSigners[i];
    await usdc.mint(agent.address, usdcAmount);
    await weth.mint(agent.address, wethAmount);
    console.log(`  ${agentNames[i]} Agent (${agent.address}): 100k USDC, 100 WETH`);
  }

  // Register agents
  console.log("\n📝 Registering agents on-chain...");
  const permissions = [
    ethers.keccak256(ethers.toUtf8Bytes("ORACLE")),
    ethers.keccak256(ethers.toUtf8Bytes("TRADE")),
    ethers.keccak256(ethers.toUtf8Bytes("LIQUIDITY")),
    ethers.keccak256(ethers.toUtf8Bytes("GOVERNANCE")),
    ethers.keccak256(ethers.toUtf8Bytes("MONITOR")),
    ethers.keccak256(ethers.toUtf8Bytes("SECURITY")),
    ethers.keccak256(ethers.toUtf8Bytes("INTENT"))
  ];

  for (let i = 0; i < Math.min(7, agentSigners.length); i++) {
    const agent = agentSigners[i];
    const dailyBudget = ethers.parseUnits("1000", 6); // 1000 USDC daily budget
    
    await registry.registerAgent(
      agent.address,
      dailyBudget,
      permissions[i],
      `${agentNames[i]} Agent`
    );
    console.log(`  Registered ${agentNames[i]} Agent`);
  }

  // Add initial liquidity to AMM
  console.log("\n💧 Adding initial liquidity to AMM...");
  const liquidityAgent = agentSigners[2]; // Liquidity agent
  const liquidityUsdc = ethers.parseUnits("50000", 6);
  const liquidityWeth = ethers.parseEther("20");

  await usdc.connect(liquidityAgent).approve(await amm.getAddress(), liquidityUsdc);
  await weth.connect(liquidityAgent).approve(await amm.getAddress(), liquidityWeth);
  await amm.connect(liquidityAgent).addLiquidity(liquidityUsdc, liquidityWeth);
  console.log("  Added 50k USDC + 20 WETH liquidity");

  // Deploy Faucet (for free starter ETH)
  console.log("\n📦 Deploying Faucet (free starter ETH for users)...");
  let faucetAddress = "";
  try {
    const Faucet = await ethers.getContractFactory("Faucet");
    const faucet = await Faucet.deploy();
    await faucet.waitForDeployment();
    faucetAddress = await faucet.getAddress();
    console.log("Faucet deployed to:", faucetAddress);
    
    // Fund the faucet with 100 ETH from deployer
    const fundingAmount = ethers.parseEther("100");
    await deployer.sendTransaction({
      to: faucetAddress,
      value: fundingAmount
    });
    console.log("  Funded faucet with 100 ETH");
  } catch (e) {
    console.log("Faucet deployment skipped:", e);
  }

  // Save deployment addresses
  const deployment = {
    network: "localhost",
    timestamp: new Date().toISOString(),
    contracts: {
      MockUSDC: await usdc.getAddress(),
      MockWETH: await weth.getAddress(),
      AgentRegistry: await registry.getAddress(),
      StablecoinGas: await gasContract.getAddress(),
      SimpleAMM: await amm.getAddress(),
      AgentOracle: await oracle.getAddress(),
      IntentMempool: await intentMempool.getAddress(),
      L2WithdrawalContract: l2WithdrawalAddress || "not_deployed",
      CreatorCoinFactory: creatorCoinFactoryAddress || "not_deployed",
      BridgeBonus: bridgeBonusAddress || "not_deployed",
      Faucet: faucetAddress || "not_deployed"
    },
    agents: {
      oracle: agentSigners[0].address,
      arbitrage: agentSigners[1].address,
      liquidity: agentSigners[2].address,
      governance: agentSigners[3].address,
      monitor: agentSigners[4].address,
      security: agentSigners.length > 5 ? agentSigners[5].address : "not_assigned",
      intent: agentSigners.length > 6 ? agentSigners[6].address : "not_assigned"
    },
    treasury: treasury.address
  };

  fs.writeFileSync(
    "./deployment.json",
    JSON.stringify(deployment, null, 2)
  );
  console.log("\n✅ Deployment info saved to deployment.json");

  // Summary
  console.log("\n" + "=".repeat(60));
  console.log("🎉 THRYX DEPLOYMENT COMPLETE");
  console.log("=".repeat(60));
  console.log("\nContracts:");
  Object.entries(deployment.contracts).forEach(([name, addr]) => {
    console.log(`  ${name}: ${addr}`);
  });
  console.log("\nAgents:");
  Object.entries(deployment.agents).forEach(([name, addr]) => {
    console.log(`  ${name}: ${addr}`);
  });
  console.log("\n🔥 Ready for autonomous agent activity!");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
