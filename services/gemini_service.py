import json

from google import genai
from google.genai import types

from config import Config


class GeminiService:
    """Service responsible for understanding natural-language transactions."""

    def __init__(self):
        if not Config.GEMINI_API_KEY:
            raise ValueError(
                "GEMINI_API_KEY is not configured."
            )

        self.client = genai.Client(
            api_key=Config.GEMINI_API_KEY
        )

        self.model = Config.GEMINI_MODEL

    def classify_transaction(
        self,
        user_input,
        categories
    ):
        """
        Convert natural-language transaction text into
        structured transaction information.

        Example:
            "dosa 60"

        Returns:
            {
                "description": "Dosa",
                "amount": 60,
                "category": "Food",
                "entry_type": "Expense"
            }
        """

        category_list = ", ".join(categories)

        prompt = f"""
You are an AI assistant for a personal finance application.

Your task is to understand a user's transaction description
and extract the relevant financial information.

The user may write transactions informally, for example:

- dosa 60
- chips 20
- swiggy biryani 250
- myntra shopping 421
- recharge 30
- payment to aadi 500 savings

Available categories are:

{category_list}

You MUST choose the category from the available categories.

Do not create a new category.

Classify the transaction as either:
- Expense
- Income

Extract the amount as a number.

If the amount is not present or cannot be determined,
return 0.

The description should contain a clean description of
what the user spent or received money for.

User transaction:
{user_input}
"""

        response_schema = {
            "type": "OBJECT",
            "properties": {
                "description": {
                    "type": "STRING",
                    "description": (
                        "Clean description of the transaction."
                    )
                },
                "amount": {
                    "type": "NUMBER",
                    "description": (
                        "Transaction amount as a number."
                    )
                },
                "category": {
                    "type": "STRING",
                    "description": (
                        "Category selected from the provided categories."
                    )
                },
                "entry_type": {
                    "type": "STRING",
                    "enum": [
                        "Expense",
                        "Income"
                    ],
                    "description": (
                        "Whether the transaction is an expense or income."
                    )
                }
            },
            "required": [
                "description",
                "amount",
                "category",
                "entry_type"
            ]
        }

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=response_schema,
                
            )
        )

        if not response.text:
            raise ValueError(
                "Gemini returned an empty response."
            )

        result = json.loads(response.text)

        return result
    def validate_transaction_result(
        self,
        result,
        categories
    ):
        """Validate Gemini's transaction classification."""

        if not isinstance(result, dict):
            raise ValueError(
                "Gemini returned an invalid response."
            )

        required_fields = [
            "description",
            "amount",
            "category",
            "entry_type"
        ]

        for field in required_fields:
            if field not in result:
                raise ValueError(
                    f"Gemini response is missing: {field}"
                )

        # Validate description
        if not isinstance(result["description"], str):
            raise ValueError(
                "Transaction description must be text."
            )

        if not result["description"].strip():
            raise ValueError(
                "Transaction description cannot be empty."
            )

        # Validate amount
        try:
            amount = float(result["amount"])
        except (TypeError, ValueError):
            raise ValueError(
                "Transaction amount must be a number."
            )

        if amount <= 0:
            raise ValueError(
                "Transaction amount must be greater than zero."
            )

        # Validate category
        if result["category"] not in categories:
            raise ValueError(
                f"Invalid category: {result['category']}"
            )

        # Validate entry type
        if result["entry_type"] not in [
            "Expense",
            "Income"
        ]:
            raise ValueError(
                f"Invalid entry type: {result['entry_type']}"
            )

        return {
            "description": result["description"].strip(),
            "amount": amount,
            "category": result["category"],
            "entry_type": result["entry_type"]
        }