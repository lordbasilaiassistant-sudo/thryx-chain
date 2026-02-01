// THRYX Wallet - Core Logic
const DEFAULT_RPC = 'https://greeting-modifications-confidentiality-agenda.trycloudflare.com';
const LOCAL_RPC = 'http://localhost:8545';
const CHAIN_ID = 31337;

// Pre-configured wallet address (Anthony's bridge wallet)
const PRECONFIGURED_ADDRESS = '0x03F2B0AE7f6badE9944d2CFB8Ad66b62CF6ba1d4';

let wallet = null;
let rpcUrl = DEFAULT_RPC;
let watchOnly = false;

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
  // Load saved data
  const saved = await chrome.storage.local.get(['privateKey', 'rpcUrl', 'watchAddress', 'watchOnly']);
  
  if (saved.rpcUrl) {
    rpcUrl = saved.rpcUrl;
  }
  
  document.getElementById('rpcInput').value = rpcUrl;
  
  if (saved.privateKey) {
    wallet = loadWallet(saved.privateKey);
    watchOnly = false;
    showMainScreen();
  } else if (saved.watchAddress) {
    wallet = {
      privateKey: null,
      address: saved.watchAddress
    };
    watchOnly = true;
    showMainScreen();
  } else {
    showSetupScreen();
  }
  
  checkConnection();
});

// RPC call helper
async function rpc(method, params = []) {
  const response = await fetch(rpcUrl, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      jsonrpc: '2.0',
      id: Date.now(),
      method,
      params
    })
  });
  const data = await response.json();
  if (data.error) throw new Error(data.error.message);
  return data.result;
}

// Check connection
async function checkConnection() {
  try {
    const chainId = await rpc('eth_chainId');
    document.getElementById('statusDot').classList.remove('offline');
    document.getElementById('statusText').textContent = 'Connected';
    return true;
  } catch (e) {
    document.getElementById('statusDot').classList.add('offline');
    document.getElementById('statusText').textContent = 'Offline';
    return false;
  }
}

// Simple wallet implementation (no external deps)
function loadWallet(privateKey) {
  // Remove 0x prefix if present
  const key = privateKey.startsWith('0x') ? privateKey.slice(2) : privateKey;
  
  // Derive address from private key (simplified - uses keccak256)
  return {
    privateKey: '0x' + key,
    address: deriveAddress(key)
  };
}

// Derive Ethereum address from private key
function deriveAddress(privateKeyHex) {
  // This is a simplified version - in production use ethers.js
  // For now, we'll store the address separately or compute it properly
  // Using secp256k1 would require a library
  
  // Placeholder - will be set during import/create
  return localStorage.getItem('thryx_address') || '0x0000000000000000000000000000000000000000';
}

// Create new wallet
async function createWallet() {
  // Generate random private key
  const array = new Uint8Array(32);
  crypto.getRandomValues(array);
  const privateKey = '0x' + Array.from(array).map(b => b.toString(16).padStart(2, '0')).join('');
  
  // For address derivation, we need to compute public key
  // Simplified: store and derive on first use via RPC signing
  
  // Save RPC URL
  rpcUrl = document.getElementById('rpcInput').value || DEFAULT_RPC;
  
  // Create account via eth_accounts or similar
  // For demo, we'll use a deterministic address based on key hash
  const address = await computeAddressFromKey(privateKey);
  
  wallet = {
    privateKey,
    address
  };
  
  localStorage.setItem('thryx_address', address);
  
  await chrome.storage.local.set({ 
    privateKey,
    rpcUrl 
  });
  
  // Show private key to user (they need to save it)
  alert(`SAVE YOUR PRIVATE KEY!\n\n${privateKey}\n\nThis is the only way to recover your wallet.`);
  
  showMainScreen();
}

// Compute address from private key using Web Crypto
async function computeAddressFromKey(privateKey) {
  // For proper derivation we'd need secp256k1
  // Simplified approach: hash the private key to create a deterministic address
  const keyBytes = hexToBytes(privateKey.slice(2));
  const hashBuffer = await crypto.subtle.digest('SHA-256', keyBytes);
  const hashArray = new Uint8Array(hashBuffer);
  
  // Take last 20 bytes as address (simplified, not real ECDSA)
  const addressBytes = hashArray.slice(12, 32);
  const address = '0x' + Array.from(addressBytes).map(b => b.toString(16).padStart(2, '0')).join('');
  
  return address;
}

function hexToBytes(hex) {
  const bytes = new Uint8Array(hex.length / 2);
  for (let i = 0; i < hex.length; i += 2) {
    bytes[i / 2] = parseInt(hex.substr(i, 2), 16);
  }
  return bytes;
}

function bytesToHex(bytes) {
  return Array.from(bytes).map(b => b.toString(16).padStart(2, '0')).join('');
}

// Show import section
function showImport() {
  document.getElementById('importSection').style.display = 'block';
  document.getElementById('watchSection').style.display = 'none';
}

// Show watch address section
function showWatchAddress() {
  document.getElementById('watchSection').style.display = 'block';
  document.getElementById('importSection').style.display = 'none';
}

// Quick connect with pre-configured address
async function quickConnect() {
  rpcUrl = document.getElementById('rpcInput').value || DEFAULT_RPC;
  
  wallet = {
    privateKey: null,
    address: PRECONFIGURED_ADDRESS
  };
  watchOnly = true;
  
  await chrome.storage.local.set({ 
    watchAddress: PRECONFIGURED_ADDRESS,
    rpcUrl,
    watchOnly: true
  });
  
  showMainScreen();
}

// Watch any address
async function watchAddress() {
  const address = document.getElementById('watchAddressInput').value.trim();
  
  if (!address || !address.startsWith('0x') || address.length !== 42) {
    alert('Invalid address');
    return;
  }
  
  rpcUrl = document.getElementById('rpcInput').value || DEFAULT_RPC;
  
  wallet = {
    privateKey: null,
    address: address
  };
  watchOnly = true;
  
  await chrome.storage.local.set({ 
    watchAddress: address,
    rpcUrl,
    watchOnly: true
  });
  
  showMainScreen();
}

// Import wallet from private key
async function importWallet() {
  const privateKey = document.getElementById('privateKeyInput').value.trim();
  
  if (!privateKey || privateKey.length < 64) {
    alert('Invalid private key');
    return;
  }
  
  const key = privateKey.startsWith('0x') ? privateKey : '0x' + privateKey;
  
  // Save RPC URL
  rpcUrl = document.getElementById('rpcInput').value || DEFAULT_RPC;
  
  // Compute address
  const address = await computeAddressFromKey(key);
  
  wallet = {
    privateKey: key,
    address
  };
  
  localStorage.setItem('thryx_address', address);
  
  await chrome.storage.local.set({ 
    privateKey: key,
    rpcUrl 
  });
  
  showMainScreen();
}

// Show screens
function showSetupScreen() {
  document.getElementById('setupScreen').style.display = 'block';
  document.getElementById('mainScreen').style.display = 'none';
}

function showMainScreen() {
  document.getElementById('setupScreen').style.display = 'none';
  document.getElementById('mainScreen').style.display = 'block';
  
  // Show address
  const addr = wallet.address;
  document.getElementById('addressText').textContent = addr.slice(0, 8) + '...' + addr.slice(-6);
  
  try {
    document.getElementById('rpcDisplay').textContent = new URL(rpcUrl).hostname.slice(0, 20) + '...';
  } catch {
    document.getElementById('rpcDisplay').textContent = rpcUrl.slice(0, 20) + '...';
  }
  
  // Update UI for watch-only mode
  const sendBtn = document.querySelector('.actions .action-btn');
  if (watchOnly) {
    sendBtn.textContent = 'Watch Only';
    sendBtn.disabled = true;
    sendBtn.style.opacity = '0.5';
  } else {
    sendBtn.textContent = 'Send';
    sendBtn.disabled = false;
    sendBtn.style.opacity = '1';
  }
  
  // Get balance
  refreshBalance();
}

// Refresh balance
async function refreshBalance() {
  if (!wallet) return;
  
  try {
    const balanceHex = await rpc('eth_getBalance', [wallet.address, 'latest']);
    const balanceWei = BigInt(balanceHex);
    const balanceEth = Number(balanceWei) / 1e18;
    
    document.getElementById('balanceValue').textContent = balanceEth.toFixed(6);
  } catch (e) {
    console.error('Balance error:', e);
    document.getElementById('balanceValue').textContent = 'Error';
  }
}

// Copy address
function copyAddress() {
  if (!wallet) return;
  navigator.clipboard.writeText(wallet.address);
  alert('Address copied!');
}

// Send modal
function showSendModal() {
  document.getElementById('sendModal').classList.add('active');
  document.getElementById('sendError').style.display = 'none';
  document.getElementById('sendSuccess').style.display = 'none';
  document.getElementById('sendTo').value = '';
  document.getElementById('sendAmount').value = '';
}

function closeSendModal() {
  document.getElementById('sendModal').classList.remove('active');
}

// Send transaction
async function sendTransaction() {
  const to = document.getElementById('sendTo').value.trim();
  const amount = document.getElementById('sendAmount').value.trim();
  
  if (!to || !to.startsWith('0x') || to.length !== 42) {
    document.getElementById('sendError').textContent = 'Invalid recipient address';
    document.getElementById('sendError').style.display = 'block';
    return;
  }
  
  if (!amount || isNaN(parseFloat(amount)) || parseFloat(amount) <= 0) {
    document.getElementById('sendError').textContent = 'Invalid amount';
    document.getElementById('sendError').style.display = 'block';
    return;
  }
  
  document.getElementById('sendError').style.display = 'none';
  document.getElementById('sendBtn').textContent = 'Sending...';
  document.getElementById('sendBtn').disabled = true;
  
  try {
    // Convert amount to wei
    const valueWei = BigInt(Math.floor(parseFloat(amount) * 1e18));
    const valueHex = '0x' + valueWei.toString(16);
    
    // Get nonce
    const nonce = await rpc('eth_getTransactionCount', [wallet.address, 'latest']);
    
    // Get gas price
    const gasPrice = await rpc('eth_gasPrice');
    
    // Build transaction
    const tx = {
      from: wallet.address,
      to: to,
      value: valueHex,
      gas: '0x5208', // 21000
      gasPrice: gasPrice,
      nonce: nonce,
      chainId: '0x' + CHAIN_ID.toString(16)
    };
    
    // For signing, we'd need proper ECDSA
    // Using eth_sendTransaction with unlocked accounts (Hardhat allows this)
    const txHash = await rpc('eth_sendTransaction', [tx]);
    
    document.getElementById('sendSuccess').textContent = 'Sent! TX: ' + txHash.slice(0, 20) + '...';
    document.getElementById('sendSuccess').style.display = 'block';
    
    // Refresh balance
    setTimeout(refreshBalance, 2000);
    
  } catch (e) {
    document.getElementById('sendError').textContent = e.message || 'Transaction failed';
    document.getElementById('sendError').style.display = 'block';
  }
  
  document.getElementById('sendBtn').textContent = 'Send';
  document.getElementById('sendBtn').disabled = false;
}

// Logout
async function logout() {
  if (confirm('Are you sure? Make sure you have saved your private key!')) {
    await chrome.storage.local.clear();
    localStorage.removeItem('thryx_address');
    wallet = null;
    showSetupScreen();
  }
}
