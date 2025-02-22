from langchain.tools import Tool
from plugins.create_erc20.script import create_token_tool

mezo_agent_create_token_tool = Tool(
    name="Mezo Create Token Tool",
    func=create_token_tool,
    description="Deploy a new ERC20 token. Example: 'create token TestToken TST 1000'"
)