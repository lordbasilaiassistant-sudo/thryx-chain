import { ethers } from "hardhat";
import * as fs from "fs";

async function main() {
  const [deployer] = await ethers.getSigners();
  console.log("Deploying L2WithdrawalContract with:", deployer.address);

  const L2Withdrawal = await ethers.getContractFactory("L2WithdrawalContract");
  const l2Withdrawal = await L2Withdrawal.deploy(deployer.address);
  await l2Withdrawal.waitForDeployment();
  
  const address = await l2Withdrawal.getAddress();
  console.log("L2WithdrawalContract deployed to:", address);

  // Update deployment.json
  const deployment = JSON.parse(fs.readFileSync("deployment.json", "utf8"));
  deployment.contracts.L2WithdrawalContract = address;
  fs.writeFileSync("deployment.json", JSON.stringify(deployment, null, 2));
  console.log("Updated deployment.json");
}

main().catch(console.error);
