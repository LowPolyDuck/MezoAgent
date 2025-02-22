from langchain.output_parsers import StructuredOutputParser, ResponseSchema
from langchain.prompts import PromptTemplate

# Swap extraction prompts
swap_response_schemas = [
    ResponseSchema(name="amount", description="The amount to swap (a number)."),
    ResponseSchema(name="from_symbol", description="The token symbol to swap from (e.g., 'MUSD')."),
    ResponseSchema(name="to_symbol", description="The token symbol to receive (e.g., 'LIMPETH').")
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

# Balance extraction prompts
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

# Price extraction prompts
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

# Liquidity Add extraction prompts
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

# Liquidity Remove extraction prompts
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