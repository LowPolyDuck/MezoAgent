import os
from dotenv import load_dotenv
from web3 import Web3
from langchain_openai import ChatOpenAI

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

# Global LLM instance
llm = ChatOpenAI(temperature=0, openai_api_key=OpenAI_API_KEY)