import os
import json
import re
import time
import requests
from web3 import Web3
from dotenv import load_dotenv
from rich.console import Console

# --- Existing Imports from Your Codebase ---
from plugins.yield_optimizer.yield_dumpyswapscript import (
    swap_tokens_by_symbol,  # originally expects arguments: amount, from_symbol, to_symbol
    list_swap_capabilities,
    transfer_token,
    get_token_balance,
    get_token_price,
    add_liquidity,
    remove_liquidity
)
from plugins.yield_optimizer.yield_createERC20 import create_erc20_token
from plugins.yield_optimizer.yield_manager import blend_deposit, blend_withdraw, blend_full_query

# Initialize console and load environment
console = Console()
load_dotenv()

OpenAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OpenAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found in environment variables!")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
if not PRIVATE_KEY:
    raise ValueError("PRIVATE_KEY not found in environment variables!")

RPC_URL = os.getenv("RPC_URL", "https://rpc.test.mezo.org")
web3 = Web3(Web3.HTTPProvider(RPC_URL))
account = web3.eth.account.from_key(PRIVATE_KEY)
sender_address = account.address

# -------------------------------
# Configuration: Only Rebalance Between Stables
# -------------------------------
STABLE_TOKENS = ["usdc", "usdt", "dai"]
# Typical decimals: USDC/USDT = 6, DAI = 18
DECIMALS_MAPPING = {"usdc": 6, "usdt": 6, "dai": 18}

# -------------------------------
# Blend Subgraph Setup
# -------------------------------
BLEND_SUBGRAPH_URL = os.getenv(
    "BLEND_SUBGRAPH_URL",
    "https://api.goldsky.com/api/public/project_cm040smxin6ju01x481kh0o8l/subgraphs/blend-mezotest/1.0.1/gn"
)
USER_ADDRESS = sender_address.lower()

BLEND_GRAPHQL_QUERY = f"""
query MyAssets {{
  userReserves(where: {{user: "{USER_ADDRESS}"}}) {{
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

def query_blend_subgraph():
    console.print("Querying Blend subgraph...", style="bold blue")
    response = requests.post(BLEND_SUBGRAPH_URL, json={'query': BLEND_GRAPHQL_QUERY})
    if response.status_code != 200:
        raise Exception("Failed to query Blend subgraph")
    return response.json().get("data", {})

def query_stable_yields_and_holdings():
    data = query_blend_subgraph()
    user_reserves = data.get("userReserves", [])
    yields = {}
    holdings = {}
    addresses = {}
    for pos in user_reserves:
        reserve = pos["reserve"]
        symbol = reserve["symbol"].strip().lower()
        if symbol not in STABLE_TOKENS:
            continue  # Only consider stables
        try:
            lr = int(reserve["liquidityRate"])
            eff_rate = (lr / 1e26) * 100  # human-readable yield percentage
        except Exception:
            eff_rate = 0.0
        yields[symbol] = eff_rate
        try:
            raw_balance = int(pos["currentBTokenBalance"])
        except Exception:
            raw_balance = 0
        decimals = DECIMALS_MAPPING.get(symbol, 18)
        holdings[symbol] = holdings.get(symbol, 0) + raw_balance / (10 ** decimals)
        addresses[symbol] = reserve["bToken"]["underlyingAssetAddress"]
    return yields, holdings, addresses

def calculate_target_weights(yield_dict):
    total_yield = sum(yield_dict.values())
    if total_yield == 0:
        return {token: 0 for token in yield_dict}
    return {token: yield_dict[token] / total_yield for token in yield_dict}

def rebalance_portfolio(current_holdings, target_weights, total_value):
    target_allocation = {token: total_value * weight for token, weight in target_weights.items()}
    differences = {token: target_allocation.get(token, 0) - current_holdings.get(token, 0)
                   for token in target_weights}
    return differences

# -------------------------------
# DumpySwap Subgraph Setup for Simulation
# -------------------------------
DUMPYSWAP_SUBGRAPH_URL = os.getenv(
    "DUMPYSWAP_SUBGRAPH_URL",
    "https://api.goldsky.com/api/public/project_cm48lsrzo0axx01tna6rb1ee9/subgraphs/exchange-v2-mezo/1.0.0/gn"
)

def simulate_swap_by_address(source_addr, target_addr, amount):
    simulation_query = """
    query($source: String!, $target: String!) {
      pairs(where: {
        token0: $source,
        token1: $target
      }) {
        id
        reserve0
        reserve1
        token0 { id }
        token1 { id }
      }
    }
    """
    variables = {"source": source_addr.lower(), "target": target_addr.lower()}
    try:
        response = requests.post(DUMPYSWAP_SUBGRAPH_URL, json={'query': simulation_query, 'variables': variables})
        response.raise_for_status()
    except Exception as e:
        console.print(f"Error querying DumpySwap subgraph: {e}", style="bold red")
        return {"price_impact": 1.0, "swapped_amount": 0}
    data = response.json().get("data", {})
    pairs = data.get("pairs", [])
    if not pairs:
        console.print("No pair found for simulation", style="bold red")
        return {"price_impact": 1.0, "swapped_amount": 0}
    pair = pairs[0]
    try:
        reserve0 = float(pair["reserve0"])
        reserve1 = float(pair["reserve1"])
    except Exception as e:
        console.print(f"Error converting reserves: {e}", style="bold red")
        return {"price_impact": 1.0, "swapped_amount": 0}
    if variables["source"] == pair["token0"]["id"].lower():
        reserve_in = reserve0
        reserve_out = reserve1
    elif variables["source"] == pair["token1"]["id"].lower():
        reserve_in = reserve1
        reserve_out = reserve0
    else:
        return {"price_impact": 1.0, "swapped_amount": 0}
    amount_in = float(amount)
    amount_in_with_fee = amount_in * 997
    numerator = amount_in_with_fee * reserve_out
    denominator = reserve_in * 1000 + amount_in_with_fee
    amount_out = numerator / denominator
    ideal_output = amount_in * (reserve_out / reserve_in)
    price_impact = (ideal_output - amount_out) / ideal_output if ideal_output != 0 else 0
    return {"price_impact": price_impact, "swapped_amount": amount_out}

# -------------------------------
# Core Yield Optimizer Rebalance Function
# -------------------------------
def execute_rebalance():
    try:
        yields, holdings, addr_mapping = query_stable_yields_and_holdings()
    except Exception as e:
        return f"Failed to retrieve stable on-chain data: {e}"
    total_value = sum(holdings.values())
    console.print(f"Total stable portfolio value: {total_value:,.2f}", style="bold green")
    console.print("Current stable yields:", style="bold green")
    for token, yld in yields.items():
        console.print(f"  {token.upper()}: {yld:.2f}%")
    target_weights = calculate_target_weights(yields)
    console.print("Target allocation weights (based on yields):", style="bold green")
    for token, weight in target_weights.items():
        console.print(f"  {token.upper()}: {weight * 100:.2f}%")
    differences = rebalance_portfolio(holdings, target_weights, total_value)
    console.print("Allocation differences (target - current):", style="bold green")
    for token, diff in differences.items():
        sign = "+" if diff >= 0 else ""
        console.print(f"  {token.upper()}: {sign}{diff:,.2f}")
    
    actions_taken = []
    # For each underweighted stable (difference > 0)
    for token, diff in differences.items():
        if diff <= 0:
            continue
        needed = diff  # in token units
        actions_taken.append(f"Need to add {needed:,.2f} {token.upper()}.")
        # Gather overweight candidates (difference < 0)
        overweight_candidates = []
        for candidate, cand_diff in differences.items():
            if candidate == token or cand_diff >= 0:
                continue
            overweight_candidates.append((candidate, abs(cand_diff)))
        if not overweight_candidates:
            actions_taken.append(f"No overweight candidates available for {token.upper()}.")
            continue
        overweight_candidates.sort(key=lambda x: x[1], reverse=True)
        # Check valid swap path exists before withdrawal:
        valid_candidate_found = False
        for candidate, available in overweight_candidates:
            source_addr = addr_mapping.get(candidate)
            target_addr = addr_mapping.get(token)
            if not source_addr or not target_addr:
                continue
            sim = simulate_swap_by_address(source_addr, target_addr, min(needed, available))
            if sim["swapped_amount"] > 0 and sim["price_impact"] <= 0.05:
                valid_candidate_found = True
                break
        if not valid_candidate_found:
            actions_taken.append(f"No valid swap path found for {token.upper()}; skipping withdrawal.")
            continue
        
        for candidate, available in overweight_candidates:
            if needed <= 0:
                break
            portion = min(needed, available)
            source_addr = addr_mapping.get(candidate)
            target_addr = addr_mapping.get(token)
            if not source_addr or not target_addr:
                continue
            simulation = simulate_swap_by_address(source_addr, target_addr, portion)
            if simulation["swapped_amount"] == 0 or simulation["price_impact"] > 0.05:
                actions_taken.append(
                    f"Candidate {candidate.upper()} with available {available:,.2f} not acceptable (price impact: {simulation['price_impact']*100:.2f}%)."
                )
                continue
            try:
                result_withdraw = blend_withdraw(candidate, str(portion))
                actions_taken.append(f"Withdrew {portion:,.2f} {candidate.upper()}.")
                time.sleep(10)
            except Exception as e:
                actions_taken.append(f"Failed to withdraw {portion:,.2f} from {candidate.upper()}: {e}")
                continue
            swap_input = {
                "amount": portion,
                # Pass contract addresses instead of symbols:
                "from_symbol": source_addr,
                "to_symbol": target_addr
            }
            try:
                swap_result = swap_tokens_by_symbol(**swap_input)
                if isinstance(swap_result, str):
                    # If the result is a string and indicates success, parse swapped_amount.
                    if "Swap successful" in swap_result or "✅" in swap_result:
                        m = re.search(r"swapped for ([\d\.]+)", swap_result)
                        if m:
                            swapped_amount = float(m.group(1))
                        else:
                            swapped_amount = 0
                    else:
                        raise Exception(swap_result)
                else:
                    swapped_amount = float(swap_result.get("swapped_amount", 0))
            except Exception as e:
                actions_taken.append(f"Swap execution failed from {candidate.upper()} to {token.upper()}: {e}")
                continue
            if swapped_amount <= 0:
                actions_taken.append(f"Swap did not return a valid swapped amount for {token.upper()} from {candidate.upper()}.")
                continue
            try:
                result_deposit = blend_deposit(token, str(swapped_amount))
                actions_taken.append(
                    f"Swapped {portion:,.2f} {candidate.upper()} to {token.upper()} (price impact: {simulation['price_impact']*100:.2f}%) and deposited."
                )
                time.sleep(10)
            except Exception as e:
                actions_taken.append(f"Failed to deposit {token.upper()} after swap from {candidate.upper()}: {e}")
                continue
            needed -= portion
        if needed > 0:
            actions_taken.append(f"Insufficient overweight funds to fully rebalance {token.upper()}; still need {needed:,.2f}.")
    return "\n".join(actions_taken)

# -------------------------------
# Blend Tool Wrappers (for reference)
# -------------------------------
def blend_deposit_tool(prompt: str) -> str:
    pattern = r"(?i)deposit\s+([\d\.]+)\s+([a-zA-Z0-9]+)"
    match = re.search(pattern, prompt)
    if match:
        amount = match.group(1)
        asset = match.group(2).lower()
        return blend_deposit(asset, amount)
    else:
        return "Could not parse deposit command. Format: deposit <amount> <asset>"

def blend_withdraw_tool(prompt: str) -> str:
    pattern = r"(?i)withdraw\s+([\d\.]+)\s+([a-zA-Z0-9]+)"
    match = re.search(pattern, prompt)
    if match:
        amount = match.group(1)
        asset = match.group(2).lower()
        return blend_withdraw(asset, amount)
    else:
        return "Could not parse withdraw command. Format: withdraw <amount> <asset>"

if __name__ == '__main__':
    outcome = execute_rebalance()
    console.print("Yield Optimizer Outcome:\n", style="bold blue")
    console.print(outcome, style="bold yellow")