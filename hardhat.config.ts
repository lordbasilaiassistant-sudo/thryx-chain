import { HardhatUserConfig } from "hardhat/config";
import "@nomicfoundation/hardhat-toolbox";
import * as dotenv from "dotenv";

// Load environment variables from .env file
dotenv.config();

// ==================== Environment Variables ====================
// SECURITY: Never hardcode private keys! Use environment variables.

const DEPLOYER_PRIVATE_KEY = process.env.DEPLOYER_PRIVATE_KEY;
const ALCHEMY_API_KEY = process.env.ALCHEMY_API_KEY || "";
const BASESCAN_API_KEY = process.env.BASESCAN_API_KEY || "";
const RPC_URL = process.env.RPC_URL || "http://127.0.0.1:8545";

// Validate production keys
if (process.env.NODE_ENV === "production" && !DEPLOYER_PRIVATE_KEY) {
  console.error("ERROR: DEPLOYER_PRIVATE_KEY is required in production!");
  process.exit(1);
}

// For local development, use Hardhat's default accounts
const accounts = DEPLOYER_PRIVATE_KEY ? [DEPLOYER_PRIVATE_KEY] : undefined;

const config: HardhatUserConfig = {
  solidity: {
    version: "0.8.24",
    settings: {
      optimizer: {
        enabled: true,
        runs: 200
      },
      viaIR: true, // Enable IR for better optimization
    }
  },
  networks: {
    // THRYX Mainnet - Chain ID 77777
    hardhat: {
      chainId: 77777,
      mining: {
        auto: true,
        interval: 2000 // 2 second blocks
      },
      accounts: {
        count: 20,
        accountsBalance: "10000000000000000000000" // 10000 ETH each
      }
    },
    // Local development
    localhost: {
      url: RPC_URL,
      chainId: 77777,
    },
    // Base Mainnet (L1 for THRYX)
    base: {
      url: process.env.BASE_RPC_URL || "https://mainnet.base.org",
      accounts: accounts,
      chainId: 8453,
    },
    // Base Sepolia (testnet)
    baseSepolia: {
      url: `https://base-sepolia.g.alchemy.com/v2/${ALCHEMY_API_KEY}`,
      accounts: accounts,
      chainId: 84532,
    },
    // Ethereum Sepolia (testnet)
    sepolia: {
      url: ALCHEMY_API_KEY 
        ? `https://eth-sepolia.g.alchemy.com/v2/${ALCHEMY_API_KEY}` 
        : "https://rpc.sepolia.org",
      accounts: accounts,
      chainId: 11155111
    }
  },
  paths: {
    sources: "./contracts",
    tests: "./test",
    cache: "./cache",
    artifacts: "./artifacts"
  },
  etherscan: {
    apiKey: {
      base: BASESCAN_API_KEY,
      baseSepolia: BASESCAN_API_KEY,
      sepolia: process.env.ETHERSCAN_API_KEY || "",
    }
  },
  gasReporter: {
    enabled: process.env.REPORT_GAS === "true",
    currency: "USD",
  },
};

export default config;
