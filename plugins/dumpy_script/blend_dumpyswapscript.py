import os
import json
import time
import requests
from dotenv import load_dotenv
from web3 import Web3

# -----------------------------------------------------------------------------
# Setup and Configuration
# -----------------------------------------------------------------------------
load_dotenv()

RPC_URL = "https://rpc.test.mezo.org"
web3 = Web3(Web3.HTTPProvider(RPC_URL))
if not web3.is_connected():
    raise ConnectionError("Failed to connect to the RPC URL.")

PRIVATE_KEY = os.getenv("PRIVATE_KEY")
if not PRIVATE_KEY:
    raise ValueError("PRIVATE_KEY not found in environment variables!")

account = web3.eth.account.from_key(PRIVATE_KEY)
sender_address = account.address
print(f"Using wallet: {sender_address}")

# Token and Router Addresses
MUSD_ADDRESS = "0x637e22A1EBbca50EA2d34027c238317fD10003eB"      # mUSD
WRAPPED_BTC_ADDRESS = "0xA460F83cdd9584E4bD6a9838abb0baC58EAde999" # wtBTC
DUMPY_ROUTER_ADDRESS = "0xe3eB6Aa5CFB0BdA17C22128A58830EBC8Ecb74C3"  # Dumpy's router

# SmartRouter details
SMART_ROUTER_ADDRESS = "0xf7458e9De34a2B34B48866336F48123F6dE4d303"
with open("plugins/dumpy_script/smart_router_abi.json", "r") as sr_abi_file:
    smart_router_abi = json.load(sr_abi_file)
smart_router_contract = web3.eth.contract(address=SMART_ROUTER_ADDRESS, abi=smart_router_abi)

with open("plugins/dumpy_script/new_router_abi.json", "r") as abi_file:
    dumpy_router_abi = json.load(abi_file)
dumpy_router_contract = web3.eth.contract(address=DUMPY_ROUTER_ADDRESS, abi=dumpy_router_abi)

# -----------------------------------------------------------------------------
# ERC‑20 Minimal ABI (with transfer, balanceOf, approve, allowance, decimals)
# -----------------------------------------------------------------------------
ERC20_ABI = json.loads(
    '''
    [
      {
        "constant": false,
        "inputs": [
          {"name": "spender", "type": "address"},
          {"name": "amount", "type": "uint256"}
        ],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "nonpayable",
        "type": "function"
      },
      {
        "constant": true,
        "inputs": [{"name": "owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
      },
      {
        "constant": true,
        "inputs": [
          {"name": "owner", "type": "address"},
          {"name": "spender", "type": "address"}
        ],
        "name": "allowance",
        "outputs": [{"name": "remaining", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
      },
      {
        "constant": false,
        "inputs": [
          {"name": "to", "type": "address"},
          {"name": "amount", "type": "uint256"}
        ],
        "name": "transfer",
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "nonpayable",
        "type": "function"
      },
      {
        "constant": true,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "stateMutability": "view",
        "type": "function"
      }
    ]
    '''
)

# For Wrapped BTC, include withdraw to unwrap to native BTC.
WBTC_EXTRA_ABI = json.loads(
    '''
    [
      {
        "constant": false,
        "inputs": [{"name": "wad", "type": "uint256"}],
        "name": "withdraw",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
      }
    ]
    '''
)
WBTC_ABI = ERC20_ABI + WBTC_EXTRA_ABI

# -----------------------------------------------------------------------------
# Graph Endpoint Functions
# -----------------------------------------------------------------------------
GRAPH_URL = "https://api.goldsky.com/api/public/project_cm48lsrzo0axx01tna6rb1ee9/subgraphs/exchange-v2-mezo/1.0.0/gn"

def query_graph(query: str) -> dict:
    response = requests.post(GRAPH_URL, json={"query": query})
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"GraphQL query failed with status code {response.status_code}")

def direct_pair_exists(token_in: str, token_out: str) -> bool:
    token_in = token_in.lower()
    token_out = token_out.lower()
    query = f'''
    {{
      pairs(where: {{ token0: "{token_in}", token1: "{token_out}" }}) {{
        id
      }}
    }}
    '''
    data = query_graph(query)
    pairs = data.get("data", {}).get("pairs", [])
    if pairs:
        return True
    query = f'''
    {{
      pairs(where: {{ token0: "{token_out}", token1: "{token_in}" }}) {{
        id
      }}
    }}
    '''
    data = query_graph(query)
    pairs = data.get("data", {}).get("pairs", [])
    return bool(pairs)

def find_swap_path(token_in: str, token_out: str) -> list:
    if direct_pair_exists(token_in, token_out):
        return [token_in, token_out]
    intermediaries = [MUSD_ADDRESS, WRAPPED_BTC_ADDRESS]
    for intermediary in intermediaries:
        if direct_pair_exists(token_in, intermediary) and direct_pair_exists(intermediary, token_out):
            return [token_in, intermediary, token_out]
    raise Exception(f"No direct Dumpy route found between tokens {token_in} and {token_out}")

# -----------------------------------------------------------------------------
# Token Discovery by Symbol (Case‑Insensitive)
# -----------------------------------------------------------------------------
def get_token_address_by_symbol(symbol: str) -> str:
    if symbol.lower() == "btc":
        symbol = "wtbtc"
    query_all = '''
    {
      tokens(first: 100) {
        id
        symbol
      }
    }
    '''
    data = query_graph(query_all)
    tokens = data.get("data", {}).get("tokens", [])
    matching_tokens = [t for t in tokens if t["symbol"].lower() == symbol.lower()]
    if matching_tokens:
        token_address = matching_tokens[0]["id"]
        checksum_address = web3.to_checksum_address(token_address)
        print(f"Found token {matching_tokens[0]['symbol']} with id: {checksum_address}")
        return checksum_address
    else:
        available_symbols = [t["symbol"] for t in tokens]
        raise Exception(f"Token with symbol '{symbol}' not found. Available: {', '.join(available_symbols)}")

# -----------------------------------------------------------------------------
# New Helper: Get Token Address from Symbol or Contract Address
# -----------------------------------------------------------------------------
def get_token_address(identifier: str) -> str:
    # If the identifier is a valid address, return it in checksum format.
    if identifier.startswith("0x") and len(identifier) == 42 and web3.is_address(identifier):
        return web3.to_checksum_address(identifier)
    # Otherwise, lookup by symbol.
    return get_token_address_by_symbol(identifier)

# -----------------------------------------------------------------------------
# New Function: List All Tokens from the Subgraph
# -----------------------------------------------------------------------------
def list_all_tokens() -> list:
    query_all = '''
    {
      tokens(first: 100) {
        id
        symbol
      }
    }
    '''
    data = query_graph(query_all)
    tokens = data.get("data", {}).get("tokens", [])
    if tokens:
        symbols = sorted(list(set(t["symbol"] for t in tokens)))
        return symbols
    else:
        return []

def list_swap_capabilities() -> str:
    tokens = list_all_tokens()
    if tokens:
        return "Available tokens on Dumpy are: " + ", ".join(tokens)
    else:
        return "No tokens found on Dumpy."

# -----------------------------------------------------------------------------
# Helper Function for Approval (Zero‑Then‑Approve Pattern)
# -----------------------------------------------------------------------------
def approve_if_needed(token_contract, amount_wei):
    current_allowance = token_contract.functions.allowance(sender_address, DUMPY_ROUTER_ADDRESS).call()
    if current_allowance < amount_wei:
        if current_allowance != 0:
            print(f"Current allowance is nonzero ({current_allowance}). Resetting to 0 first...")
            nonce = web3.eth.get_transaction_count(sender_address)
            gas_price = web3.eth.gas_price
            reset_tx = token_contract.functions.approve(DUMPY_ROUTER_ADDRESS, 0).build_transaction({
                "from": sender_address,
                "nonce": nonce,
                "gas": 100000,
                "gasPrice": gas_price,
            })
            signed_reset_tx = web3.eth.account.sign_transaction(reset_tx, PRIVATE_KEY)
            reset_tx_hash = web3.eth.send_raw_transaction(signed_reset_tx.raw_transaction)
            reset_receipt = web3.eth.wait_for_transaction_receipt(reset_tx_hash)
            if reset_receipt.status != 1:
                raise Exception("Approval reset transaction failed.")
            print("Approval reset successful.")
        nonce = web3.eth.get_transaction_count(sender_address)
        gas_price = web3.eth.gas_price
        approve_tx = token_contract.functions.approve(DUMPY_ROUTER_ADDRESS, amount_wei).build_transaction({
            "from": sender_address,
            "nonce": nonce,
            "gas": 100000,
            "gasPrice": gas_price,
        })
        signed_tx = web3.eth.account.sign_transaction(approve_tx, PRIVATE_KEY)
        tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
        if receipt.status != 1:
            raise Exception("Approval transaction failed.")
        print(f"Approval successful. TX Hash: {tx_hash.hex()}")
    else:
        print("Sufficient allowance already set.")

# -----------------------------------------------------------------------------
# New Function: Unwrap Wrapped BTC (to native BTC)
# -----------------------------------------------------------------------------
def unwrap_btc(amount_wei: int) -> float:
    wtbtc_contract = web3.eth.contract(address=WRAPPED_BTC_ADDRESS, abi=WBTC_ABI)
    nonce = web3.eth.get_transaction_count(sender_address)
    gas_price = web3.eth.gas_price
    tx = wtbtc_contract.functions.withdraw(amount_wei).build_transaction({
         "from": sender_address,
         "nonce": nonce,
         "gasPrice": gas_price,
    })
    signed_tx = web3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
    receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
    if receipt.status == 1:
         print(f"Unwrap successful. TX Hash: {tx_hash.hex()}")
         return amount_wei / 10**18
    else:
         raise Exception("Unwrap transaction failed")

# -----------------------------------------------------------------------------
# New Function: Get Token Price using Subgraph Data
# -----------------------------------------------------------------------------
def get_token_price(token_symbol: str) -> str:
    if token_symbol.lower() == "btc":
        token_symbol = "wtbtc"
    try:
        token_address = get_token_address_by_symbol(token_symbol)
    except Exception as e:
        return f"Token lookup error: {e}"
    token_id = token_address.lower()
    query = f'''
    {{
      token(id: "{token_id}") {{
        id
        decimals
        derivedUSD
        derivedETH
      }}
    }}
    '''
    try:
        result = query_graph(query)
        token_data = result["data"]["token"]
        if token_data is None:
            return f"Price data for token {token_symbol.upper()} not found."
        derivedUSD = token_data.get("derivedUSD", "N/A")
        derivedETH = token_data.get("derivedETH", "N/A")
        return f"Price of {token_symbol.upper()}: {derivedUSD} USD, {derivedETH} BTC."
    except Exception as e:
        return f"Failed to get price data: {e}"

# -----------------------------------------------------------------------------
# Swap via Dumpy's Router with SmartRouter Fallback (with output simulation)
# -----------------------------------------------------------------------------
def swap_tokens_by_symbol(from_symbol: str, to_symbol: str, amount: float, min_amount_out: float = 0.000000000000001):
    unwrap_output = False
    # If the output token is BTC (or symbol) then set unwrap flag and map to wrapped BTC.
    if to_symbol.lower() == "btc":
        unwrap_output = True
        to_symbol = "wtbtc"
    
    try:
        token_in_address = get_token_address(from_symbol)
        token_out_address = get_token_address(to_symbol)
    except Exception as e:
        return f"Token lookup error: {e}"
    
    # Get decimals for token in and token out. Default to 18 if not available.
    try:
        token_in_contract = web3.eth.contract(address=token_in_address, abi=ERC20_ABI)
        token_in_decimals = token_in_contract.functions.decimals().call()
    except Exception:
        token_in_decimals = 18
    try:
        token_out_contract = web3.eth.contract(address=token_out_address, abi=ERC20_ABI)
        token_out_decimals = token_out_contract.functions.decimals().call()
    except Exception:
        token_out_decimals = 18

    amount_wei = int(amount * 10**token_in_decimals)
    min_amount_out_wei = int(min_amount_out * 10**token_out_decimals)
    deadline = int(time.time()) + 600

    approve_if_needed(token_in_contract, amount_wei)
    
    try:
        path = find_swap_path(token_in_address, token_out_address)
        print(f"Using Dumpy swap path: {path}")
        nonce = web3.eth.get_transaction_count(sender_address)
        gas_price = web3.eth.gas_price
        
        simulated_output = dumpy_router_contract.functions.swapExactTokensForTokens(
            amount_wei,
            min_amount_out_wei,
            path,
            sender_address,
            deadline
        ).call({"from": sender_address})
        if isinstance(simulated_output, list):
            out_amount_wei = simulated_output[-1]
        else:
            out_amount_wei = simulated_output
        swap_tx = dumpy_router_contract.functions.swapExactTokensForTokens(
            amount_wei,
            min_amount_out_wei,
            path,
            sender_address,
            deadline
        ).build_transaction({
            "from": sender_address,
            "nonce": nonce,
            "gasPrice": gas_price,
        })
        try:
            estimated_gas = web3.eth.estimate_gas(swap_tx)
            swap_tx["gas"] = estimated_gas + 10000
            print(f"Estimated gas: {estimated_gas}, using gas limit: {swap_tx['gas']}")
        except Exception as e:
            print(f"Gas estimation failed: {e}. Using default gas limit of 250000.")
            swap_tx["gas"] = 250000
        signed_swap_tx = web3.eth.account.sign_transaction(swap_tx, PRIVATE_KEY)
        tx_hash = web3.eth.send_raw_transaction(signed_swap_tx.raw_transaction)
        print(f"Dumpy swap transaction sent. TX Hash: {tx_hash.hex()}")
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
        print("Dumpy swap transaction receipt:")
        print(f"  Transaction Hash: {receipt.transactionHash.hex()}")
        print(f"  Gas Used: {receipt.gasUsed}")
        print(f"  Status: {'Success' if receipt.status == 1 else 'Failed'}")
        out_amount = out_amount_wei / (10**token_out_decimals)
        
        if unwrap_output:
            try:
                unwrapped_amount = unwrap_btc(out_amount_wei)
                final_token = "BTC"
                out_amount = unwrapped_amount
            except Exception as e:
                return f"Swap succeeded, but unwrapping failed: {e}"
        else:
            final_token = to_symbol.upper()
            
        return f"✅ Swap successful via Dumpy! {amount} {from_symbol.upper()} swapped for {out_amount:.8f} {final_token}. TX Hash: {tx_hash.hex()}"
    except Exception as dumpy_error:
        print(f"Dumpy router route failed: {dumpy_error}")
        print("Falling back to SmartRouter...")
        try:
            nonce = web3.eth.get_transaction_count(sender_address)
            gas_price = web3.eth.gas_price
            smart_swap_tx = smart_router_contract.functions.swapExactTokensForTokensExternal(
                amount_wei,
                min_amount_out_wei,
                [],
                token_in_address,
                token_out_address,
                sender_address
            ).build_transaction({
                "from": sender_address,
                "nonce": nonce,
                "gasPrice": gas_price,
            })
            try:
                estimated_gas = web3.eth.estimate_gas(smart_swap_tx)
                smart_swap_tx["gas"] = estimated_gas + 10000
                print(f"SmartRouter estimated gas: {estimated_gas}, using gas limit: {smart_swap_tx['gas']}")
            except Exception as e:
                print(f"SmartRouter gas estimation failed: {e}. Using default gas limit of 250000.")
                smart_swap_tx["gas"] = 250000
            simulated_output = smart_router_contract.functions.swapExactTokensForTokensExternal(
                amount_wei,
                min_amount_out_wei,
                [],
                token_in_address,
                token_out_address,
                sender_address
            ).call({"from": sender_address})
            if isinstance(simulated_output, list):
                out_amount_wei = simulated_output[-1]
            else:
                out_amount_wei = simulated_output
            out_amount = out_amount_wei / (10**token_out_decimals)
            signed_smart_swap_tx = web3.eth.account.sign_transaction(smart_swap_tx, PRIVATE_KEY)
            tx_hash = web3.eth.send_raw_transaction(signed_smart_swap_tx.raw_transaction)
            print(f"SmartRouter swap transaction sent. TX Hash: {tx_hash.hex()}")
            receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
            print("SmartRouter swap transaction receipt:")
            print(f"  Transaction Hash: {receipt.transactionHash.hex()}")
            print(f"  Gas Used: {receipt.gasUsed}")
            print(f"  Status: {'Success' if receipt.status == 1 else 'Failed'}")
            if unwrap_output:
                try:
                    unwrapped_amount = unwrap_btc(out_amount_wei)
                    final_token = "BTC"
                    out_amount = unwrapped_amount
                except Exception as e:
                    return f"Swap succeeded via SmartRouter, but unwrapping failed: {e}"
            else:
                final_token = to_symbol.upper()
            return f"✅ Swap successful via SmartRouter! {amount} {from_symbol.upper()} swapped for {out_amount:.8f} {final_token}. TX Hash: {tx_hash.hex()}"
        except Exception as smart_error:
            return f"❌ Both Dumpy and SmartRouter swap attempts failed: {smart_error}"

# -----------------------------------------------------------------------------
# New Function: Generic Token Transfer
# -----------------------------------------------------------------------------
def transfer_token(token_symbol: str, recipient: str, amount: float) -> str:
    if token_symbol.lower() == "btc":
        amount_wei = int(amount * 10**18)
        nonce = web3.eth.get_transaction_count(sender_address)
        gas_price = web3.eth.gas_price
        chain_id = web3.eth.chain_id
        tx = {
            "to": recipient,
            "value": amount_wei,
            "gas": 21000,
            "gasPrice": gas_price,
            "nonce": nonce,
            "chainId": chain_id
        }
        try:
            signed_tx = web3.eth.account.sign_transaction(tx, PRIVATE_KEY)
            tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
            receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
            return f"✅ Transfer successful! {amount} BTC transferred to {recipient}. TX Hash: {tx_hash.hex()}"
        except Exception as e:
            return f"❌ Transfer failed: {e}"
    else:
        try:
            token_address = get_token_address(token_symbol)
        except Exception as e:
            return f"Token lookup error: {e}"
        amount_wei = int(amount * 10**18)
        token_contract = web3.eth.contract(address=token_address, abi=ERC20_ABI)
        nonce = web3.eth.get_transaction_count(sender_address)
        gas_price = web3.eth.gas_price
        transfer_tx = token_contract.functions.transfer(recipient, amount_wei).build_transaction({
            "from": sender_address,
            "nonce": nonce,
            "gasPrice": gas_price,
        })
        try:
            estimated_gas = web3.eth.estimate_gas(transfer_tx)
            transfer_tx["gas"] = estimated_gas + 10000
        except Exception as e:
            transfer_tx["gas"] = 250000
        try:
            signed_transfer_tx = web3.eth.account.sign_transaction(transfer_tx, PRIVATE_KEY)
            tx_hash = web3.eth.send_raw_transaction(signed_transfer_tx.raw_transaction)
            receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
            return f"✅ Transfer successful! {amount} {token_symbol.upper()} transferred to {recipient}. TX Hash: {tx_hash.hex()}"
        except Exception as e:
            return f"❌ Transfer failed: {e}"

# -----------------------------------------------------------------------------
# New Function: Get Wallet Token Balance
# -----------------------------------------------------------------------------
def get_token_balance(token_symbol: str) -> str:
    if token_symbol.lower() == "btc":
        try:
            balance_wei = web3.eth.get_balance(sender_address)
            balance = balance_wei / 10**18
            return f"Your balance of BTC is {balance}"
        except Exception as e:
            return f"Failed to get native BTC balance: {e}"
    else:
        try:
            token_address = get_token_address(token_symbol)
        except Exception as e:
            return f"Token lookup error: {e}"
        token_contract = web3.eth.contract(address=token_address, abi=ERC20_ABI)
        try:
            balance_wei = token_contract.functions.balanceOf(sender_address).call()
            balance = balance_wei / 10**18
            return f"Your balance of {token_symbol.upper()} is {balance}"
        except Exception as e:
            return f"Failed to get balance: {e}"

# -----------------------------------------------------------------------------
# New Function: Remove Liquidity
# -----------------------------------------------------------------------------
def remove_liquidity(token_symbol: str, pair_token: str) -> str:
    try:
        tokenA_address = get_token_address(token_symbol)
        tokenB_address = get_token_address(pair_token)
    except Exception as e:
        return f"Token lookup error: {e}"
    
    # Use the router's factory to get the pair address
    try:
        factory_address = dumpy_router_contract.functions.factory().call()
        UNISWAP_FACTORY_ABI = json.loads(
            '''
            [
              {
                "constant": true,
                "inputs": [
                  {"internalType": "address", "name": "tokenA", "type": "address"},
                  {"internalType": "address", "name": "tokenB", "type": "address"}
                ],
                "name": "getPair",
                "outputs": [{"internalType": "address", "name": "pair", "type": "address"}],
                "payable": false,
                "stateMutability": "view",
                "type": "function"
              }
            ]
            '''
        )
        factory_contract = web3.eth.contract(address=factory_address, abi=UNISWAP_FACTORY_ABI)
        pair_address = factory_contract.functions.getPair(tokenA_address, tokenB_address).call()
    except Exception as e:
        return f"Failed to get liquidity pool pair: {e}"
    
    if not pair_address or int(pair_address, 16) == 0:
        return f"No liquidity pool found for {token_symbol}-{pair_token}."
    
    lp_token_contract = web3.eth.contract(address=pair_address, abi=ERC20_ABI)
    liquidity_balance = lp_token_contract.functions.balanceOf(sender_address).call()
    if liquidity_balance == 0:
        return f"No liquidity to remove for pool {token_symbol}-{pair_token}."
    
    approve_if_needed(lp_token_contract, liquidity_balance)
    
    deadline = int(time.time()) + 600
    nonce = web3.eth.get_transaction_count(sender_address)
    gas_price = web3.eth.gas_price
    
    tx = dumpy_router_contract.functions.removeLiquidity(
         tokenA_address,
         tokenB_address,
         liquidity_balance,
         0,  # amountAMin
         0,  # amountBMin
         sender_address,
         deadline
    ).build_transaction({
         "from": sender_address,
         "nonce": nonce,
         "gasPrice": gas_price,
    })
    
    signed_tx = web3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
    receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
    
    if receipt.status == 1:
         return f"✅ Removed all liquidity for pool {token_symbol}-{pair_token}. TX Hash: {tx_hash.hex()}"
    else:
         return "❌ Liquidity removal failed."

# -----------------------------------------------------------------------------
# New Function: Add Liquidity
# -----------------------------------------------------------------------------
def add_liquidity(token_symbol: str, pair_token: str, amount: float) -> str:
    try:
        tokenA_address = get_token_address(token_symbol)
        tokenB_address = get_token_address(pair_token)
    except Exception as e:
        return f"Token lookup error: {e}"
    
    amount_wei = int(amount * 10**18)
    
    tokenA_contract = web3.eth.contract(address=tokenA_address, abi=ERC20_ABI)
    tokenB_contract = web3.eth.contract(address=tokenB_address, abi=ERC20_ABI)
    approve_if_needed(tokenA_contract, amount_wei)
    approve_if_needed(tokenB_contract, amount_wei)
    
    # Try to get pair reserves from the pair contract via the factory.
    try:
        factory_address = dumpy_router_contract.functions.factory().call()
        UNISWAP_FACTORY_ABI = json.loads(
            '''
            [
              {
                "constant": true,
                "inputs": [
                  {"internalType": "address", "name": "tokenA", "type": "address"},
                  {"internalType": "address", "name": "tokenB", "type": "address"}
                ],
                "name": "getPair",
                "outputs": [{"internalType": "address", "name": "pair", "type": "address"}],
                "payable": false,
                "stateMutability": "view",
                "type": "function"
              }
            ]
            '''
        )
        factory_contract = web3.eth.contract(address=factory_address, abi=UNISWAP_FACTORY_ABI)
        pair_address = factory_contract.functions.getPair(tokenA_address, tokenB_address).call()
    except Exception as e:
        pair_address = None

    if pair_address and int(pair_address, 16) != 0:
        # Use minimal pair ABI to get reserves and token order.
        PAIR_ABI = json.loads(
            '''
            [
              {
                "constant": true,
                "inputs": [],
                "name": "getReserves",
                "outputs": [
                  {"internalType": "uint112", "name": "reserve0", "type": "uint112"},
                  {"internalType": "uint112", "name": "reserve1", "type": "uint112"},
                  {"internalType": "uint32", "name": "blockTimestampLast", "type": "uint32"}
                ],
                "stateMutability": "view",
                "type": "function"
              },
              {
                "constant": true,
                "inputs": [],
                "name": "token0",
                "outputs": [{"internalType": "address", "name": "", "type": "address"}],
                "stateMutability": "view",
                "type": "function"
              },
              {
                "constant": true,
                "inputs": [],
                "name": "token1",
                "outputs": [{"internalType": "address", "name": "", "type": "address"}],
                "stateMutability": "view",
                "type": "function"
              }
            ]
            '''
        )
        pair_contract = web3.eth.contract(address=pair_address, abi=PAIR_ABI)
        reserves = pair_contract.functions.getReserves().call()
        token0 = pair_contract.functions.token0().call()
        token1 = pair_contract.functions.token1().call()
        if tokenA_address.lower() == token0.lower():
            reserveA = reserves[0]
            reserveB = reserves[1]
        else:
            reserveA = reserves[1]
            reserveB = reserves[0]
        # If reserves are zero, fallback to 1:1 ratio.
        if reserveA == 0 or reserveB == 0:
            amountB_wei = amount_wei
        else:
            amountB_wei = int((amount_wei * reserveB) / reserveA)
    else:
        # If no pair exists, use 1:1 ratio.
        amountB_wei = amount_wei
    
    deadline = int(time.time()) + 600
    nonce = web3.eth.get_transaction_count(sender_address)
    gas_price = web3.eth.gas_price
    
    tx = dumpy_router_contract.functions.addLiquidity(
        tokenA_address,
        tokenB_address,
        amount_wei,
        amountB_wei,
        0,  # amountAMin
        0,  # amountBMin
        sender_address,
        deadline
    ).build_transaction({
        "from": sender_address,
        "nonce": nonce,
        "gasPrice": gas_price,
    })
    
    signed_tx = web3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
    receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
    
    if receipt.status == 1:
        return f"✅ Added liquidity: {amount} {token_symbol} and {amountB_wei/10**18:.8f} {pair_token}. TX Hash: {tx_hash.hex()}"
    else:
        return "❌ Liquidity addition failed."

# -----------------------------------------------------------------------------
# Example Usage (Command‑Line)
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    # For testing: try swapping 100 of a token (symbol or contract address) for DAI.
    # Example: swap_tokens_by_symbol("0xF08085Ed33C0619113Ee706fdB4b1b2c96137bEE", "DAI", 100)
    result = swap_tokens_by_symbol(from_symbol="0xF08085Ed33C0619113Ee706fdB4b1b2c96137bEE", to_symbol="DAI", amount=100)
    print(result)
    # Uncomment to test transfers, balance queries, liquidity functions, and price checks:
    # print(transfer_token("BTC", "0xF0Ee42AA7A347A2D1e9DBDF5cfc42B66843aB33D", 0.0000001))
    # print(get_token_balance("BTC"))
    # print(get_token_price("MUSD"))
    # print(add_liquidity("MUSD", "wtBTC", 10))
    # print(remove_liquidity("MUSD", "wtBTC"))