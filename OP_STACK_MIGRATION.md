# THRYX → OP Stack Migration Guide

This guide outlines the steps to migrate THRYX from Hardhat to a production-ready OP Stack L2.

## Why OP Stack?

| Feature | Current (Hardhat) | OP Stack |
|---------|-------------------|----------|
| Consensus | Single node | Sequencer + Validators |
| Finality | None | L1 anchoring on Base |
| Data Availability | Local | L1 calldata or EigenDA |
| Fraud Proofs | None | 7-day challenge period |
| Production Ready | No | Yes |
| Battle Tested | No | Yes (Base, Zora, Mode) |

## Migration Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        THRYX L2                              │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────────────┐ │
│  │Sequencer│→ │ Batcher │→ │Proposer │→ │ Contracts       │ │
│  │ (op-node)  │ (op-batcher) │ (op-proposer) │ (Your contracts) │ │
│  └─────────┘  └─────────┘  └─────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                     Base Mainnet (L1)                        │
│  ┌──────────────────┐  ┌────────────────────────────────┐   │
│  │ OptimismPortal   │  │ L2OutputOracle                 │   │
│  │ (Deposits/Exits) │  │ (State root submissions)       │   │
│  └──────────────────┘  └────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Phase 1: Infrastructure Setup (Week 1)

### 1.1 Clone OP Stack Monorepo

```bash
git clone https://github.com/ethereum-optimism/optimism.git
cd optimism
git checkout v1.7.0  # Use stable release
make build
```

### 1.2 Generate Keys

```bash
# Generate new keys for each role
cast wallet new  # Sequencer
cast wallet new  # Batcher  
cast wallet new  # Proposer
cast wallet new  # Admin
```

### 1.3 Configure Network

Create `thryx-config.json`:

```json
{
  "l1ChainID": 8453,
  "l2ChainID": 77777,
  "l2BlockTime": 2,
  "sequencerAddress": "0x...",
  "batcherAddress": "0x...",
  "proposerAddress": "0x...",
  "adminAddress": "0x...",
  "baseFeeVaultRecipient": "0x...",
  "l1FeeVaultRecipient": "0x...",
  "sequencerFeeVaultRecipient": "0x...",
  "governanceTokenName": "THRYX",
  "governanceTokenSymbol": "THRYX",
  "enableGovernance": true,
  "fundDevAccounts": false,
  "faultGameAbsolutePrestate": "0x...",
  "faultGameMaxDepth": 73,
  "faultGameSplitDepth": 30,
  "faultGameClockExtension": 0,
  "faultGameMaxClockDuration": 302400
}
```

## Phase 2: Deploy L1 Contracts (Week 2)

### 2.1 Deploy System Contracts to Base

```bash
cd packages/contracts-bedrock

# Configure for Base mainnet
export L1_RPC_URL="https://mainnet.base.org"
export DEPLOYER_PRIVATE_KEY="0x..."

# Deploy
forge script scripts/Deploy.s.sol:Deploy \
  --rpc-url $L1_RPC_URL \
  --private-key $DEPLOYER_PRIVATE_KEY \
  --broadcast \
  --verify
```

### 2.2 Key L1 Contracts

| Contract | Purpose |
|----------|---------|
| `OptimismPortal` | Bridge deposits/withdrawals |
| `L2OutputOracle` | Accept state root submissions |
| `SystemConfig` | L2 configuration |
| `AddressManager` | Contract registry |

## Phase 3: Launch L2 (Week 3)

### 3.1 Generate Genesis

```bash
cd op-node/cmd/genesis

go run . \
  --l1-deployments ../../../packages/contracts-bedrock/deployments/base-mainnet/.deploy \
  --deploy-config ./thryx-config.json \
  --l1-rpc https://mainnet.base.org \
  --outfile thryx-genesis.json
```

### 3.2 Start Services

```yaml
# docker-compose.op-stack.yml
version: '3.8'

services:
  op-geth:
    image: us-docker.pkg.dev/oplabs-tools-artifacts/images/op-geth:v1.101315.0
    ports:
      - "8545:8545"
      - "8546:8546"
    volumes:
      - geth-data:/data
    command:
      - --datadir=/data
      - --http
      - --http.addr=0.0.0.0
      - --http.port=8545
      - --http.corsdomain=*
      - --http.api=web3,debug,eth,txpool,net,engine
      - --ws
      - --ws.addr=0.0.0.0
      - --ws.port=8546
      - --ws.origins=*
      - --syncmode=full
      - --gcmode=archive
      - --networkid=77777
      - --rollup.disabletxpoolgossip=true

  op-node:
    image: us-docker.pkg.dev/oplabs-tools-artifacts/images/op-node:v1.7.0
    depends_on:
      - op-geth
    environment:
      - OP_NODE_L1_ETH_RPC=https://mainnet.base.org
      - OP_NODE_L2_ENGINE_RPC=http://op-geth:8551
      - OP_NODE_L2_ETH_RPC=http://op-geth:8545
      - OP_NODE_ROLLUP_CONFIG=/config/rollup.json
      - OP_NODE_P2P_DISABLE=true
      - OP_NODE_SEQUENCER_ENABLED=true
      - OP_NODE_SEQUENCER_L1_CONFS=4
    volumes:
      - ./config:/config

  op-batcher:
    image: us-docker.pkg.dev/oplabs-tools-artifacts/images/op-batcher:v1.7.0
    depends_on:
      - op-node
    environment:
      - OP_BATCHER_L1_ETH_RPC=https://mainnet.base.org
      - OP_BATCHER_L2_ETH_RPC=http://op-geth:8545
      - OP_BATCHER_ROLLUP_RPC=http://op-node:8547
      - OP_BATCHER_PRIVATE_KEY=${BATCHER_PRIVATE_KEY}
      - OP_BATCHER_MAX_CHANNEL_DURATION=1

  op-proposer:
    image: us-docker.pkg.dev/oplabs-tools-artifacts/images/op-proposer:v1.7.0
    depends_on:
      - op-node
    environment:
      - OP_PROPOSER_L1_ETH_RPC=https://mainnet.base.org
      - OP_PROPOSER_ROLLUP_RPC=http://op-node:8547
      - OP_PROPOSER_L2OO_ADDRESS=0x...
      - OP_PROPOSER_PRIVATE_KEY=${PROPOSER_PRIVATE_KEY}

volumes:
  geth-data:
```

## Phase 4: Migrate Contracts (Week 4)

### 4.1 Deploy THRYX Contracts to New L2

Your existing contracts will work unchanged:

```bash
# Point to new L2 RPC
export RPC_URL="http://localhost:8545"  # New OP Stack L2

# Deploy
npx hardhat run scripts/deploy.ts --network localhost
```

### 4.2 Update Bridge Contracts

Replace custom bridge with OP Stack's native bridge:

```solidity
// Use OptimismPortal for deposits
interface IOptimismPortal {
    function depositTransaction(
        address _to,
        uint256 _value,
        uint64 _gasLimit,
        bool _isCreation,
        bytes memory _data
    ) external payable;
}

// Use L2StandardBridge for tokens
interface IL2StandardBridge {
    function withdraw(
        address _l2Token,
        uint256 _amount,
        uint32 _minGasLimit,
        bytes calldata _extraData
    ) external payable;
}
```

## Phase 5: Agent Migration

### 5.1 Update Agent RPC URLs

```python
# agents/config.py
RPC_URL = os.getenv("RPC_URL", "http://op-geth:8545")

# All agents work unchanged - just different RPC
```

### 5.2 Add L1 Monitoring

```python
# agents/l1_monitor_agent.py
class L1MonitorAgent:
    """Monitor L1 for deposits and state submissions"""
    
    def __init__(self):
        self.l1_rpc = os.getenv("BASE_RPC_URL")
        self.optimism_portal = "0x..."  # Deployed OptimismPortal
        
    async def watch_deposits(self):
        # Monitor TransactionDeposited events
        pass
        
    async def verify_state_roots(self):
        # Verify L2OutputOracle submissions
        pass
```

## Cost Estimates

| Component | Monthly Cost |
|-----------|-------------|
| L1 Gas (Batcher) | ~$500-2000 |
| L1 Gas (Proposer) | ~$100-500 |
| Infrastructure | ~$200-500 |
| **Total** | **~$800-3000** |

## Timeline

| Week | Milestone |
|------|-----------|
| 1 | Infrastructure setup, key generation |
| 2 | Deploy L1 contracts to Base |
| 3 | Launch L2, test sequencer |
| 4 | Migrate contracts and agents |
| 5 | Testing, security review |
| 6 | Mainnet launch |

## Alternative: Arbitrum Orbit

If you prefer Arbitrum's stack:

```bash
# Clone Arbitrum Nitro
git clone https://github.com/OffchainLabs/nitro.git

# Similar process but different tooling
# Benefits: Lower L1 costs with AnyTrust
# Tradeoffs: Less mature than OP Stack
```

## Quick Start Script

```bash
#!/bin/bash
# migrate-to-op-stack.sh

set -e

echo "=== THRYX OP Stack Migration ==="

# 1. Check prerequisites
command -v docker >/dev/null 2>&1 || { echo "Docker required"; exit 1; }
command -v forge >/dev/null 2>&1 || { echo "Foundry required"; exit 1; }

# 2. Generate keys if not exist
if [ ! -f .keys ]; then
    echo "Generating operator keys..."
    echo "SEQUENCER_KEY=$(cast wallet new --json | jq -r '.private_key')" > .keys
    echo "BATCHER_KEY=$(cast wallet new --json | jq -r '.private_key')" >> .keys
    echo "PROPOSER_KEY=$(cast wallet new --json | jq -r '.private_key')" >> .keys
fi

source .keys

# 3. Clone OP Stack
if [ ! -d "optimism" ]; then
    git clone https://github.com/ethereum-optimism/optimism.git
    cd optimism && git checkout v1.7.0 && cd ..
fi

echo "=== Next Steps ==="
echo "1. Fund operator addresses on Base"
echo "2. Configure thryx-config.json"
echo "3. Deploy L1 contracts"
echo "4. Start L2 services"
```

## Resources

- [OP Stack Docs](https://stack.optimism.io/)
- [Base Documentation](https://docs.base.org/)
- [Optimism Monorepo](https://github.com/ethereum-optimism/optimism)
- [OP Stack Deployment Tutorial](https://blog.oplabs.co/op-stack-deployment/)
