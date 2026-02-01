'use client';

import { useState } from 'react';
import { useAccount, useBalance, useSendTransaction, useChainId, useSwitchChain } from 'wagmi';
import { parseEther, formatEther } from 'viem';
import { base } from 'wagmi/chains';
import { thryx, BRIDGE_WALLET } from '@/lib/wagmi';

type BridgeDirection = 'to-thryx' | 'from-thryx';

export function BridgePanel() {
  const { address } = useAccount();
  const chainId = useChainId();
  const { switchChain } = useSwitchChain();
  const [direction, setDirection] = useState<BridgeDirection>('to-thryx');
  const [amount, setAmount] = useState('');
  const [status, setStatus] = useState<'idle' | 'pending' | 'success' | 'error'>('idle');

  // Base ETH balance
  const { data: baseBalance } = useBalance({
    address,
    chainId: base.id,
  });

  // THRYX ETH balance
  const { data: thryxBalance } = useBalance({
    address,
    chainId: thryx.id,
  });

  const { sendTransaction, isPending } = useSendTransaction();

  const handleBridge = async () => {
    if (!amount || parseFloat(amount) <= 0) return;

    setStatus('pending');

    try {
      if (direction === 'to-thryx') {
        // Bridge TO THRYX: Send ETH to bridge wallet on Base
        if (chainId !== base.id) {
          await switchChain?.({ chainId: base.id });
          return; // User needs to retry after switching
        }

        sendTransaction({
          to: BRIDGE_WALLET as `0x${string}`,
          value: parseEther(amount),
          chainId: base.id,
        });
      } else {
        // Bridge FROM THRYX: This requires the withdrawal bridge
        // For now, show instructions
        setStatus('idle');
        alert('To withdraw from THRYX to Base, please use the withdrawal bridge CLI tool. Contact support for assistance.');
        return;
      }
      
      setStatus('success');
      setAmount('');
    } catch (e) {
      setStatus('error');
    }
  };

  const sourceChain = direction === 'to-thryx' ? 'Base' : 'THRYX';
  const destChain = direction === 'to-thryx' ? 'THRYX' : 'Base';
  const sourceBalance = direction === 'to-thryx' ? baseBalance : thryxBalance;

  return (
    <div className="card">
      <h3 className="font-semibold text-lg mb-4 flex items-center gap-2">
        <span className="text-xl">🌉</span>
        Bridge
      </h3>

      {/* Direction Toggle */}
      <div className="flex gap-2 mb-4">
        <button
          onClick={() => setDirection('to-thryx')}
          className={`flex-1 py-2 px-4 rounded-lg text-sm font-medium transition-colors ${
            direction === 'to-thryx' 
              ? 'bg-thryx-primary text-white' 
              : 'bg-thryx-dark text-gray-400 hover:text-white'
          }`}
        >
          Base → THRYX
        </button>
        <button
          onClick={() => setDirection('from-thryx')}
          className={`flex-1 py-2 px-4 rounded-lg text-sm font-medium transition-colors ${
            direction === 'from-thryx' 
              ? 'bg-thryx-primary text-white' 
              : 'bg-thryx-dark text-gray-400 hover:text-white'
          }`}
        >
          THRYX → Base
        </button>
      </div>

      {/* Bridge Flow Visual */}
      <div className="bg-thryx-dark rounded-lg p-4 mb-4">
        <div className="flex items-center justify-between text-sm">
          <div className="text-center">
            <div className="w-12 h-12 bg-thryx-card rounded-full flex items-center justify-center mx-auto mb-2">
              {direction === 'to-thryx' ? '🔵' : '🟣'}
            </div>
            <p className="font-medium">{sourceChain}</p>
            <p className="text-xs text-gray-500">
              {sourceBalance ? formatEther(sourceBalance.value).slice(0, 8) : '0.00'} ETH
            </p>
          </div>
          
          <div className="flex-1 mx-4">
            <div className="h-0.5 bg-gradient-to-r from-thryx-primary to-thryx-secondary relative">
              <span className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 text-lg">
                →
              </span>
            </div>
          </div>
          
          <div className="text-center">
            <div className="w-12 h-12 bg-thryx-card rounded-full flex items-center justify-center mx-auto mb-2">
              {direction === 'to-thryx' ? '🟣' : '🔵'}
            </div>
            <p className="font-medium">{destChain}</p>
            <p className="text-xs text-gray-500">1:1 Rate</p>
          </div>
        </div>
      </div>

      {/* Amount Input */}
      <div className="mb-4">
        <label className="text-sm text-gray-400 mb-2 block">Amount (ETH)</label>
        <div className="relative">
          <input
            type="number"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            placeholder="0.0"
            step="0.001"
            min="0"
            className="input w-full pr-16"
          />
          <button
            onClick={() => setAmount(sourceBalance ? formatEther(sourceBalance.value) : '0')}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-xs text-thryx-primary hover:underline"
          >
            MAX
          </button>
        </div>
      </div>

      {/* Bridge Info */}
      <div className="bg-thryx-dark rounded-lg p-3 mb-4 text-xs text-gray-400 space-y-1">
        <div className="flex justify-between">
          <span>Fee</span>
          <span className="text-white">Free</span>
        </div>
        <div className="flex justify-between">
          <span>Time</span>
          <span className="text-white">~30 seconds</span>
        </div>
        <div className="flex justify-between">
          <span>You receive</span>
          <span className="text-white">{amount || '0'} ETH</span>
        </div>
      </div>

      {/* Bridge Button */}
      <button
        onClick={handleBridge}
        disabled={isPending || !amount || parseFloat(amount) <= 0}
        className="btn-primary w-full disabled:opacity-50"
      >
        {isPending ? 'Confirming...' : `Bridge to ${destChain}`}
      </button>

      {/* Status Messages */}
      {status === 'success' && (
        <div className="mt-4 bg-green-500/10 border border-green-500/30 rounded-lg p-3 text-green-400 text-sm">
          Transaction sent! Your {destChain} ETH will arrive in ~30 seconds.
        </div>
      )}

      {status === 'error' && (
        <div className="mt-4 bg-red-500/10 border border-red-500/30 rounded-lg p-3 text-red-400 text-sm">
          Bridge failed. Please try again.
        </div>
      )}

      {/* Bridge Wallet Info */}
      {direction === 'to-thryx' && (
        <div className="mt-4 text-xs text-gray-500">
          <p className="mb-1">Bridge Wallet:</p>
          <p className="font-mono break-all">{BRIDGE_WALLET}</p>
        </div>
      )}
    </div>
  );
}
