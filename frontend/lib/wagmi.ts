import { getDefaultConfig } from '@rainbow-me/rainbowkit';
import { http } from 'wagmi';
import { mainnet, sepolia } from 'wagmi/chains';

// Define Thryx local chain
const thryxLocal = {
  id: 31337,
  name: 'Thryx Local',
  nativeCurrency: {
    decimals: 18,
    name: 'Ether',
    symbol: 'ETH',
  },
  rpcUrls: {
    default: { http: ['http://127.0.0.1:8545'] },
    public: { http: ['http://127.0.0.1:8545'] },
  },
  blockExplorers: {
    default: { name: 'Local', url: 'http://localhost:8545' },
  },
  testnet: true,
} as const;

export const config = getDefaultConfig({
  appName: 'Thryx',
  projectId: 'thryx-ai-blockchain', // WalletConnect project ID (get free at cloud.walletconnect.com)
  chains: [thryxLocal, sepolia, mainnet],
  transports: {
    [thryxLocal.id]: http('http://127.0.0.1:8545'),
    [sepolia.id]: http(),
    [mainnet.id]: http(),
  },
  ssr: true,
});

// Contract addresses (loaded from deployment.json or env)
export const CONTRACTS = {
  MockUSDC: process.env.NEXT_PUBLIC_USDC_ADDRESS || '0x5FbDB2315678afecb367f032d93F642f64180aa3',
  MockWETH: process.env.NEXT_PUBLIC_WETH_ADDRESS || '0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512',
  AgentRegistry: process.env.NEXT_PUBLIC_REGISTRY_ADDRESS || '0x9fE46736679d2D9a65F0992F2272dE9f3c7fa6e0',
  SimpleAMM: process.env.NEXT_PUBLIC_AMM_ADDRESS || '0xDc64a140Aa3E981100a9becA4E685f962f0cF6C9',
  AgentOracle: process.env.NEXT_PUBLIC_ORACLE_ADDRESS || '0x5FC8d32690cc91D4c39d9d3abcBD16989F875707',
};

// Agent addresses
export const AGENTS = {
  oracle: '0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC',
  arbitrage: '0x90F79bf6EB2c4f870365E785982E1f101E93b906',
  liquidity: '0x15d34AAf54267DB7D7c367839AAf71A00a2C6A65',
  governance: '0x9965507D1a55bcC2695C58ba16FB37d819B0A4dc',
  monitor: '0x976EA74026E726554dB657fA54763abd0C3a0aa9',
};
