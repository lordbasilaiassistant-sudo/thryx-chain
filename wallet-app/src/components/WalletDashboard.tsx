'use client';

import { useState } from 'react';
import { useAccount, useBalance, useSendTransaction, useWaitForTransactionReceipt, useChainId } from 'wagmi';
import { parseEther, formatEther } from 'viem';
import { base } from 'wagmi/chains';
import { thryx, CONTRACTS } from '@/lib/wagmi';

export function WalletDashboard() {
  const { address } = useAccount();
  const chainId = useChainId();
  const [showSend, setShowSend] = useState(false);
  const [recipient, setRecipient] = useState('');
  const [amount, setAmount] = useState('');

  // ETH Balance on THRYX
  const { data: thryxEthBalance, refetch: refetchThryxEth } = useBalance({
    address,
    chainId: thryx.id,
  });

  // ETH Balance on Base
  const { data: baseEthBalance, refetch: refetchBaseEth } = useBalance({
    address,
    chainId: base.id,
  });

  // USDC Balance on THRYX
  const { data: thryxUsdcBalance, refetch: refetchThryxUsdc } = useBalance({
    address,
    token: CONTRACTS.USDC as `0x${string}`,
    chainId: thryx.id,
  });

  // USDC Balance on Base  
  const { data: baseUsdcBalance, refetch: refetchBaseUsdc } = useBalance({
    address,
    token: '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913' as `0x${string}`,
    chainId: base.id,
  });

  // For backwards compatibility
  const ethBalance = thryxEthBalance;
  const usdcBalance = thryxUsdcBalance;

  const { sendTransaction, data: txHash, isPending } = useSendTransaction();
  const { isLoading: isConfirming, isSuccess } = useWaitForTransactionReceipt({
    hash: txHash,
  });

  const handleSend = () => {
    if (!recipient || !amount) return;
    
    sendTransaction({
      to: recipient as `0x${string}`,
      value: parseEther(amount),
      chainId: thryx.id,
    });
  };

  const refreshBalances = () => {
    refetchThryxEth();
    refetchBaseEth();
    refetchThryxUsdc();
    refetchBaseUsdc();
  };

  const isOnThryx = chainId === thryx.id;
  const isOnBase = chainId === base.id;

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-bold">Wallet</h2>
        <button 
          onClick={refreshBalances}
          className="text-gray-400 hover:text-white transition-colors"
          title="Refresh balances"
        >
          🔄
        </button>
      </div>

      {/* Address */}
      <div className="bg-thryx-dark rounded-lg p-4 mb-6">
        <p className="text-xs text-gray-500 mb-1">Connected Address</p>
        <p className="font-mono text-sm break-all">{address}</p>
        <p className="text-xs text-gray-500 mt-2">
          Currently on: <span className={isOnThryx ? 'text-purple-400' : isOnBase ? 'text-blue-400' : 'text-yellow-400'}>
            {isOnThryx ? 'THRYX' : isOnBase ? 'Base' : 'Other Network'}
          </span>
        </p>
      </div>

      {/* THRYX Balances */}
      <div className="mb-4">
        <h3 className="text-sm font-semibold text-purple-400 mb-2 flex items-center gap-2">
          <span className="w-2 h-2 bg-purple-400 rounded-full"></span>
          THRYX Chain
        </h3>
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-thryx-dark rounded-lg p-4">
            <p className="text-xs text-gray-500 mb-1">ETH</p>
            <p className="text-xl font-bold">
              {thryxEthBalance ? formatEther(thryxEthBalance.value).slice(0, 8) : '0.00'}
            </p>
          </div>
          <div className="bg-thryx-dark rounded-lg p-4">
            <p className="text-xs text-gray-500 mb-1">USDC</p>
            <p className="text-xl font-bold">
              {thryxUsdcBalance ? Number(thryxUsdcBalance.formatted).toFixed(2) : '0.00'}
            </p>
          </div>
        </div>
      </div>

      {/* Base Balances */}
      <div className="mb-6">
        <h3 className="text-sm font-semibold text-blue-400 mb-2 flex items-center gap-2">
          <span className="w-2 h-2 bg-blue-400 rounded-full"></span>
          Base Chain
        </h3>
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-thryx-dark rounded-lg p-4">
            <p className="text-xs text-gray-500 mb-1">ETH</p>
            <p className="text-xl font-bold">
              {baseEthBalance ? formatEther(baseEthBalance.value).slice(0, 8) : '0.00'}
            </p>
          </div>
          <div className="bg-thryx-dark rounded-lg p-4">
            <p className="text-xs text-gray-500 mb-1">USDC</p>
            <p className="text-xl font-bold">
              {baseUsdcBalance ? Number(baseUsdcBalance.formatted).toFixed(2) : '0.00'}
            </p>
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-4">
        <button 
          onClick={() => setShowSend(!showSend)}
          className="btn-primary flex-1"
        >
          {showSend ? 'Cancel' : 'Send ETH'}
        </button>
        <button 
          onClick={() => window.open(`${process.env.NEXT_PUBLIC_THRYX_EXPLORER || 'http://localhost:5100'}`, '_blank')}
          className="btn-secondary flex-1"
        >
          View Explorer
        </button>
      </div>

      {/* Send Form */}
      {showSend && (
        <div className="mt-6 space-y-4 border-t border-thryx-border pt-6">
          <div>
            <label className="text-sm text-gray-400 mb-2 block">Recipient Address</label>
            <input
              type="text"
              value={recipient}
              onChange={(e) => setRecipient(e.target.value)}
              placeholder="0x..."
              className="input w-full"
            />
          </div>
          <div>
            <label className="text-sm text-gray-400 mb-2 block">Amount (ETH)</label>
            <input
              type="number"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              placeholder="0.0"
              step="0.001"
              className="input w-full"
            />
          </div>
          <button 
            onClick={handleSend}
            disabled={isPending || isConfirming || !recipient || !amount}
            className="btn-primary w-full disabled:opacity-50"
          >
            {isPending ? 'Confirm in Wallet...' : isConfirming ? 'Sending...' : 'Send'}
          </button>
          
          {isSuccess && (
            <div className="bg-green-500/10 border border-green-500/30 rounded-lg p-4 text-green-400 text-sm">
              Transaction successful! 
              <a 
                href={`${process.env.NEXT_PUBLIC_THRYX_EXPLORER || 'http://localhost:5100'}`}
                target="_blank"
                className="underline ml-2"
              >
                View in Explorer
              </a>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
