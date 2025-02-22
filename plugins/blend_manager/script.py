import re
from plugins.blend_manager.blend_manager import blend_deposit, blend_withdraw, blend_full_query

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

def blend_query_tool(prompt: str) -> str:
    pattern = r"(?i).*(?:for|about)\s+([a-zA-Z0-9]+).*"
    match = re.search(pattern, prompt)
    filter_token = match.group(1) if match else None
    return blend_full_query(filter_token)