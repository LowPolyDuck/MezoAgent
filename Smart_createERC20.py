import os
import json
import time
from dotenv import load_dotenv
from web3 import Web3
import solcx

# =====================================
# Configurable Parameter (default mUSD for liquidity seeding)
# =====================================
SEED_MUSD = 100  # Default mUSD used for liquidity seeding (in whole mUSD)
DEFAULT_SEED_PERCENTAGE = 10  # Default percentage of token supply used for liquidity seeding

# =====================================
# Environment & Web3 Setup
# =====================================
load_dotenv()
RPC_URL = "https://rpc.test.mezo.org"
web3 = Web3(Web3.HTTPProvider(RPC_URL))
if not web3.is_connected():
    raise Exception("❌ Failed to connect to the RPC URL.")

PRIVATE_KEY = os.getenv("PRIVATE_KEY")
if not PRIVATE_KEY:
    raise Exception("❌ PRIVATE_KEY not found in environment variables!")
account = web3.eth.account.from_key(PRIVATE_KEY)
sender_address = account.address
print(f"🚀 Using wallet: {sender_address}")

# =====================================
# Solidity Source: Minimal ERC20 Token
# =====================================
solidity_source = '''
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;
contract MyToken {
    string public name;
    string public symbol;
    uint8 public decimals = 18;
    uint256 public totalSupply;
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;
    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);
    constructor(string memory _name, string memory _symbol, uint256 _initialSupply) {
        name = _name; symbol = _symbol;
        totalSupply = _initialSupply * (10 ** uint256(decimals));
        balanceOf[msg.sender] = totalSupply;
        emit Transfer(address(0), msg.sender, totalSupply);
    }
    function transfer(address _to, uint256 _value) public returns (bool success) {
        require(balanceOf[msg.sender] >= _value, "Insufficient balance");
        balanceOf[msg.sender] -= _value;
        balanceOf[_to] += _value;
        emit Transfer(msg.sender, _to, _value);
        return true;
    }
    function approve(address _spender, uint256 _value) public returns (bool success) {
        allowance[msg.sender][_spender] = _value;
        emit Approval(msg.sender, _spender, _value);
        return true;
    }
    function transferFrom(address _from, address _to, uint256 _value) public returns (bool success) {
        require(balanceOf[_from] >= _value, "Insufficient balance");
        require(allowance[_from][msg.sender] >= _value, "Allowance exceeded");
        balanceOf[_from] -= _value;
        balanceOf[_to] += _value;
        allowance[_from][msg.sender] -= _value;
        emit Transfer(_from, _to, _value);
        return true;
    }
}
'''
solcx.install_solc("0.8.0")
compiled_sol = solcx.compile_standard({
  "language": "Solidity",
  "sources": {"MyToken.sol": {"content": solidity_source}},
  "settings": {"outputSelection": {"*": {"*": ["abi", "evm.bytecode.object"]}}}
}, solc_version="0.8.0")
token_abi = compiled_sol["contracts"]["MyToken.sol"]["MyToken"]["abi"]
token_bytecode = compiled_sol["contracts"]["MyToken.sol"]["MyToken"]["evm"]["bytecode"]["object"]

# =====================================
# Router & Token Configuration
# =====================================
DUMPY_ROUTER_ADDRESS = "0xe3eB6Aa5CFB0BdA17C22128A58830EBC8Ecb74C3"
with open("ABIs/new_router_abi.json", "r") as f:
    router_abi = json.load(f)
router_contract = web3.eth.contract(address=DUMPY_ROUTER_ADDRESS, abi=router_abi)

MUSD_ADDRESS = "0x637e22A1EBbca50EA2d34027c238317fD10003eB"
ERC20_ABI = json.loads(
'''
[
  {"constant": false, "inputs": [{"name": "spender", "type": "address"}, {"name": "amount", "type": "uint256"}],
   "name": "approve", "outputs": [{"name": "", "type": "bool"}],
   "stateMutability": "nonpayable", "type": "function"},
  {"constant": true, "inputs": [{"name": "owner", "type": "address"}],
   "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}],
   "stateMutability": "view", "type": "function"}
]
'''
)

# =====================================
# Pretty Logging Helpers
# =====================================
def log_msg(msg):
    print(f"{msg}")

# =====================================
# Function: create_erc20_token
# =====================================
def create_erc20_token(token_name: str, token_symbol: str, initial_supply: float, seed_musd: float = SEED_MUSD, seed_percentage: float = DEFAULT_SEED_PERCENTAGE) -> str:
    supply_int = int(initial_supply)
    
    # 🚀 Deploy token
    log_msg("🚀 Deploying token...")
    token_contract = web3.eth.contract(abi=token_abi, bytecode=token_bytecode)
    nonce = web3.eth.get_transaction_count(sender_address)
    tx_deploy = token_contract.constructor(token_name, token_symbol, supply_int).build_transaction({
        "from": sender_address,
        "nonce": nonce,
        "gasPrice": web3.eth.gas_price,
        "gas": 3000000
    })
    signed_tx_deploy = web3.eth.account.sign_transaction(tx_deploy, PRIVATE_KEY)
    tx_hash_deploy = web3.eth.send_raw_transaction(signed_tx_deploy.raw_transaction)
    receipt_deploy = web3.eth.wait_for_transaction_receipt(tx_hash_deploy)
    if receipt_deploy.status != 1:
        return "❌ Token deployment failed."
    token_address = receipt_deploy.contractAddress
    log_msg(f"✅ Token deployed at: {token_address} (Tx: {tx_hash_deploy.hex()})")
    
    # 💵 Check mUSD balance
    musd_contract = web3.eth.contract(address=MUSD_ADDRESS, abi=ERC20_ABI)
    current_musd = musd_contract.functions.balanceOf(sender_address).call()
    if current_musd < 10 * (10**18):
        return "❌ Insufficient mUSD balance."
    log_msg("💵 mUSD balance OK.")
    
    # 🔢 Set liquidity amounts
    total_supply_wei = supply_int * (10**18)
    token_liquidity = int(total_supply_wei * (seed_percentage / 100))
    desired_musd = int(seed_musd * (10**18))
    log_msg("🔢 Liquidity amounts set.")
    
    # 🔄 Sort tokens (Uniswap V2 expects ascending order)
    if token_address.lower() < MUSD_ADDRESS.lower():
        tokenA, tokenB = token_address, MUSD_ADDRESS
        amountADesired, amountBDesired = token_liquidity, desired_musd
    else:
        tokenA, tokenB = MUSD_ADDRESS, token_address
        amountADesired, amountBDesired = desired_musd, token_liquidity
    amountAMin, amountBMin = 0, 0
    log_msg("🔄 Tokens sorted.")
    
    # ✅ Approve token and mUSD
    new_token = web3.eth.contract(address=token_address, abi=ERC20_ABI)
    nonce += 1
    tx_approve_token = new_token.functions.approve(DUMPY_ROUTER_ADDRESS, token_liquidity).build_transaction({
        "from": sender_address,
        "nonce": nonce,
        "gasPrice": web3.eth.gas_price,
        "gas": 100000
    })
    signed_tx_approve_token = web3.eth.account.sign_transaction(tx_approve_token, PRIVATE_KEY)
    tx_hash_approve_token = web3.eth.send_raw_transaction(signed_tx_approve_token.raw_transaction)
    receipt_approve_token = web3.eth.wait_for_transaction_receipt(tx_hash_approve_token)
    if receipt_approve_token.status != 1:
        return "❌ Token approval failed."
    log_msg(f"✅ Token approved (Tx: {tx_hash_approve_token.hex()})")
    
    nonce += 1
    tx_approve_musd = musd_contract.functions.approve(DUMPY_ROUTER_ADDRESS, desired_musd).build_transaction({
        "from": sender_address,
        "nonce": nonce,
        "gasPrice": web3.eth.gas_price,
        "gas": 100000
    })
    signed_tx_approve_musd = web3.eth.account.sign_transaction(tx_approve_musd, PRIVATE_KEY)
    tx_hash_approve_musd = web3.eth.send_raw_transaction(signed_tx_approve_musd.raw_transaction)
    receipt_approve_musd = web3.eth.wait_for_transaction_receipt(tx_hash_approve_musd)
    if receipt_approve_musd.status != 1:
        return "❌ mUSD approval failed."
    log_msg(f"✅ mUSD approved (Tx: {tx_hash_approve_musd.hex()})")
    
    # ⏳ Add liquidity
    log_msg("⏳ Adding liquidity...")
    nonce += 1
    deadline = int(time.time()) + 600
    tx_liquidity = router_contract.functions.addLiquidity(
        tokenA,
        tokenB,
        amountADesired,
        amountBDesired,
        amountAMin,
        amountBMin,
        sender_address,
        deadline
    ).build_transaction({
        "from": sender_address,
        "nonce": nonce,
        "gasPrice": web3.eth.gas_price,
        "gas": 8000000
    })
    signed_tx_liquidity = web3.eth.account.sign_transaction(tx_liquidity, PRIVATE_KEY)
    tx_hash_liquidity = web3.eth.send_raw_transaction(signed_tx_liquidity.raw_transaction)
    receipt_liquidity = web3.eth.wait_for_transaction_receipt(tx_hash_liquidity)
    if receipt_liquidity.status != 1:
        return "❌ Liquidity addition failed."
    log_msg(f"✅ Liquidity added! (Tx: {tx_hash_liquidity.hex()})")
    
    return f"✅ Token created at {token_address} and liquidity seeded! Liquidity TX Hash: {tx_hash_liquidity.hex()}"

if __name__ == "__main__":
    result = create_erc20_token("QQQ", "QQQ", 999)
    print(result)