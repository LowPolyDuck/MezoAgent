from langchain.tools import Tool
from plugins.blend_manager.script import blend_deposit_tool, blend_withdraw_tool, blend_query_tool

mezo_agent_blend_deposit_tool = Tool(
    name="Mezo Blend Deposit Tool",
    func=blend_deposit_tool,
    description="Deposit into Blend. Format: 'deposit <amount> <asset>'."
)

mezo_agent_blend_withdraw_tool = Tool(
    name="Mezo Blend Withdraw Tool",
    func=blend_withdraw_tool,
    description="Withdraw from Blend. Format: 'withdraw <amount> <asset>'."
)

mezo_agent_blend_query_tool = Tool(
    name="Mezo Blend Query Tool",
    func=blend_query_tool,
    description="Query detailed information about your Blend positions."
)