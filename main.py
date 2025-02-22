from config import llm
from personality_prompt import PERSONALITY_PROMPT
from rich.console import Console
from langchain.agents import initialize_agent, AgentType
from langchain.memory import ConversationBufferMemory

# Import plugin loader
from plugins import load_plugins

# List the plugin names you want to include
plugin_names = [
    "dumpy_script",
    "create_erc20",
    "blend_manager",
    "yield_optimizer",
    "chat"
]

tools = load_plugins(plugin_names)

def create_agent():
    memory = ConversationBufferMemory(memory_key="chat_history")
    return initialize_agent(
        tools=tools,
        llm=llm,
        agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        memory=memory,
        verbose=False,
        handle_parsing_errors=True
    )

console = Console()

def main():
    agent = create_agent()
    console.print("Your Mezo Agent is live! Type your requests (or type 'exit' to quit):", style="bold blue")
    while True:
        user_input = input("> ")
        if user_input.strip().lower() in ["exit", "quit"]:
            console.print("Mezo Agent signing off.", style="bold blue")
            break
        final_prompt = PERSONALITY_PROMPT + "\n\nUser: " + user_input
        try:
            response = agent.invoke(final_prompt)
            if isinstance(response, dict):
                final_answer = response.get("output", str(response))
            else:
                final_answer = response
            console.print("\n" + final_answer, style="bold green")
        except Exception as e:
            console.print(f"Error: {e}", style="bold red")

if __name__ == "__main__":
    main()