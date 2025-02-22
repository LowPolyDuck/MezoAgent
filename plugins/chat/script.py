from config import llm
from personality_prompt import PERSONALITY_PROMPT

def mezo_chat(prompt: str) -> str:
    query = PERSONALITY_PROMPT + "\n\nUser: " + prompt + "\n\nAnswer according to your defined personality."
    response = llm.invoke(query)
    return response.content.strip()