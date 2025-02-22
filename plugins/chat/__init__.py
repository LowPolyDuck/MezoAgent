from .tool import mezo_agent_chat_tool

def get_tools():
    """Return the Chat tool instance."""
    return [mezo_agent_chat_tool]