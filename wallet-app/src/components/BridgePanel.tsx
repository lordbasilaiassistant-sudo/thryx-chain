'use client';

import { useState } from 'react';
import { useAccount, useBalance, useChainId, useSwitchChain } from 'wagmi';
import { useSendTransaction, useWaitForTransactionReceipt } from 'wagmi';
import { parseEther, formatEther } from 'viem';
import { base } from 'wagmi/chains';
import { thryx, BRIDGE_WALLET } from '@/lib/wagmi';

export function BridgePanel() {
  const { address } = useAccount();
  const chainId = useChainId();
  const { switchChain } = useSwitchChain();
  const [direction, setDirection] = useState<'to-thryx' | 'from-thryx'>('to-thryx');
  const [amount, setAmount] = useState('');

  // Balances
  const { data: baseBalance, refetch: refetchBase } = useBalance({
    address,
    chainId: base.id,
  });

  const { data: thryxBalance, refetch: refetchThryx } = useBalance({
    address,
    chainId: thryx.id,
  });

  // Transaction hooks
  const { 
    sendTransaction, 
    data: txHash, 
    isPending,
    isError,
    error 
  } = useSendTransaction();
  
  const { isLoading: isConfirming, isSuccess: isConfirmed } = useWaitForTransactionReceipt({
    hash: txHash,
  });

  const isOnBase = chainId === base.id;
  const sourceBalance = direction === 'to-thryx' ? baseBalance : thryxBalance;

  const handleSwitchToBase = () => {
    switchChain?.({ chainId: base.id });
  };

  const handleBridgeClick = () => {
    console.log('Bridge clicked!', { amount, direction, chainId, isOnBase, BRIDGE_WALLET });
    
    if (!amount || parseFloat(amount) <= 0) {
      alert('Please enter a valid amount');
      return;
    }

    if (direction === 'from-thryx') {
      alert('Withdrawals from THRYX require the CLI tool. Contact support.');
      return;
    }

    if (!isOnBase) {
      alert('Please switch to Base network first, then click Bridge again.');
      handleSwitchToBase();
      return;
    }

    // Execute the transaction - this WILL trigger wallet popup
    console.log('Sending transaction to:', BRIDGE_WALLET, 'amount:', amount);
    
    sendTransaction({
      to: BRIDGE_WALLET as `0x${string}`,
      value: parseEther(amount),
    });
  };

  // Refresh balances when confirmed
  if (isConfirmed) {
    setTimeout(() => {
      refetchBase();
      refetchThryx();
    }, 3000);
  }

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

      {/* Network Status */}
      <div className={`mb-4 p-3 rounded-lg text-sm ${isOnBase ? 'bg-green-500/10 text-green-400' : 'bg-yellow-500/10 text-yellow-400'}`}>
        {isOnBase ? (
          <span>✓ Connected to Base - Ready to bridge</span>
        ) : (
          <div className="flex items-center justify-between">
            <span>⚠ Switch to Base to bridge</span>
            <button 
              onClick={handleSwitchToBase}
              className="underline hover:no-underline"
            >
              Switch Now
            </button>
          </div>
        )}
      </div>

      {/* Balance Display */}
      <div className="bg-thryx-dark rounded-lg p-4 mb-4">
        <div className="flex items-center justify-between text-sm">
          <div className="text-center">
            <div className="w-12 h-12 bg-thryx-card rounded-full flex items-center justify-center mx-auto mb-2 text-2xl">
              🔵
            </div>
            <p className="font-medium">Base</p>
            <p className="text-xs text-gray-500">
              {baseBalance ? formatEther(baseBalance.value).slice(0, 8) : '0.00'} ETH
            </p>
          </div>
          
          <div className="flex-1 mx-4">
            <div className="h-0.5 bg-gradient-to-r from-blue-500 to-purple-500 relative">
              <span className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 text-lg bg-thryx-dark px-2">
                →
              </span>
            </div>
          </div>
          
          <div className="text-center">
            <div className="w-12 h-12 bg-thryx-card rounded-full flex items-center justify-center mx-auto mb-2 text-2xl">
              🟣
            </div>
            <p className="font-medium">THRYX</p>
            <p className="text-xs text-gray-500">
              {thryxBalance ? formatEther(thryxBalance.value).slice(0, 8) : '0.00'} ETH
            </p>
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
            placeholder="0.001"
            step="0.001"
            min="0"
            className="input w-full pr-16"
          />
          <button
            onClick={() => setAmount(baseBalance ? formatEther(baseBalance.value) : '0')}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-xs text-thryx-primary hover:underline"
          >
            MAX
          </button>
        </div>
      </div>

      {/* Bridge Info */}
      <div className="bg-thryx-dark rounded-lg p-3 mb-4 text-xs text-gray-400 space-y-1">
        <div className="flex justify-between">
          <span>Rate</span>
          <span className="text-white">1:1</span>
        </div>
        <div className="flex justify-between">
          <span>Fee</span>
          <span className="text-white">Free</span>
        </div>
        <div className="flex justify-between">
          <span>Time</span>
          <span className="text-white">~30 seconds</span>
        </div>
      </div>

      {/* Bridge Button */}
      <button
        onClick={handleBridgeClick}
        disabled={isPending || isConfirming || !amount}
        className="btn-primary w-full disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {isPending ? '⏳ Confirm in Wallet...' : 
         isConfirming ? '⏳ Confirming on Base...' : 
         !isOnBase ? 'Switch to Base & Bridge' :
         'Bridge to THRYX'}
      </button>

      {/* Status Messages */}
      {isPending && (
        <div className="mt-4 bg-blue-500/10 border border-blue-500/30 rounded-lg p-3 text-blue-400 text-sm">
          Please confirm the transaction in your wallet...
        </div>
      )}

      {isConfirming && (
        <div className="mt-4 bg-blue-500/10 border border-blue-500/30 rounded-lg p-3 text-blue-400 text-sm">
          Transaction submitted! Waiting for Base confirmation...
        </div>
      )}

      {isConfirmed && (
        <div className="mt-4 bg-green-500/10 border border-green-500/30 rounded-lg p-3 text-green-400 text-sm">
          ✓ Bridge transaction confirmed! Your THRYX ETH will arrive in ~30 seconds.
          {txHash && (
            <a 
              href={`https://basescan.org/tx/${txHash}`}
              target="_blank"
              rel="noopener noreferrer"
              className="underline ml-2"
            >
              View on Basescan
            </a>
          )}
        </div>
      )}

      {isError && (
        <div className="mt-4 bg-red-500/10 border border-red-500/30 rounded-lg p-3 text-red-400 text-sm">
          Error: {error?.message || 'Transaction failed'}
        </div>
      )}

      {/* Bridge Wallet Info */}
      <div className="mt-4 text-xs text-gray-500">
        <p className="mb-1">Bridge Wallet (on Base):</p>
        <p className="font-mono break-all bg-thryx-dark p-2 rounded">{BRIDGE_WALLET}</p>
        <p className="mt-2 text-gray-600">Send ETH to this address on Base → Receive ETH on THRYX</p>
      </div>
    </div>
  );
}
