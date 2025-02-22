from langchain.tools import Tool
from plugins.chat.script import mezo_chat

mezo_agent_chat_tool = Tool(
    name="Mezo Chat Tool",
    func=mezo_chat,
    description="Chat with the agent using its personality."
)