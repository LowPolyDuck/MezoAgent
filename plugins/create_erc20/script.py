from config import llm
from plugins.create_erc20.prompts import create_token_prompt_template, create_token_output_parser
from plugins.create_erc20.blend_createERC20 import create_erc20_token

def extract_create_token_details(prompt: str):
    formatted_prompt = create_token_prompt_template.format(input=prompt)
    response = llm.invoke(formatted_prompt)
    print("LLM raw create token response:", response.content)
    try:
        details = create_token_output_parser.parse(response.content)
        if "seed_musd" not in details or details["seed_musd"] in [None, ""]:
            details["seed_musd"] = 100
        if "seed_percentage" not in details or details["seed_percentage"] in [None, ""]:
            details["seed_percentage"] = 10
        return details
    except Exception as e:
        return f"Failed to extract create token details: {str(e)}"

def create_token_tool(prompt: str) -> str:
    details = extract_create_token_details(prompt)
    if isinstance(details, dict):
        try:
            details["initial_supply"] = float(details["initial_supply"])
            seed_musd = float(details.get("seed_musd", 100))
            seed_percentage = float(details.get("seed_percentage", 10))
        except Exception as e:
            return f"Failed to parse numeric values: {e}"
        return create_erc20_token(details["name"], details["symbol"], details["initial_supply"], seed_musd, seed_percentage)
    else:
        return details