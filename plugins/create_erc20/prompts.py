from langchain.output_parsers import StructuredOutputParser, ResponseSchema
from langchain.prompts import PromptTemplate

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
        description="Optional: The mUSD amount for liquidity seeding (default to 100)."
    ),
    ResponseSchema(
        name="seed_percentage",
        description="Optional: The percentage of the token supply for liquidity seeding (default to 10)."
    )
]
create_token_output_parser = StructuredOutputParser.from_response_schemas(create_token_response_schema)
create_token_prompt_template = PromptTemplate(
    template="""Output a JSON object with the following keys:
- name: (string) The name of the token to create (e.g., "TestToken").
- symbol: (string) The symbol for the token (e.g., "TST").
- initial_supply: (number) The initial supply for the token.
- seed_musd: (number, optional) The mUSD amount for liquidity seeding (default 100).
- seed_percentage: (number, optional) The percentage of the token supply for liquidity seeding (default 10).

Extract these details from the following command:
{input}

Your output must be a valid JSON object with no additional text.
""",
    input_variables=["input"],
)