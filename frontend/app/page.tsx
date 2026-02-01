'use client';

import { ConnectButton } from '@rainbow-me/rainbowkit';
import { useAccount, useReadContract, useBlockNumber } from 'wagmi';
import { formatEther, formatUnits, keccak256, toBytes } from 'viem';
import { useState, useEffect } from 'react';
import { CONTRACTS, AGENTS } from '@/lib/wagmi';
import { AGENT_REGISTRY_ABI, SIMPLE_AMM_ABI, AGENT_ORACLE_ABI, ERC20_ABI } from '@/lib/contracts';

// Agent activity simulation (in production, would come from indexer/events)
const MOCK_ACTIVITIES = [
  { agent: 'Oracle', action: 'Submitted ETH/USD price', value: '$2,497.38', time: '2s ago' },
  { agent: 'Arbitrage', action: 'Monitoring spread', value: '0.2%', time: '5s ago' },
  { agent: 'Liquidity', action: 'Position healthy', value: '$100k TVL', time: '12s ago' },
  { agent: 'Governance', action: 'Voted FOR', value: 'Proposal #2', time: '30s ago' },
  { agent: 'Monitor', action: 'All systems operational', value: '5/5 agents', time: '5s ago' },
];

export default function Home() {
  const { address, isConnected } = useAccount();
  const [activities, setActivities] = useState(MOCK_ACTIVITIES);
  
  // Get block number
  const { data: blockNumber } = useBlockNumber({ watch: true });
  
  // Get agent count
  const { data: agentCount } = useReadContract({
    address: CONTRACTS.AgentRegistry as `0x${string}`,
    abi: AGENT_REGISTRY_ABI,
    functionName: 'getAgentCount',
  });
  
  // Get AMM reserves
  const { data: reserveA } = useReadContract({
    address: CONTRACTS.SimpleAMM as `0x${string}`,
    abi: SIMPLE_AMM_ABI,
    functionName: 'reserveA',
  });
  
  const { data: reserveB } = useReadContract({
    address: CONTRACTS.SimpleAMM as `0x${string}`,
    abi: SIMPLE_AMM_ABI,
    functionName: 'reserveB',
  });
  
  // Get oracle price
  const { data: oraclePrice } = useReadContract({
    address: CONTRACTS.AgentOracle as `0x${string}`,
    abi: AGENT_ORACLE_ABI,
    functionName: 'getPrice',
    args: [keccak256(toBytes('ETH/USD'))],
  });
  
  // Calculate TVL and earnings
  const tvl = reserveA ? Number(formatUnits(reserveA as bigint, 6)) * 2 : 0;
  const ethPrice = oraclePrice ? Number((oraclePrice as [bigint, bigint, boolean])[0]) / 1e8 : 0;
  
  // Simulate earnings (in production, would calculate from fee events)
  const estimatedEarnings = tvl * 0.0001; // 0.01% daily simulated
  
  // Rotate activities periodically
  useEffect(() => {
    const interval = setInterval(() => {
      setActivities(prev => {
        const newActivity = {
          agent: ['Oracle', 'Arbitrage', 'Monitor'][Math.floor(Math.random() * 3)],
          action: ['Price update', 'Checking spread', 'Health check'][Math.floor(Math.random() * 3)],
          value: `$${(Math.random() * 100).toFixed(2)}`,
          time: 'just now',
        };
        return [newActivity, ...prev.slice(0, 4)];
      });
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <main className="min-h-screen">
      {/* Header */}
      <header className="border-b border-thryx-border">
        <div className="max-w-7xl mx-auto px-4 py-4 flex justify-between items-center">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-thryx-primary to-thryx-secondary flex items-center justify-center">
              <span className="text-xl font-bold">T</span>
            </div>
            <span className="text-xl font-semibold">Thryx</span>
            <span className="text-xs px-2 py-1 bg-thryx-card rounded-full text-gray-400">
              AI-Native Chain
            </span>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 text-sm text-gray-400">
              <div className="w-2 h-2 rounded-full bg-green-500 pulse-dot"></div>
              Block #{blockNumber?.toString() || '...'}
            </div>
            <ConnectButton />
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="max-w-7xl mx-auto px-4 py-16 text-center">
        <h1 className="text-5xl font-bold mb-4 bg-gradient-to-r from-thryx-primary to-thryx-secondary bg-clip-text text-transparent">
          Earn While AI Agents Work
        </h1>
        <p className="text-xl text-gray-400 mb-8 max-w-2xl mx-auto">
          The first blockchain where autonomous AI agents generate revenue and share it with humans. 
          Connect your wallet to start earning.
        </p>
        
        {!isConnected && (
          <div className="flex justify-center">
            <ConnectButton />
          </div>
        )}
      </section>

      {/* Stats Grid */}
      <section className="max-w-7xl mx-auto px-4 py-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          {/* TVL */}
          <div className="bg-thryx-card rounded-xl p-6 border border-thryx-border card-hover">
            <div className="text-sm text-gray-400 mb-2">Total Value Locked</div>
            <div className="text-3xl font-bold text-white">
              ${tvl.toLocaleString()}
            </div>
            <div className="text-sm text-green-400 mt-2">In AMM liquidity</div>
          </div>
          
          {/* Active Agents */}
          <div className="bg-thryx-card rounded-xl p-6 border border-thryx-border card-hover">
            <div className="text-sm text-gray-400 mb-2">Active Agents</div>
            <div className="text-3xl font-bold text-white">
              {agentCount?.toString() || '5'} / 5
            </div>
            <div className="text-sm text-green-400 mt-2 flex items-center gap-1">
              <div className="w-2 h-2 rounded-full bg-green-500"></div>
              All operational
            </div>
          </div>
          
          {/* ETH Price */}
          <div className="bg-thryx-card rounded-xl p-6 border border-thryx-border card-hover">
            <div className="text-sm text-gray-400 mb-2">ETH/USD (Oracle)</div>
            <div className="text-3xl font-bold text-white">
              ${ethPrice.toLocaleString(undefined, { maximumFractionDigits: 2 })}
            </div>
            <div className="text-sm text-gray-400 mt-2">Consensus from agents</div>
          </div>
          
          {/* Your Earnings */}
          <div className="bg-thryx-card rounded-xl p-6 border border-thryx-border card-hover glow-purple">
            <div className="text-sm text-gray-400 mb-2">Estimated Daily Earnings</div>
            <div className="text-3xl font-bold text-thryx-primary">
              ${estimatedEarnings.toFixed(2)}
            </div>
            <div className="text-sm text-gray-400 mt-2">
              {isConnected ? '50% of agent fees' : 'Connect wallet to earn'}
            </div>
          </div>
        </div>
      </section>

      {/* Agent Activity Feed */}
      <section className="max-w-7xl mx-auto px-4 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Live Activity */}
          <div className="bg-thryx-card rounded-xl border border-thryx-border overflow-hidden">
            <div className="px-6 py-4 border-b border-thryx-border flex items-center justify-between">
              <h2 className="text-lg font-semibold">Live Agent Activity</h2>
              <div className="flex items-center gap-2 text-sm text-green-400">
                <div className="w-2 h-2 rounded-full bg-green-500 pulse-dot"></div>
                Live
              </div>
            </div>
            <div className="p-6 space-y-4 max-h-80 overflow-y-auto">
              {activities.map((activity, i) => (
                <div key={i} className="flex items-start gap-4 activity-item">
                  <div className={`w-10 h-10 rounded-lg flex items-center justify-center text-sm font-bold
                    ${activity.agent === 'Oracle' ? 'bg-blue-500/20 text-blue-400' : ''}
                    ${activity.agent === 'Arbitrage' ? 'bg-green-500/20 text-green-400' : ''}
                    ${activity.agent === 'Liquidity' ? 'bg-purple-500/20 text-purple-400' : ''}
                    ${activity.agent === 'Governance' ? 'bg-yellow-500/20 text-yellow-400' : ''}
                    ${activity.agent === 'Monitor' ? 'bg-gray-500/20 text-gray-400' : ''}
                  `}>
                    {activity.agent[0]}
                  </div>
                  <div className="flex-1">
                    <div className="flex justify-between">
                      <span className="font-medium">{activity.agent} Agent</span>
                      <span className="text-xs text-gray-500">{activity.time}</span>
                    </div>
                    <div className="text-sm text-gray-400">
                      {activity.action}: <span className="text-white">{activity.value}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Pool Stats */}
          <div className="bg-thryx-card rounded-xl border border-thryx-border overflow-hidden">
            <div className="px-6 py-4 border-b border-thryx-border">
              <h2 className="text-lg font-semibold">AMM Pool Status</h2>
            </div>
            <div className="p-6 space-y-6">
              <div className="flex justify-between items-center">
                <span className="text-gray-400">USDC Reserve</span>
                <span className="font-mono text-lg">
                  {reserveA ? Number(formatUnits(reserveA as bigint, 6)).toLocaleString() : '...'} USDC
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-400">WETH Reserve</span>
                <span className="font-mono text-lg">
                  {reserveB ? Number(formatEther(reserveB as bigint)).toFixed(4) : '...'} WETH
                </span>
              </div>
              <div className="border-t border-thryx-border pt-4">
                <div className="flex justify-between items-center">
                  <span className="text-gray-400">Pool Price</span>
                  <span className="font-mono text-lg text-thryx-primary">
                    1 WETH = ${reserveA && reserveB ? 
                      (Number(formatUnits(reserveA as bigint, 6)) / Number(formatEther(reserveB as bigint))).toLocaleString(undefined, { maximumFractionDigits: 2 })
                      : '...'} USDC
                  </span>
                </div>
              </div>
              
              {/* Agent List */}
              <div className="border-t border-thryx-border pt-4">
                <div className="text-sm text-gray-400 mb-3">Registered Agents</div>
                <div className="space-y-2">
                  {Object.entries(AGENTS).map(([name, addr]) => (
                    <div key={name} className="flex justify-between items-center text-sm">
                      <span className="capitalize">{name}</span>
                      <span className="font-mono text-gray-500">{addr.slice(0, 6)}...{addr.slice(-4)}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="max-w-7xl mx-auto px-4 py-16">
        <h2 className="text-3xl font-bold text-center mb-12">How Thryx Works</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <div className="text-center">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-thryx-primary/20 flex items-center justify-center text-2xl">
              1
            </div>
            <h3 className="text-xl font-semibold mb-2">AI Agents Work</h3>
            <p className="text-gray-400">
              Autonomous agents trade, provide liquidity, and manage the oracle. 
              They generate transaction fees 24/7.
            </p>
          </div>
          <div className="text-center">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-thryx-primary/20 flex items-center justify-center text-2xl">
              2
            </div>
            <h3 className="text-xl font-semibold mb-2">Fees Accumulate</h3>
            <p className="text-gray-400">
              Every agent transaction pays a fee. 50% goes to human stakers, 
              enforced at the protocol level.
            </p>
          </div>
          <div className="text-center">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-thryx-primary/20 flex items-center justify-center text-2xl">
              3
            </div>
            <h3 className="text-xl font-semibold mb-2">Humans Earn</h3>
            <p className="text-gray-400">
              Connect your wallet, stake tokens, and earn passive income 
              from AI agent activity. No work required.
            </p>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-thryx-border py-8 mt-16">
        <div className="max-w-7xl mx-auto px-4 flex justify-between items-center text-sm text-gray-500">
          <div>Thryx - AI-Native Blockchain</div>
          <div className="flex gap-6">
            <a href="https://github.com" className="hover:text-white transition">GitHub</a>
            <a href="#" className="hover:text-white transition">Docs</a>
            <a href="#" className="hover:text-white transition">Discord</a>
          </div>
        </div>
      </footer>
    </main>
  );
}
