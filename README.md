# Mezo Agent

A LangChain-powered Web3 AI agent that facilitates:
- Plain English transactions
- DumpySwap token swaps
- Yield optimization
- ERC20 token creation
- Blend protocol interactions
- Token balance & price checks
- Yield analytics

## 🚀 Features

- **Natural Language Processing**: Process plain English requests for crypto transactions and queries
- **Multi-Token Support**: Handle BTC, mUSD, and custom ERC20 tokens
- **DumpySwap Integration**: Automated token swaps and liquidity management
- **Yield Optimization**: Automated portfolio rebalancing based on yield data
- **Blend Protocol**: Deposit and withdraw from Blend lending markets
- **Token Creation**: Deploy and seed new ERC20 tokens with liquidity
- **Balance & Price Tracking**: Check token balances and current market prices
- **Yield Analytics**: Monitor and analyze yield opportunities across protocols

## ⚡ Installation

1️⃣ Clone the Repository

2️⃣ Install Requirements

3️⃣ Set Up Environment Variables
```
Create a `.env` file in the root directory:

OPENAI_API_KEY=your_openai_api_key

PRIVATE_KEY=your_mezo_private_key
```

🚀 **Usage**

   Run the Agent

   After running, you can interact with the agent by entering commands like:


💡 **Example Commands**

### Transaction Commands
- `"i cant sign rn because im in a tight bowling cap and its cutting off circulation to my head, can you send .01 BTC to 0xABC123"`
  → Sends 0.01 BTC to a recipient

- `"i need to pay my mums barber! Urgent. send 100 mUSD to 0xABC123"`
  → Transfers 100 mUSD to a wallet

- `"im gonna get rekt by NK hackzoorz if u dont swap 10 musd for btc rn"`
  → Swaps 10 mUSD for exact BTC via DumpySwap

### Balance & Price Queries
- `"bro wtf is my BTC balance?"`
  → Shows your current BTC balance

- `"how much mUSD do i have rn g?"`
  → Displays your mUSD balance

- `"gimmie the current price of BTC?"`
  → Shows current BTC price in USD

### Yield Optimization
- `"aight so optimize my yields doe duh fuh"`
  → Analyzes and rebalances stable coin positions for optimal yield

- `"is there any cold ass yield on mUSD?"`
  → Shows current yield rates for mUSD

### Token Creation
- `"make a token called UrMum with symbol MUMZ, seed it fo me, use 69 percent of supply and like 4200 musd or summin"`
  → Deploys new ERC20 token and seeds initial liquidity

### Blend Protocol
- `"deposit 100 USDC into blend ok ty bb"`
  → Handles deposit into Blend lending markets

### Liquidity Management
- `"add a lil liquidity, like 10, to dat mUSD BTC pair"`
  → Adds liquidity to DumpySwap pool

- `"remove all my stupid liquidity from the dumb mUSD BTC pool"`
  → Removes liquidity from DumpySwap pool

📝 **Notes:**

Mezo Agent uses LangChain's StructuredOutputParser Tool to extract structured data from natural language prompt requests based on multiple web3 transaction schemas. The agent will decide which schema to use based on user intent. 

This code has not been rigourously evaluated and is intended to be experimental  

## 📝 Technical Notes

- Uses LangChain's StructuredOutputParser for natural language processing
- Implements multiple transaction schemas based on user intent
- Integrates with DumpySwap for automated market making
- Connects to Blend protocol for lending operations
- Includes yield optimization algorithms for portfolio management
- Features real-time balance and price checking capabilities
- Provides yield analytics across multiple protocols
- Requires mUSD loan for swap functionality

## ⚠️ Disclaimer

This code is experimental and not intended for production use. Use at your own risk.

## 🔒 Requirements

- Sufficient gas for transactions
- Funny ass pants
