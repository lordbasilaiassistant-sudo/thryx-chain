/**
 * Check THRYX balance for an address
 */
import { ThryxSDK, formatEther } from '../sdk/src/index';

async function main() {
  const address = process.argv[2] || '0x03F2B0AE7f6badE9944d2CFB8Ad66b62CF6ba1d4';
  
  const sdk = new ThryxSDK({
    rpcUrl: 'https://crispy-goggles-v6jg77gvqwqv3pxpg-8545.app.github.dev'
  });

  console.log(`Checking THRYX balance for: ${address}`);
  
  const balance = await sdk.getBalance(address as `0x${string}`);
  console.log(`THRYX Balance: ${formatEther(balance)} ETH`);
}

main().catch(console.error);
