from web3 import Web3
w3 = Web3(Web3.HTTPProvider('http://localhost:8545'))
addr = '0x718d6142Fb15F95F43FaC6F70498d8Da130240BC'
bal = w3.eth.get_balance(addr)
print(f"THRYX ETH Balance for {addr[:10]}...: {w3.from_wei(bal, 'ether')} ETH")
