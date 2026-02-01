"""
Thryx Chain Connection
"""
import json
import asyncio
from typing import Optional, Dict, Any
from web3 import Web3, AsyncWeb3
from web3.middleware import ExtraDataToPOAMiddleware
from eth_account import Account
from pathlib import Path


class ThryxChain:
    """Connection to Thryx blockchain"""
    
    # Default RPC endpoints
    MAINNET_RPC = "http://localhost:8545"
    TESTNET_RPC = "http://localhost:8545"
    
    def __init__(
        self,
        rpc_url: str = None,
        private_key: str = None,
        deployment_path: str = None
    ):
        """
        Initialize Thryx chain connection.
        
        Args:
            rpc_url: RPC endpoint URL (defaults to localhost:8545)
            private_key: Private key for signing transactions
            deployment_path: Path to deployment.json for contract addresses
        """
        self.rpc_url = rpc_url or self.MAINNET_RPC
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        self.w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
        
        self.account = None
        if private_key:
            self.account = Account.from_key(private_key)
        
        self.contracts: Dict[str, str] = {}
        self._load_deployment(deployment_path)
    
    def _load_deployment(self, path: str = None):
        """Load contract addresses from deployment.json"""
        if path is None:
            # Try common locations
            for p in ["deployment.json", "../deployment.json", "/app/deployment.json"]:
                if Path(p).exists():
                    path = p
                    break
        
        if path and Path(path).exists():
            with open(path) as f:
                data = json.load(f)
                self.contracts = data.get("contracts", {})
    
    @property
    def connected(self) -> bool:
        """Check if connected to RPC"""
        try:
            self.w3.eth.block_number
            return True
        except:
            return False
    
    @property
    def block_number(self) -> int:
        """Get current block number"""
        return self.w3.eth.block_number
    
    @property
    def chain_id(self) -> int:
        """Get chain ID"""
        return self.w3.eth.chain_id
    
    @property
    def address(self) -> Optional[str]:
        """Get connected wallet address"""
        return self.account.address if self.account else None
    
    def get_balance(self, address: str = None) -> int:
        """Get ETH balance in wei"""
        addr = address or self.address
        if not addr:
            raise ValueError("No address provided")
        return self.w3.eth.get_balance(addr)
    
    def get_contract(self, name: str, abi: list) -> Any:
        """Get contract instance by name"""
        address = self.contracts.get(name)
        if not address:
            raise ValueError(f"Contract {name} not found in deployment")
        return self.w3.eth.contract(address=address, abi=abi)
    
    def send_transaction(self, tx: dict, wait: bool = True) -> Optional[str]:
        """Send a signed transaction"""
        if not self.account:
            raise ValueError("No account configured for signing")
        
        tx['nonce'] = self.w3.eth.get_transaction_count(self.address)
        tx['from'] = self.address
        tx['chainId'] = self.chain_id
        
        if 'gas' not in tx:
            tx['gas'] = self.w3.eth.estimate_gas(tx)
        
        if 'maxFeePerGas' not in tx:
            base_fee = self.w3.eth.get_block('latest')['baseFeePerGas']
            tx['maxFeePerGas'] = base_fee * 2
            tx['maxPriorityFeePerGas'] = self.w3.to_wei(1, 'gwei')
        
        signed = self.account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        
        if wait:
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
            return tx_hash.hex() if receipt['status'] == 1 else None
        
        return tx_hash.hex()
    
    def call_contract(self, contract: Any, function: str, *args) -> Any:
        """Call a contract view function"""
        func = getattr(contract.functions, function)
        return func(*args).call()
    
    def build_tx(self, contract: Any, function: str, *args) -> dict:
        """Build a contract transaction"""
        func = getattr(contract.functions, function)
        return func(*args).build_transaction({'from': self.address})


class AsyncThryxChain(ThryxChain):
    """Async version of ThryxChain for high-performance agents"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.async_w3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(self.rpc_url))
    
    async def get_block_number(self) -> int:
        return await self.async_w3.eth.block_number
    
    async def get_balance_async(self, address: str = None) -> int:
        addr = address or self.address
        return await self.async_w3.eth.get_balance(addr)
