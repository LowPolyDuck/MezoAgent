from .tool import mezo_agent_create_token_tool

def get_tools():
    """Return all Create ERC20 tool instances."""
    return [mezo_agent_create_token_tool]