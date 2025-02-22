import re
from config import llm
from plugins.dumpy_script.prompts import (
    swap_prompt_template, swap_output_parser,
    balance_prompt_template, balance_output_parser,
    price_prompt_template, price_output_parser,
    liquidity_add_prompt_template, liquidity_add_output_parser,
    liquidity_remove_prompt_template, liquidity_remove_output_parser
)
from plugins.dumpy_script.blend_dumpyswapscript import (
    swap_tokens_by_symbol,
    list_swap_capabilities,
    transfer_token,
    get_token_balance,
    get_token_price,
    add_liquidity,
    remove_liquidity
)

def extract_swap_details(prompt: str):
    formatted_prompt = swap_prompt_template.format(input=prompt)
    response = llm.invoke(formatted_prompt)
    print("LLM raw swap response:", response.content)
    try:
        return swap_output_parser.parse(response.content)
    except Exception as e:
        return f"Failed to extract swap details: {str(e)}"

def extract_balance_details(prompt: str):
    formatted_prompt = balance_prompt_template.format(input=prompt)
    response = llm.invoke(formatted_prompt)
    print("LLM raw balance response:", response.content)
    try:
        return balance_output_parser.parse(response.content)
    except Exception as e:
        return f"Failed to extract balance details: {str(e)}"

def extract_price_details(prompt: str):
    formatted_prompt = price_prompt_template.format(input=prompt)
    response = llm.invoke(formatted_prompt)
    print("LLM raw price response:", response.content)
    try:
        return price_output_parser.parse(response.content)
    except Exception as e:
        return f"Failed to extract price details: {str(e)}"

def extract_add_liquidity_details(prompt: str):
    formatted_prompt = liquidity_add_prompt_template.format(input=prompt)
    response = llm.invoke(formatted_prompt)
    print("LLM raw add liquidity response:", response.content)
    try:
        return liquidity_add_output_parser.parse(response.content)
    except Exception as e:
        return f"Failed to extract add liquidity details: {str(e)}"

def extract_remove_liquidity_details(prompt: str):
    formatted_prompt = liquidity_remove_prompt_template.format(input=prompt)
    response = llm.invoke(formatted_prompt)
    print("LLM raw remove liquidity response:", response.content)
    try:
        return liquidity_remove_output_parser.parse(response.content)
    except Exception as e:
        return f"Failed to extract remove liquidity details: {str(e)}"

def safe_swap_tool(prompt: str) -> str:
    details = extract_swap_details(prompt)
    if isinstance(details, dict):
        return swap_tokens_by_symbol(**details)
    else:
        return details

def token_transfer_tool(prompt: str) -> str:
    if "btc" in prompt.lower():
        pattern = r"(?i)(send|transfer)\s+([\d\.eE+-]+)\s+btc\s+(?:to)\s+(0x[a-fA-F0-9]{40})"
        match = re.search(pattern, prompt)
        if match:
            amount_str = match.group(2)
            recipient = match.group(3)
            try:
                amount = float(amount_str)
            except:
                return "Couldn't parse the amount."
            return transfer_token("BTC", recipient, amount)
        else:
            return "I couldn't parse your BTC transfer command."
    else:
        pattern = r"(?i)(send|transfer)\s+([\d\.eE+-]+)\s+\$?([A-Z]{2,})\s+(?:to)\s+(0x[a-fA-F0-9]{40})"
        match = re.search(pattern, prompt)
        if match:
            amount_str = match.group(2)
            token_symbol = match.group(3).upper()
            recipient = match.group(4)
            try:
                amount = float(amount_str)
            except:
                return "Couldn't parse the amount."
            return transfer_token(token_symbol, recipient, amount)
        else:
            return "I couldn't parse your transfer command."

def token_balance_tool(prompt: str) -> str:
    details = extract_balance_details(prompt)
    if isinstance(details, dict):
        token_symbol = details.get("token_symbol")
        if token_symbol:
            return get_token_balance(token_symbol)
        else:
            return "Could not extract token symbol for balance query."
    else:
        return details

def token_price_tool(prompt: str) -> str:
    details = extract_price_details(prompt)
    if isinstance(details, dict):
        token_symbol = details.get("token_symbol")
        if token_symbol:
            return get_token_price(token_symbol)
        else:
            return "Could not extract token symbol for price query."
    else:
        return details

def token_info_tool(prompt: str) -> str:
    return list_swap_capabilities()

def add_liquidity_tool(prompt: str) -> str:
    details = extract_add_liquidity_details(prompt)
    if isinstance(details, dict):
        return add_liquidity(**details)
    else:
        return details

def remove_liquidity_tool(prompt: str) -> str:
    details = extract_remove_liquidity_details(prompt)
    if isinstance(details, dict):
        return remove_liquidity(**details)
    else:
        return details