'use client';

import { useState, useEffect } from 'react';
import { usePublicClient } from 'wagmi';
import { thryx } from '@/lib/wagmi';

export function NetworkStatus() {
  const [blockNumber, setBlockNumber] = useState<number>(0);
  const [isConnected, setIsConnected] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);

  const publicClient = usePublicClient({ chainId: thryx.id });

  useEffect(() => {
    const checkConnection = async () => {
      try {
        if (publicClient) {
          const block = await publicClient.getBlockNumber();
          setBlockNumber(Number(block));
          setIsConnected(true);
          setLastUpdate(new Date());
        }
      } catch (e) {
        setIsConnected(false);
      }
    };

    checkConnection();
    const interval = setInterval(checkConnection, 5000);
    return () => clearInterval(interval);
  }, [publicClient]);

  return (
    <div className="flex items-center gap-2 bg-thryx-card border border-thryx-border rounded-lg px-3 py-2">
      <div 
        className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}
        title={isConnected ? 'Connected' : 'Disconnected'}
      />
      <div className="text-xs">
        <p className="text-gray-400">THRYX</p>
        <p className="font-mono text-white">
          {isConnected ? `#${blockNumber.toLocaleString()}` : 'Offline'}
        </p>
      </div>
    </div>
  );
}
