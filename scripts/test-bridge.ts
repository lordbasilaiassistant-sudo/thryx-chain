/**
 * Test script for THRYX Bridge
 * Tests bridging ETH from Base to THRYX using the SDK
 * 
 * Usage:
 *   npx ts-node scripts/test-bridge.ts [amount]
 * 
 * Environment:
 *   BASE_PRIVATE_KEY - Private key for Base wallet
 */

import { BridgeClient, BRIDGE_WALLET, formatEther } from '../sdk/src/index';

async function main() {
  const privateKey = process.env.BASE_PRIVATE_KEY;
  
  if (!privateKey) {
    console.error('ERROR: BASE_PRIVATE_KEY environment variable not set');
    console.log('\nSet it with:');
    console.log('  $env:BASE_PRIVATE_KEY = "0x..."  (PowerShell)');
    console.log('  export BASE_PRIVATE_KEY=0x...    (Bash)');
    process.exit(1);
  }

  const amount = process.argv[2] || '0.0001'; // Default to small test amount

  console.log('\n===========================================');
  console.log('THRYX Bridge Test (Base -> THRYX)');
  console.log('===========================================\n');
  
  // Create bridge client
  const bridge = new BridgeClient('https://mainnet.base.org', privateKey);
  
  console.log(`Your Address: ${bridge.address}`);
  console.log(`Bridge Wallet: ${BRIDGE_WALLET}`);
  console.log(`Amount to Bridge: ${amount} ETH\n`);

  // Check balances
  const baseBalance = await bridge.getBaseBalance();
  console.log(`Base ETH Balance: ${formatEther(baseBalance)} ETH`);
  
  try {
    const usdcBalance = await bridge.getBaseUsdcBalance();
    console.log(`Base USDC Balance: ${Number(usdcBalance) / 1e6} USDC`);
  } catch (e) {
    console.log('Base USDC Balance: (could not fetch)');
  }

  console.log('\n-------------------------------------------');
  console.log('Initiating bridge transaction...\n');

  // Bridge ETH
  const result = await bridge.bridgeETH(amount);

  if (result.success) {
    console.log('✅ Bridge transaction sent!');
    console.log(`   TX Hash: ${result.txHash}`);
    console.log(`   Amount: ${result.amount} ETH`);
    console.log(`\n   View on Basescan: https://basescan.org/tx/${result.txHash}`);
    console.log('\n   Your ETH will arrive on THRYX in ~30 seconds.');
    console.log('   The bridge agent monitors Base and automatically');
    console.log('   sends ETH to your address on THRYX (1:1).');
  } else {
    console.log('❌ Bridge failed:', result.error);
  }

  console.log('\n===========================================\n');
}

main().catch(console.error);
