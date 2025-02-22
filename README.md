# Mezo Agent

A LangChain-powered Web3 AI agent that facilitates:
- Plain English BTC transactions
- mUSD transactions 
- DumpySwap token swaps
- Yield optimization
- ERC20 token creation
- Blend protocol interactions

## 🚀 Features

- **Natural Language Processing**: Process plain English requests for crypto transactions
- **Multi-Token Support**: Handle BTC, mUSD, and custom ERC20 tokens
- **DumpySwap Integration**: Automated token swaps and liquidity management
- **Yield Optimization**: Automated portfolio rebalancing based on yield data
- **Blend Protocol**: Deposit and withdraw from Blend lending markets
- **Token Creation**: Deploy and seed new ERC20 tokens with liquidity

## ⚡ Installation

1️⃣ Clone the Repository

2️⃣ Install Requirements

3️⃣ Set Up Environment Variables
Create a `.env` file in the root directory:

OPENAI_API_KEY=your_openai_api_key

PRIVATE_KEY=your_mezo_private_key

🚀 **Usage**

   Run the Agent

   After running, you can interact with the agent by entering commands like:


💡 **Example Commands**

### Transaction Commands
- `"I can't sign rn because im in a rush can you send .01 BTC to 0xABC123"`
  → Sends 0.01 BTC to a recipient

- `"I need to pay my rent! Urgent. Send 100 mUSD to 0xABC123"`
  → Transfers 100 mUSD to a wallet

- `"im gonna get rekt if u dont swap 10 musd for btc rn"`
  → Swaps 10 mUSD for exact BTC via DumpySwap

### Yield Optimization
- `"optimize my yield across stable coins"`
  → Analyzes and rebalances stable coin positions for optimal yield

### Token Creation
- `"create a new token called MezoCoin with symbol MZC"`
  → Deploys new ERC20 token and seeds initial liquidity

### Blend Protocol
- `"deposit 100 USDC into Blend"`
  → Handles deposit into Blend lending markets

📝 **Notes:**

Mezo Agent uses LangChain's StructuredOutputParser Tool to extract structured data from natural language prompt requests based on a multiple web3 transaction schemas. The agent will decide which scehma to use based on user intent. 

Currently working on more robust web3 transaction error handling for Mezo Agent

Your agent key must have a mUSD loan open to use the swap tool.

This code has not been rigourously evaluated and is intended to be experimental  

## 📝 Technical Notes

- Uses LangChain's StructuredOutputParser for natural language processing
- Implements multiple transaction schemas based on user intent
- Integrates with DumpySwap for automated market making
- Connects to Blend protocol for lending operations
- Includes yield optimization algorithms for portfolio management
- Requires mUSD loan for swap functionality

## ⚠️ Disclaimer

This code is experimental and not intended for production use. Use at your own risk.

## 🔒 Requirements

- Active mUSD loan for swap operations
- Sufficient gas for transactions
- Appropriate token approvals for DumpySwap interactions
