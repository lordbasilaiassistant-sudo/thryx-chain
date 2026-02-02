import { ethers } from "hardhat";
import * as fs from "fs";

/**
 * Deploy L1 Bridge Contract to Sepolia
 * 
 * BEFORE RUNNING:
 * 1. Get Sepolia ETH from faucets:
 *    - https://sepoliafaucet.com
 *    - https://www.alchemy.com/faucets/ethereum-sepolia
 *    - https://faucet.quicknode.com/ethereum/sepolia
 * 
 * 2. Set your private key in .env:
 *    SEPOLIA_PRIVATE_KEY=0x...
 * 
 * 3. Set Sepolia RPC (free from Alchemy/Infura):
 *    SEPOLIA_RPC_URL=https://eth-sepolia.g.alchemy.com/v2/YOUR_KEY
 * 
 * 4. Run: npx hardhat run scripts/deploy-sepolia.ts --network sepolia
 */

async function main() {
  console.log("🌉 Deploying Thryx L1 Bridge to Sepolia...\n");

  const [deployer] = await ethers.getSigners();
  const balance = await ethers.provider.getBalance(deployer.address);
  
  console.log("Deployer:", deployer.address);
  console.log("Balance:", ethers.formatEther(balance), "ETH");
  
  if (balance < ethers.parseEther("0.01")) {
    console.error("\n❌ Insufficient Sepolia ETH! Get testnet ETH from faucets:");
    console.error("   - https://sepoliafaucet.com");
    console.error("   - https://www.alchemy.com/faucets/ethereum-sepolia");
    process.exit(1);
  }

  // Deploy L1DepositContract
  console.log("\n📦 Deploying L1DepositContract...");
  const L1DepositContract = await ethers.getContractFactory("L1DepositContract");
  const depositContract = await L1DepositContract.deploy();
  await depositContract.waitForDeployment();
  const depositAddress = await depositContract.getAddress();
  console.log("L1DepositContract deployed to:", depositAddress);

  // Verify on Etherscan (optional but helpful)
  console.log("\n📝 To verify on Etherscan:");
  console.log(`npx hardhat verify --network sepolia ${depositAddress}`);

  // Save deployment info
  const sepoliaDeployment = {
    network: "sepolia",
    chainId: 11155111,
    timestamp: new Date().toISOString(),
    deployer: deployer.address,
    contracts: {
      L1DepositContract: depositAddress
    },
    blockExplorer: `https://sepolia.etherscan.io/address/${depositAddress}`
  };

  fs.writeFileSync(
    "./deployment-sepolia.json",
    JSON.stringify(sepoliaDeployment, null, 2)
  );

  console.log("\n✅ Sepolia deployment saved to deployment-sepolia.json");
  console.log("\n🔗 View on Etherscan:", sepoliaDeployment.blockExplorer);
  
  console.log("\n" + "=".repeat(60));
  console.log("🎉 L1 BRIDGE DEPLOYMENT COMPLETE");
  console.log("=".repeat(60));
  console.log("\nL1DepositContract:", depositAddress);
  console.log("\nNext steps:");
  console.log("1. Fund the bridge contract with test ETH");
  console.log("2. Set the sequencer address");
  console.log("3. Connect L2 to watch for deposits");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
