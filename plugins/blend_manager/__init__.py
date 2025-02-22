from .tool import (
    mezo_agent_blend_deposit_tool,
    mezo_agent_blend_withdraw_tool,
    mezo_agent_blend_query_tool
)

def get_tools():
    """Return all Blend Manager tool instances."""
    return [
        mezo_agent_blend_deposit_tool,
        mezo_agent_blend_withdraw_tool,
        mezo_agent_blend_query_tool,
    ]