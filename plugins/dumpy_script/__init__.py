from .tool import (
    mezo_agent_swap_tool,
    mezo_agent_token_info_tool,
    mezo_agent_token_transfer_tool,
    mezo_agent_token_balance_tool,
    mezo_agent_token_price_tool,
    mezo_agent_add_liquidity_tool,
    mezo_agent_remove_liquidity_tool
)

def get_tools():
    """Return all Dumpy Script tool instances."""
    return [
        mezo_agent_swap_tool,
        mezo_agent_token_info_tool,
        mezo_agent_token_transfer_tool,
        mezo_agent_token_balance_tool,
        mezo_agent_token_price_tool,
        mezo_agent_add_liquidity_tool,
        mezo_agent_remove_liquidity_tool,
    ]