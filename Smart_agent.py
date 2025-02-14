import os
import json
import time
import re
from dotenv import load_dotenv
from web3 import Web3
from langchain.tools import Tool
from langchain.agents import initialize_agent, AgentType
from langchain_openai import ChatOpenAI
from langchain.output_parsers import StructuredOutputParser, ResponseSchema
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory
from rich.console import Console

# -------------------------------
# Import the Personality Prompt from its own file
# -------------------------------
from personality_prompt import PERSONALITY_PROMPT

# Import functions from testing_dumpyswapscript.py
from Smart_dumpyswapscript import (
    swap_tokens_by_symbol,
    list_swap_capabilities,
    transfer_token,
    get_token_balance,
    get_token_price,
    add_liquidity,
    remove_liquidity  # removal now uses the factory getPair approach
)

# New import for token creation
from Smart_createERC20 import create_erc20_token

# Initialize Rich Console for pretty output
console = Console()

load_dotenv()

OpenAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OpenAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found in environment variables!")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
if not PRIVATE_KEY:
    raise ValueError("PRIVATE_KEY not found in environment variables!")

RPC_URL = "https://rpc.test.mezo.org"
web3 = Web3(Web3.HTTPProvider(RPC_URL))
account = web3.eth.account.from_key(PRIVATE_KEY)
sender_address = account.address

# -------------------------------
# Define Prompt Templates for Extraction
# -------------------------------
swap_response_schemas = [
    ResponseSchema(name="amount", description="The amount to swap (a number)."),
    ResponseSchema(name="from_symbol", description="The token symbol to swap from (e.g. 'MUSD')."),
    ResponseSchema(name="to_symbol", description="The token symbol to receive (e.g. 'LIMPETH').")
]
swap_output_parser = StructuredOutputParser.from_response_schemas(swap_response_schemas)
swap_prompt_template = PromptTemplate(
    template="""Output a JSON object with the following keys:
- amount: (number) The amount to swap.
- from_symbol: (string) The token symbol to swap from (e.g., "MUSD").
- to_symbol: (string) The token symbol to receive (e.g., "LIMPETH").

Extract these details from the following request:
{input}

Your output must be a valid JSON object with no additional text.
""",
    input_variables=["input"],
)

balance_response_schema = [
    ResponseSchema(name="token_symbol", description="The token symbol to check the balance for (e.g., 'MUSD').")
]
balance_output_parser = StructuredOutputParser.from_response_schemas(balance_response_schema)
balance_prompt_template = PromptTemplate(
    template="""Output a JSON object with the following key:
- token_symbol: (string) The token symbol for which to check the balance (e.g., "MUSD").

Extract this detail from the following query:
{input}

Your output must be a valid JSON object with no additional text.
""",
    input_variables=["input"],
)

price_response_schema = [
    ResponseSchema(name="token_symbol", description="The token symbol to check the price for (e.g., 'LIMPETH').")
]
price_output_parser = StructuredOutputParser.from_response_schemas(price_response_schema)
price_prompt_template = PromptTemplate(
    template="""Output a JSON object with the following key:
- token_symbol: (string) The token symbol for which to check the price (e.g., "LIMPETH").

Extract this detail from the following request:
{input}

Your output must be a valid JSON object with no additional text.
""",
    input_variables=["input"],
)

# Liquidity Add extraction template
liquidity_add_response_schemas = [
    ResponseSchema(name="amount", description="The amount of one token to add."),
    ResponseSchema(name="token_symbol", description="The token being provided."),
    ResponseSchema(name="pair_token", description="The other token in the liquidity pair.")
]
liquidity_add_output_parser = StructuredOutputParser.from_response_schemas(liquidity_add_response_schemas)
liquidity_add_prompt_template = PromptTemplate(
    template="""Output a JSON object with the following keys:
- amount: (number) The amount of one token to add.
- token_symbol: (string) The token being provided.
- pair_token: (string) The other token in the liquidity pair.

Extract these details from:
{input}

Your output must be a valid JSON object with no additional text.
""",
    input_variables=["input"],
)

# Liquidity Remove extraction template
liquidity_remove_response_schemas = [
    ResponseSchema(name="token_symbol", description="The first token in the liquidity pair (e.g., 'MUSD')."),
    ResponseSchema(name="pair_token", description="The second token in the liquidity pair (e.g., 'BTC').")
]
liquidity_remove_output_parser = StructuredOutputParser.from_response_schemas(liquidity_remove_response_schemas)
liquidity_remove_prompt_template = PromptTemplate(
    template="""Output a JSON object with the following keys:
- token_symbol: (string) The first token of the pair.
- pair_token: (string) The second token of the pair.

Extract these details from:
{input}

Your output must be a valid JSON object with no additional text.
""",
    input_variables=["input"],
)

# -------------------------------
# Create Token Extraction Template (Natural Language)
# -------------------------------
create_token_response_schema = [
    ResponseSchema(
        name="name",
        description="The name of the token to create (e.g., 'TestToken')."
    ),
    ResponseSchema(
        name="symbol",
        description="The symbol for the token (e.g., 'TST')."
    ),
    ResponseSchema(
        name="initial_supply",
        description="The initial supply for the token as a number."
    ),
    ResponseSchema(
        name="seed_musd",
        description="Optional: The mUSD amount for liquidity seeding. If the command explicitly states a mUSD amount (e.g., 'seed it with 50 musd'), then use that value. Otherwise, default to 100."
    ),
    ResponseSchema(
        name="seed_percentage",
        description="Optional: The percentage of the token supply to use for liquidity seeding. If not provided, default to 10."
    )
]
create_token_output_parser = StructuredOutputParser.from_response_schemas(create_token_response_schema)
create_token_prompt_template = PromptTemplate(
    template="""Output a JSON object with the following keys:
- name: (string) The name of the token to create (e.g., "TestToken").
- symbol: (string) The symbol for the token (e.g., "TST").
- initial_supply: (number) The initial supply for the token.
- seed_musd: (number, optional) The mUSD amount for liquidity seeding. If the command explicitly states a mUSD amount (e.g., "seed it with 50 musd"), then use that value. Otherwise, default to 100.
- seed_percentage: (number, optional) The percentage of the token supply to use for liquidity seeding. If not provided, default to 10.

Extract these details from the following command:
{input}

Your output must be a valid JSON object with no additional text.
""",
    input_variables=["input"],
)

def extract_create_token_details(prompt: str):
    formatted_prompt = create_token_prompt_template.format(input=prompt)
    response = llm.invoke(formatted_prompt)
    print("LLM raw create token response:", response.content)
    try:
        details = create_token_output_parser.parse(response.content)
        # Default values if not provided
        if "seed_musd" not in details or details["seed_musd"] in [None, ""]:
            details["seed_musd"] = 100
        if "seed_percentage" not in details or details["seed_percentage"] in [None, ""]:
            details["seed_percentage"] = 10
        return details
    except Exception as e:
        return f"Failed to extract create token details: {str(e)}"

# -------------------------------
# Extraction Functions for Other Tools
# -------------------------------
def extract_swap_details(prompt: str):
    formatted_prompt = swap_prompt_template.format(input=prompt)
    response = llm.invoke(formatted_prompt)
    print("LLM raw swap response:", response.content)
    try:
        return swap_output_parser.parse(response.content)
    except Exception as e:
        return f"Failed to extract swap details: {str(e)}"

def extract_balance_details(prompt: str):
    formatted_prompt = balance_prompt_template.format(input=prompt)
    response = llm.invoke(formatted_prompt)
    print("LLM raw balance response:", response.content)
    try:
        return balance_output_parser.parse(response.content)
    except Exception as e:
        return f"Failed to extract balance details: {str(e)}"

def extract_price_details(prompt: str):
    formatted_prompt = price_prompt_template.format(input=prompt)
    response = llm.invoke(formatted_prompt)
    print("LLM raw price response:", response.content)
    try:
        return price_output_parser.parse(response.content)
    except Exception as e:
        return f"Failed to extract price details: {str(e)}"

def extract_add_liquidity_details(prompt: str):
    formatted_prompt = liquidity_add_prompt_template.format(input=prompt)
    response = llm.invoke(formatted_prompt)
    print("LLM raw add liquidity response:", response.content)
    try:
        return liquidity_add_output_parser.parse(response.content)
    except Exception as e:
        return f"Failed to extract add liquidity details: {str(e)}"

def extract_remove_liquidity_details(prompt: str):
    formatted_prompt = liquidity_remove_prompt_template.format(input=prompt)
    response = llm.invoke(formatted_prompt)
    print("LLM raw remove liquidity response:", response.content)
    try:
        return liquidity_remove_output_parser.parse(response.content)
    except Exception as e:
        return f"Failed to extract remove liquidity details: {str(e)}"

def mezo_chat(prompt: str) -> str:
    # Use the consolidated personality prompt here
    query = PERSONALITY_PROMPT + "\n\nUser: " + prompt + "\n\nAnswer in a witty, crypto-native tone."
    response = llm.invoke(query)
    return response.content.strip()

# -------------------------------
# Tool Functions
# -------------------------------
def safe_swap_tool(prompt: str) -> str:
    details = extract_swap_details(prompt)
    if isinstance(details, dict):
        return swap_tokens_by_symbol(**details)
    else:
        return details

def token_transfer_tool(prompt: str) -> str:
    if "btc" in prompt.lower():
        pattern = r"(?i)(send|transfer)\s+([\d\.eE+-]+)\s+btc\s+(?:to)\s+(0x[a-fA-F0-9]{40})"
        match = re.search(pattern, prompt)
        if match:
            amount_str = match.group(2)
            recipient = match.group(3)
            try:
                amount = float(amount_str)
            except:
                return "Couldn't parse the amount."
            return transfer_token("BTC", recipient, amount)
        else:
            return "I couldn't parse your BTC transfer command. Please use 'transfer 0.001 BTC to 0xABC...'."
    else:
        pattern = r"(?i)(send|transfer)\s+([\d\.eE+-]+)\s+\$?([A-Z]{2,})\s+(?:to)\s+(0x[a-fA-F0-9]{40})"
        match = re.search(pattern, prompt)
        if match:
            amount_str = match.group(2)
            token_symbol = match.group(3).upper()
            recipient = match.group(4)
            try:
                amount = float(amount_str)
            except:
                return "Couldn't parse the amount."
            return transfer_token(token_symbol, recipient, amount)
        else:
            return "I couldn't parse your transfer command. Please use the format 'transfer 10 MUSD to 0xABC...'."

def token_balance_tool(prompt: str) -> str:
    details = extract_balance_details(prompt)
    if isinstance(details, dict):
        token_symbol = details.get("token_symbol")
        if token_symbol:
            return get_token_balance(token_symbol)
        else:
            return "Could not extract token symbol for balance query."
    else:
        return details

def token_price_tool(prompt: str) -> str:
    details = extract_price_details(prompt)
    if isinstance(details, dict):
        token_symbol = details.get("token_symbol")
        if token_symbol:
            return get_token_price(token_symbol)
        else:
            return "Could not extract token symbol for price query."
    else:
        return details

def token_info_tool(prompt: str) -> str:
    return list_swap_capabilities()

def add_liquidity_tool(prompt: str) -> str:
    details = extract_add_liquidity_details(prompt)
    if isinstance(details, dict):
        return add_liquidity(**details)
    else:
        return details

def remove_liquidity_tool(prompt: str) -> str:
    details = extract_remove_liquidity_details(prompt)
    if isinstance(details, dict):
        return remove_liquidity(**details)
    else:
        return details

# -------------------------------
# Updated: Create Token Tool (Natural Language with optional liquidity seeding mUSD and percentage)
# -------------------------------
def create_token_tool(prompt: str) -> str:
    details = extract_create_token_details(prompt)
    if isinstance(details, dict):
        try:
            details["initial_supply"] = float(details["initial_supply"])
        except Exception as e:
            return f"Failed to parse initial supply: {e}"
        try:
            seed_musd = float(details.get("seed_musd", 100))
        except Exception as e:
            return f"Failed to parse seed mUSD amount: {e}"
        try:
            seed_percentage = float(details.get("seed_percentage", 10))
        except Exception as e:
            return f"Failed to parse seed percentage: {e}"
        return create_erc20_token(details["name"], details["symbol"], details["initial_supply"], seed_musd, seed_percentage)
    else:
        return details

# -------------------------------
# Chat Tool
# -------------------------------
def mezo_chat_tool(prompt: str) -> str:
    return mezo_chat(prompt)

# -------------------------------
# Initialize LLM
# -------------------------------
llm = ChatOpenAI(temperature=0, openai_api_key=OpenAI_API_KEY)

# -------------------------------
# Define LangChain Tools
# -------------------------------
mezo_agent_swap_tool = Tool(
    name="Mezo Swap Tool",
    func=safe_swap_tool,
    description="Swap tokens on Dumpy. Example: 'Swap 1 MUSD for LIMPETH'."
)
mezo_agent_token_info_tool = Tool(
    name="Mezo Token Info Tool",
    func=token_info_tool,
    description="Answer questions about what tokens you can swap on Dumpy. For example, 'what tokens can I swap on dumpy?'."
)
mezo_agent_token_transfer_tool = Tool(
    name="Mezo Token Transfer Tool",
    func=token_transfer_tool,
    description="Transfer tokens from your wallet. For BTC, perform a native coin transfer. Example: 'transfer 0.001 BTC to 0xABC...'."
)
mezo_agent_token_balance_tool = Tool(
    name="Mezo Token Balance Tool",
    func=token_balance_tool,
    description="Query your wallet balance for a token. For BTC, return your native coin balance. Example: 'what is my BTC balance?'."
)
mezo_agent_token_price_tool = Tool(
    name="Mezo Token Price Tool",
    func=token_price_tool,
    description="Check the price of a token in USD and ETH. For example, 'what is the price of LIMPETH?'."
)
mezo_agent_add_liquidity_tool = Tool(
    name="Mezo Add Liquidity Tool",
    func=add_liquidity_tool,
    description="Add liquidity to a pool. Example: 'Add 10 MUSD to the MUSD-wtBTC pool'."
)
mezo_agent_remove_liquidity_tool = Tool(
    name="Mezo Remove Liquidity Tool",
    func=remove_liquidity_tool,
    description="Remove all liquidity from a pool. Example: 'Remove liquidity from the MUSD-BTC pool'."
)
mezo_agent_create_token_tool = Tool(
    name="Mezo Create Token Tool",
    func=create_token_tool,
    description="Deploy a new ERC20 token. Example: 'create token TestToken TST 1000', or 'create a token called FINALTEST with a ticker of FTX, a supply of 100000, seed it with 50 musd and 15 percent'."
)
mezo_agent_chat_tool = Tool(
    name="Mezo Chat Tool",
    func=mezo_chat_tool,
    description="Answer according to your defined personality."
)

# -------------------------------
# Agent Initialization with Memory and Tools
# -------------------------------
memory = ConversationBufferMemory(memory_key="chat_history")
agent = initialize_agent(
    tools=[
        mezo_agent_swap_tool,
        mezo_agent_token_info_tool,
        mezo_agent_token_transfer_tool,
        mezo_agent_token_balance_tool,
        mezo_agent_token_price_tool,
        mezo_agent_add_liquidity_tool,
        mezo_agent_remove_liquidity_tool,
        mezo_agent_create_token_tool,
        mezo_agent_chat_tool
    ],
    llm=llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    memory=memory,
    verbose=False,
    handle_parsing_errors=True
)

# -------------------------------
# Continuous Conversation Loop
# -------------------------------
console.print("Your Mezo Agent is live! Type your requests (or type 'exit' to quit):", style="bold blue")
while True:
    user_input = input("> ")
    if user_input.strip().lower() in ["exit", "quit"]:
        console.print("Mezo Agent signing off.", style="bold blue")
        break
    # Use the consolidated personality prompt here as well
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