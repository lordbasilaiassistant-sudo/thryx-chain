/**
 * Deploy Upgradeable Contracts
 * 
 * This script deploys contracts using the UUPS proxy pattern.
 * 
 * Usage:
 *   npx hardhat run scripts/deploy-upgradeable.ts --network localhost
 */

import { ethers, upgrades } from "hardhat";
import * as fs from "fs";

async function main() {
  console.log("\n=== THRYX Upgradeable Contract Deployment ===\n");

  const [deployer] = await ethers.getSigners();
  console.log("Deployer:", deployer.address);
  console.log("Balance:", ethers.formatEther(await ethers.provider.getBalance(deployer.address)), "ETH\n");

  // Deploy ThryxTokenV2 as upgradeable
  console.log("Deploying ThryxTokenV2 (Upgradeable)...");
  
  const ThryxTokenV2 = await ethers.getContractFactory("ThryxTokenV2");
  
  // This deploys both the implementation and the proxy
  const thryxToken = await upgrades.deployProxy(ThryxTokenV2, [], {
    initializer: "initialize",
    kind: "uups",
  });
  
  await thryxToken.waitForDeployment();
  
  const proxyAddress = await thryxToken.getAddress();
  const implementationAddress = await upgrades.erc1967.getImplementationAddress(proxyAddress);
  
  console.log("  Proxy Address:", proxyAddress);
  console.log("  Implementation Address:", implementationAddress);
  
  // Verify it works
  const name = await thryxToken.name();
  const symbol = await thryxToken.symbol();
  const version = await thryxToken.version();
  
  console.log(`  Token: ${name} (${symbol})`);
  console.log(`  Version: ${version}`);
  
  // Save deployment info
  const deployment = {
    network: "thryx",
    chainId: 77777,
    timestamp: new Date().toISOString(),
    deployer: deployer.address,
    upgradeable: {
      ThryxTokenV2: {
        proxy: proxyAddress,
        implementation: implementationAddress,
        version: Number(version),
      },
    },
  };
  
  fs.writeFileSync(
    "deployment-upgradeable.json",
    JSON.stringify(deployment, null, 2)
  );
  
  console.log("\n✅ Deployment saved to deployment-upgradeable.json");
  
  // Example: How to upgrade later
  console.log("\n--- Upgrade Instructions ---");
  console.log(`
To upgrade to a new version:

1. Create ThryxTokenV3.sol with new features
2. Run:
   
   const ThryxTokenV3 = await ethers.getContractFactory("ThryxTokenV3");
   await upgrades.upgradeProxy("${proxyAddress}", ThryxTokenV3);
   
3. The proxy address stays the same, only implementation changes
`);
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
