from langchain.tools import Tool
from plugins.dumpy_script.script import (
    safe_swap_tool,
    token_transfer_tool,
    token_balance_tool,
    token_price_tool,
    token_info_tool,
    add_liquidity_tool,
    remove_liquidity_tool
)

mezo_agent_swap_tool = Tool(
    name="Mezo Swap Tool",
    func=safe_swap_tool,
    description="Swap tokens on Dumpy. Example: 'Swap 1 MUSD for LIMPETH'."
)

mezo_agent_token_info_tool = Tool(
    name="Mezo Token Info Tool",
    func=token_info_tool,
    description="Answer questions about available tokens on Dumpy."
)

mezo_agent_token_transfer_tool = Tool(
    name="Mezo Token Transfer Tool",
    func=token_transfer_tool,
    description="Transfer tokens from your wallet. For BTC, performs a native coin transfer."
)

mezo_agent_token_balance_tool = Tool(
    name="Mezo Token Balance Tool",
    func=token_balance_tool,
    description="Query your wallet balance for a token."
)

mezo_agent_token_price_tool = Tool(
    name="Mezo Token Price Tool",
    func=token_price_tool,
    description="Check the price of a token in USD and ETH."
)

mezo_agent_add_liquidity_tool = Tool(
    name="Mezo Add Liquidity Tool",
    func=add_liquidity_tool,
    description="Add liquidity to a pool. Example: 'Add 10 MUSD to the MUSD-wtBTC pool'."
)

mezo_agent_remove_liquidity_tool = Tool(
    name="Mezo Remove Liquidity Tool",
    func=remove_liquidity_tool,
    description="Remove liquidity from a pool. Example: 'Remove liquidity from the MUSD-BTC pool'."
)