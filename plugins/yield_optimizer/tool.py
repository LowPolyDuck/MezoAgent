from langchain.tools import Tool
from plugins.yield_optimizer.script import yield_optimizer_tool

mezo_agent_yield_optimizer_tool = Tool(
    name="Mezo Yield Optimizer Tool",
    func=yield_optimizer_tool,
    description="Rebalance your portfolio using on-chain yield data."
)