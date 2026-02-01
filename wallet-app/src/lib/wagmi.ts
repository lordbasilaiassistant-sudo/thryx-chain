import { getDefaultConfig } from '@rainbow-me/rainbowkit';
import { http, createConfig } from 'wagmi';
import { base } from 'wagmi/chains';
import { defineChain } from 'viem';

// Define THRYX chain
export const thryx = defineChain({
  id: 31337,
  name: 'THRYX',
  nativeCurrency: {
    decimals: 18,
    name: 'THRYX ETH',
    symbol: 'ETH',
  },
  rpcUrls: {
    default: {
      http: [process.env.NEXT_PUBLIC_THRYX_RPC || 'http://localhost:8545'],
    },
    public: {
      http: [process.env.NEXT_PUBLIC_THRYX_RPC || 'http://localhost:8545'],
    },
  },
  blockExplorers: {
    default: { 
      name: 'THRYX Explorer', 
      url: process.env.NEXT_PUBLIC_THRYX_EXPLORER || 'http://localhost:5100' 
    },
  },
});

export const config = getDefaultConfig({
  appName: 'THRYX Wallet',
  projectId: 'c691d01c72b0b3e656af1fabd9ed0304',
  chains: [thryx, base],
  transports: {
    [thryx.id]: http(process.env.NEXT_PUBLIC_THRYX_RPC || 'http://localhost:8545'),
    [base.id]: http('https://mainnet.base.org'),
  },
  ssr: true,
});

// Contract addresses (loaded from deployment)
export const CONTRACTS = {
  USDC: process.env.NEXT_PUBLIC_USDC_ADDRESS || '0x5FbDB2315678afecb367f032d93F642f64180aa3',
  WETH: process.env.NEXT_PUBLIC_WETH_ADDRESS || '0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512',
  AMM: process.env.NEXT_PUBLIC_AMM_ADDRESS || '0xDc64a140Aa3E981100a9becA4E685f962f0cF6C9',
};

// Bridge wallet address on Base
export const BRIDGE_WALLET = process.env.NEXT_PUBLIC_BRIDGE_WALLET || '0x03F2B0AE7f6badE9944d2CFB8Ad66b62CF6ba1d4';
