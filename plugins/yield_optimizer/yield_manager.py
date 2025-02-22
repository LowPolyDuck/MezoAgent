import os
import random
import requests
from dotenv import load_dotenv
from web3 import Web3

# --- Helper: pad value to 32 bytes ---
def to_32byte_hex(val):
    """
    For integers: returns hex string (without 0x) padded to 64 characters.
    For strings (addresses): strips '0x' and pads to 64 characters.
    """
    if isinstance(val, int):
        return hex(val)[2:].lower().rjust(64, "0")
    elif isinstance(val, str):
        if val.startswith("0x"):
            val = val[2:]
        return val.lower().rjust(64, "0")
    else:
        raise TypeError("Unsupported type for padding")

# ------------------------------
# Common Setup
# ------------------------------
load_dotenv()
RPC_URL = os.getenv("RPC_URL", "https://rpc.test.mezo.org")
web3 = Web3(Web3.HTTPProvider(RPC_URL))
if not web3.is_connected():
    raise Exception("❌ Failed to connect to RPC URL.")

PRIVATE_KEY = os.getenv("PRIVATE_KEY")
if not PRIVATE_KEY:
    raise Exception("❌ PRIVATE_KEY not found in environment variables!")
account = web3.eth.account.from_key(PRIVATE_KEY)
sender_address = account.address
print(f"🚀 Using wallet: {sender_address}")

# ------------------------------
# Subgraph Query Setup
# ------------------------------
SUBGRAPH_URL = "https://api.goldsky.com/api/public/project_cm040smxin6ju01x481kh0o8l/subgraphs/blend-mezotest/1.0.1/gn"
user_address_lower = sender_address.lower()
query = f"""
query MyAssets {{
  reserves {{
    id
    name
    symbol
    liquidityRate
  }}
  userReserves(where: {{user: "{user_address_lower}"}}) {{
    id
    currentBTokenBalance
    currentTotalDebt
    usageAsCollateralEnabledOnUser
    pool {{
      id
    }}
    reserve {{
      id
      symbol
      name
      liquidityRate
      price {{
        priceInEth
      }}
      bToken {{
        id
        underlyingAssetAddress
      }}
    }}
  }}
}}
"""

def blend_query_subgraph():
    """Query the Blend subgraph and return the JSON data."""
    print("\n🔍 Querying Blend subgraph...")
    response = requests.post(SUBGRAPH_URL, json={'query': query})
    if response.status_code != 200:
        raise Exception("Failed to query subgraph")
    data = response.json()["data"]
    return data

# ------------------------------
# Define Target Addresses
# ------------------------------
BTC_DEPOSIT_TARGET = os.getenv("POOL_CONTRACT_ADDRESS", "0x9Fbc2fDFBC6B5bbca9895e28E55eb8Cc77C9cF9c")
BTC_DEPOSIT_TARGET = Web3.to_checksum_address(BTC_DEPOSIT_TARGET)
ERC20_DEPOSIT_TARGET = "0x9c55214751472788a06797d88f38af1e79eee018"
ERC20_DEPOSIT_TARGET = Web3.to_checksum_address(ERC20_DEPOSIT_TARGET)
BTC_WITHDRAW_ASSET = "0x5eaa741552d6af40c7bf46467eaf79eea08eea9f"
BTC_WITHDRAW_ASSET = Web3.to_checksum_address(BTC_WITHDRAW_ASSET)
COLLATERAL_TARGET = "0x7683b5ce24d4e8c73d58cfdb6dfaa9544bee7085"
COLLATERAL_TARGET = Web3.to_checksum_address(COLLATERAL_TARGET)

# ------------------------------
# Deposit Function
# ------------------------------
def blend_deposit(asset_input, deposit_str):
    """Deposit into Blend given an asset (e.g. 'usdc' or 'btc') and an amount string."""
    nonce = web3.eth.get_transaction_count(sender_address)
    if asset_input == "btc":
        try:
            deposit_amount_btc = float(deposit_str)
        except ValueError:
            raise Exception("For BTC, deposit must be a number (e.g., 0.1 for 0.1 BTC).")
        deposit_value = int(deposit_amount_btc * (10 ** 18))
        function_selector = "0x474cf53d"
        data_payload = function_selector + ("0" * 64) + to_32byte_hex(sender_address) + ("0" * 64)
        print("\nUsing BTC deposit style.")
        tx = {
            "to": BTC_DEPOSIT_TARGET,
            "value": deposit_value,
            "data": data_payload,
            "gas": int(os.getenv("GAS_LIMIT", "300000")),
            "gasPrice": web3.eth.gas_price,
            "nonce": nonce,
            "chainId": web3.eth.chain_id,
        }
        print("\nTX details (BTC deposit):", tx)
        signed_tx = web3.eth.account.sign_transaction(tx, PRIVATE_KEY)
        tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
        return f"🚀 BTC Deposit tx sent! Tx hash: {web3.to_hex(tx_hash)}"
    else:
        # ERC20 deposit: Build asset mapping using the subgraph.
        data = blend_query_subgraph()
        reserves = data.get("reserves", [])
        user_reserves = data.get("userReserves", [])
        asset_mapping = {r["symbol"].strip().lower(): r["id"][:42] for r in reserves}
        if asset_input not in asset_mapping:
            raise Exception(f"Asset '{asset_input}' not supported. Supported assets: {list(asset_mapping.keys())}")
        token_address = Web3.to_checksum_address(asset_mapping[asset_input])
        erc20_abi = [
            {
                "constant": True,
                "inputs": [],
                "name": "decimals",
                "outputs": [{"name": "", "type": "uint8"}],
                "type": "function"
            },
            {
                "constant": True,
                "inputs": [
                    {"name": "_owner", "type": "address"},
                    {"name": "_spender", "type": "address"}
                ],
                "name": "allowance",
                "outputs": [{"name": "", "type": "uint256"}],
                "type": "function"
            },
            {
                "constant": False,
                "inputs": [
                    {"name": "_spender", "type": "address"},
                    {"name": "_value", "type": "uint256"}
                ],
                "name": "approve",
                "outputs": [{"name": "", "type": "bool"}],
                "type": "function"
            }
        ]
        token_contract = web3.eth.contract(address=token_address, abi=erc20_abi)
        decimals = token_contract.functions.decimals().call()
        print(f"\nAsset {asset_input.upper()} has {decimals} decimals.")
        try:
            deposit_amount_tokens = float(deposit_str)
        except ValueError:
            raise Exception("Deposit amount must be a number for ERC20 assets.")
        deposit_value = int(deposit_amount_tokens * (10 ** decimals))
        print(f"Depositing {deposit_amount_tokens} {asset_input.upper()} => {deposit_value} in smallest unit.")

        current_allowance = token_contract.functions.allowance(sender_address, ERC20_DEPOSIT_TARGET).call()
        if current_allowance < deposit_value:
            print(f"\nAllowance ({current_allowance}) is less than deposit value ({deposit_value}). Approving...")
            approve_tx = token_contract.functions.approve(ERC20_DEPOSIT_TARGET, deposit_value).build_transaction({
                "from": sender_address,
                "nonce": nonce,
                "gasPrice": web3.eth.gas_price,
                "chainId": web3.eth.chain_id,
                "gas": int(os.getenv("APPROVE_GAS_LIMIT", "100000")),
            })
            signed_approve_tx = web3.eth.account.sign_transaction(approve_tx, PRIVATE_KEY)
            approve_tx_hash = web3.eth.send_raw_transaction(signed_approve_tx.raw_transaction)
            print(f"Approval tx sent! Tx hash: {web3.to_hex(approve_tx_hash)}")
            web3.eth.wait_for_transaction_receipt(approve_tx_hash)
            print("Approval confirmed.")
            nonce += 1
        else:
            print("Sufficient allowance present.")

        # Check if collateral is already enabled for this asset
        collateral_already_enabled = False
        for reserve in user_reserves:
            if reserve["reserve"]["symbol"].strip().lower() == asset_input:
                collateral_already_enabled = reserve.get("usageAsCollateralEnabledOnUser", False)
                break

        if collateral_already_enabled:
            print("Collateral already enabled for this asset. Skipping collateral tx.")
        else:
            # Enable asset as collateral BEFORE deposit.
            collateral_fn_sig = "setUserUseReserveAsCollateral(address,bool)"
            collateral_selector = web3.keccak(text=collateral_fn_sig)[:4].hex()
            param1_coll = "000000000000000000000000" + token_address[2:]
            param2_coll = to_32byte_hex(1)
            collateral_data = collateral_selector + param1_coll + param2_coll
            print("Raw collateral data payload:", collateral_data)
            tx_collateral = {
                "to": COLLATERAL_TARGET,
                "value": 0,
                "data": collateral_data,
                "gas": int(os.getenv("COLLATERAL_GAS_LIMIT", "200000")),
                "gasPrice": web3.eth.gas_price,
                "nonce": nonce,
                "chainId": web3.eth.chain_id,
            }
            print("\n📨 Sending collateral enabling tx:", tx_collateral)
            signed_tx_collateral = web3.eth.account.sign_transaction(tx_collateral, PRIVATE_KEY)
            collateral_tx_hash = web3.eth.send_raw_transaction(signed_tx_collateral.raw_transaction)
            print(f"\n🚀 Collateral tx sent! Tx hash: {web3.to_hex(collateral_tx_hash)}")
            web3.eth.wait_for_transaction_receipt(collateral_tx_hash)
            print("Collateral enabling confirmed.")
            nonce += 1

        # Build ERC20 deposit raw transaction using the working USDC blueprint.
        function_selector = "0x617ba037"
        param1 = "000000000000000000000000" + token_address[2:]
        param2 = to_32byte_hex(deposit_value)
        param3 = "000000000000000000000000" + sender_address[2:]
        param4 = "0" * 64
        data_payload = function_selector + param1 + param2 + param3 + param4
        print("\nUsing ERC20 deposit style. Data payload:", data_payload)
        tx = {
            "to": ERC20_DEPOSIT_TARGET,
            "value": 0,
            "data": data_payload,
            "gas": int(os.getenv("GAS_LIMIT", "300000")),
            "gasPrice": web3.eth.gas_price,
            "nonce": nonce,
            "chainId": web3.eth.chain_id,
        }
        print("\nTX details (ERC20 deposit):", tx)
        signed_tx = web3.eth.account.sign_transaction(tx, PRIVATE_KEY)
        tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
        return f"🚀 ERC20 Deposit tx sent! Tx hash: {web3.to_hex(tx_hash)}"

# ------------------------------
# Withdrawal Function
# ------------------------------
def blend_withdraw(asset_input, withdraw_str):
    """Withdraw from Blend given an asset (e.g. 'usdc' or 'btc') and an amount string."""
    nonce = web3.eth.get_transaction_count(sender_address)
    WITHDRAW_TARGET = "0x9c55214751472788a06797d88f38af1e79eee018"
    WITHDRAW_TARGET = Web3.to_checksum_address(WITHDRAW_TARGET)
    if asset_input == "btc":
        try:
            btc_amount = float(withdraw_str)
        except ValueError:
            raise Exception("For BTC, withdrawal amount must be a number (e.g., 0.0000001).")
        withdraw_value = int(btc_amount * (10 ** 18))
        asset_address = BTC_WITHDRAW_ASSET
        print("\nUsing BTC withdrawal style.")
    else:
        data = blend_query_subgraph()
        reserves = data.get("reserves", [])
        asset_mapping = {r["symbol"].strip().lower(): r["id"][:42] for r in reserves}
        if asset_input not in asset_mapping:
            raise Exception(f"Asset '{asset_input}' not supported. Supported assets: {list(asset_mapping.keys())}")
        asset_address = Web3.to_checksum_address(asset_mapping[asset_input])
        erc20_abi_dec = [{
            "constant": True,
            "inputs": [],
            "name": "decimals",
            "outputs": [{"name": "", "type": "uint8"}],
            "type": "function"
        }]
        token_contract_dec = web3.eth.contract(address=asset_address, abi=erc20_abi_dec)
        decimals = token_contract_dec.functions.decimals().call()
        try:
            withdraw_amount_tokens = float(withdraw_str)
        except ValueError:
            raise Exception("Withdrawal amount must be a number for ERC20 assets.")
        withdraw_value = int(withdraw_amount_tokens * (10 ** decimals))
        print(f"\nWithdrawing {withdraw_amount_tokens} {asset_input.upper()} => {withdraw_value} in smallest unit.")

    withdraw_abi = [
        {
            "inputs": [
                {"internalType": "address", "name": "asset", "type": "address"},
                {"internalType": "uint256", "name": "amount", "type": "uint256"},
                {"internalType": "address", "name": "to", "type": "address"}
            ],
            "name": "withdraw",
            "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
            "stateMutability": "nonpayable",
            "type": "function"
        }
    ]
    withdraw_contract = web3.eth.contract(address=WITHDRAW_TARGET, abi=withdraw_abi)
    tx = withdraw_contract.functions.withdraw(asset_address, withdraw_value, sender_address).build_transaction({
        "from": sender_address,
        "nonce": nonce,
        "gasPrice": web3.eth.gas_price,
        "chainId": web3.eth.chain_id,
        "gas": 300000,
    })
    print("\n📨 Sending withdrawal transaction:", tx)
    signed_tx = web3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
    return f"🚀 Withdrawal transaction sent! Tx hash: {web3.to_hex(tx_hash)}"

# ------------------------------
# New: Combined Detailed Query Function for Positions
# ------------------------------
def blend_full_query(filter_token: str = None):
    """
    Query the full state of Blend and provide detailed, human-readable information 
    about your positions.
    
    If filter_token is provided (by symbol), only details for that asset are returned.
    For known tokens like USDC or USDT, raw balances are divided by 1e6; otherwise, assume 1e18.
    If no filter is provided, a detailed summary of all positions is returned.
    """
    # Define a simple decimals mapping for known tokens.
    decimals_mapping = {
        "usdc": 6,
        "usdt": 6
    }
    
    data = blend_query_subgraph()
    reserves = data.get("reserves", [])
    user_reserves = data.get("userReserves", [])
    
    # If no filter_token is provided, produce a broad summary of all positions.
    if not filter_token:
        output = "Broad summary of all your positions on Blend:\n\n"
        if not user_reserves:
            output += "You currently have no positions on Blend."
        else:
            for pos in user_reserves:
                reserve = pos["reserve"]
                symbol = reserve["symbol"].strip()
                decimals = decimals_mapping.get(symbol.lower(), 18)
                try:
                    btoken_balance = int(pos["currentBTokenBalance"]) / (10 ** decimals)
                except Exception:
                    btoken_balance = pos["currentBTokenBalance"]
                try:
                    total_debt = int(pos["currentTotalDebt"]) / (10 ** decimals)
                except Exception:
                    total_debt = pos["currentTotalDebt"]
                lr = int(reserve["liquidityRate"])
                eff_rate = (lr / 1e26) * 100
                output += f"• {symbol} ({reserve['name']}): BToken Balance: {btoken_balance}, Total Debt: {total_debt}, Liquidity Rate: {eff_rate:.3f}%\n"
        return output
    else:
        # Provide detailed breakdown for the specified token.
        output = f"Detailed report for {filter_token.upper()} on Blend:\n\n"
        found = False
        for pos in user_reserves:
            reserve = pos["reserve"]
            symbol = reserve["symbol"].strip()
            if symbol.lower() != filter_token.lower():
                continue
            found = True
            decimals = decimals_mapping.get(symbol.lower(), 18)
            try:
                btoken_balance = int(pos["currentBTokenBalance"]) / (10 ** decimals)
            except Exception:
                btoken_balance = pos["currentBTokenBalance"]
            try:
                total_debt = int(pos["currentTotalDebt"]) / (10 ** decimals)
            except Exception:
                total_debt = pos["currentTotalDebt"]
            lr = int(reserve["liquidityRate"])
            eff_rate = (lr / 1e26) * 100
            output += f"• {symbol} ({reserve['name']}):\n"
            output += f"   - BToken Balance: {btoken_balance}\n"
            output += f"   - Total Debt: {total_debt}\n"
            collateral = "Yes" if pos["usageAsCollateralEnabledOnUser"] else "No"
            output += f"   - Collateral Enabled: {collateral}\n"
            output += f"   - Pool ID: {pos['pool']['id']}\n"
            output += f"   - Liquidity Rate: {eff_rate:.3f}%\n"
            price = reserve.get("price", {}).get("priceInEth", "N/A")
            output += f"   - Price in ETH: {price}\n"
            output += f"   - BToken Underlying: {reserve['bToken']['underlyingAssetAddress']}\n"
        if not found:
            output = f"No positions found for {filter_token.upper()} on Blend."
        return output

# ------------------------------
# Main Interactive Flow (for testing)
# ------------------------------
if __name__ == '__main__':
    action = input("\nAction (deposit/withdraw/fullquery): ").strip().lower()
    if action == "deposit":
        asset_input = input("\nAsset (e.g., usdc, wbtc, btc): ").strip().lower()
        deposit_str = input("Deposit (in tokens for ERC20, in BTC for btc): ").strip()
        result = blend_deposit(asset_input, deposit_str)
        print("\n" + result)
    elif action == "withdraw":
        asset_input = input("\nAsset to withdraw (e.g., usdc, wbtc, btc): ").strip().lower()
        withdraw_str = input("Withdrawal amount: ").strip()
        result = blend_withdraw(asset_input, withdraw_str)
        print("\n" + result)
    elif action == "fullquery":
        filter_token = input("Enter token symbol to filter (or leave blank for broad summary): ").strip()
        filter_token = filter_token if filter_token else None
        result = blend_full_query(filter_token)
        print("\n" + result)
    else:
        raise Exception("Invalid action selected.")