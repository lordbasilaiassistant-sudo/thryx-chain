'use client';

import { useState, useEffect } from 'react';
import { useAccount, usePublicClient } from 'wagmi';
import { formatEther } from 'viem';
import { thryx } from '@/lib/wagmi';

interface Transaction {
  hash: string;
  from: string;
  to: string;
  value: string;
  blockNumber: number;
  type: 'sent' | 'received';
}

export function TransactionHistory() {
  const { address } = useAccount();
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);

  const publicClient = usePublicClient({ chainId: thryx.id });

  useEffect(() => {
    const fetchTransactions = async () => {
      if (!address || !publicClient) return;

      setLoading(true);
      try {
        const currentBlock = await publicClient.getBlockNumber();
        const txs: Transaction[] = [];

        // Scan last 100 blocks for transactions involving this address
        const startBlock = currentBlock > 100n ? currentBlock - 100n : 0n;

        for (let i = currentBlock; i > startBlock && txs.length < 10; i--) {
          try {
            const block = await publicClient.getBlock({
              blockNumber: i,
              includeTransactions: true,
            });

            for (const tx of block.transactions) {
              if (typeof tx === 'object') {
                const from = tx.from?.toLowerCase();
                const to = tx.to?.toLowerCase();
                const addr = address.toLowerCase();

                if (from === addr || to === addr) {
                  txs.push({
                    hash: tx.hash,
                    from: tx.from,
                    to: tx.to || '',
                    value: formatEther(tx.value),
                    blockNumber: Number(block.number),
                    type: from === addr ? 'sent' : 'received',
                  });
                }
              }
            }
          } catch (e) {
            // Skip problematic blocks
          }
        }

        setTransactions(txs);
      } catch (e) {
        console.error('Error fetching transactions:', e);
      }
      setLoading(false);
    };

    fetchTransactions();
    const interval = setInterval(fetchTransactions, 30000);
    return () => clearInterval(interval);
  }, [address, publicClient]);

  const shortenAddress = (addr: string) => 
    `${addr.slice(0, 6)}...${addr.slice(-4)}`;

  return (
    <div className="card">
      <h3 className="font-semibold text-lg mb-4 flex items-center gap-2">
        <span className="text-xl">📜</span>
        Recent Transactions
      </h3>

      {loading ? (
        <div className="text-center py-8 text-gray-500">
          <div className="animate-spin text-2xl mb-2">⏳</div>
          <p>Loading transactions...</p>
        </div>
      ) : transactions.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          <p className="text-2xl mb-2">📭</p>
          <p>No transactions yet</p>
        </div>
      ) : (
        <div className="space-y-3">
          {transactions.map((tx) => (
            <div
              key={tx.hash}
              className="flex items-center justify-between py-3 border-b border-thryx-border last:border-0"
            >
              <div className="flex items-center gap-3">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                  tx.type === 'sent' ? 'bg-red-500/20 text-red-400' : 'bg-green-500/20 text-green-400'
                }`}>
                  {tx.type === 'sent' ? '↑' : '↓'}
                </div>
                <div>
                  <p className="font-medium text-sm">
                    {tx.type === 'sent' ? 'Sent' : 'Received'}
                  </p>
                  <p className="text-xs text-gray-500">
                    {tx.type === 'sent' ? `To: ${shortenAddress(tx.to)}` : `From: ${shortenAddress(tx.from)}`}
                  </p>
                </div>
              </div>
              <div className="text-right">
                <p className={`font-medium ${tx.type === 'sent' ? 'text-red-400' : 'text-green-400'}`}>
                  {tx.type === 'sent' ? '-' : '+'}{parseFloat(tx.value).toFixed(4)} ETH
                </p>
                <a
                  href={`${process.env.NEXT_PUBLIC_THRYX_EXPLORER || 'http://localhost:5100'}`}
                  target="_blank"
                  className="text-xs text-gray-500 hover:text-thryx-primary"
                >
                  Block #{tx.blockNumber}
                </a>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
