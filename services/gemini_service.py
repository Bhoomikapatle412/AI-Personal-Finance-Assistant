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
        """

        if not categories:
            raise ValueError(
                "No categories were provided."
            )

        category_list = ", ".join(categories)

        prompt = f"""
You are an AI assistant for a personal finance application.

Understand the user's transaction and return structured
financial information.

Examples:

- dosa 60
- chips 20
- swiggy biryani 250
- myntra shopping 421
- recharge 30
- salary 50000
- pizza 240

Available categories:

{category_list}

Rules:

1. You MUST choose the category from the available categories.
2. NEVER create a new category.
3. Classify the transaction as either Expense or Income.
4. Extract the amount as a number.
5. If the amount cannot be determined, return 0.
6. Return a clean transaction description.
7. Do not include currency symbols in the amount.

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
                response_schema=response_schema
            )
        )

        if not response.text:
            raise ValueError(
                "Gemini returned an empty response."
            )

        try:
            result = json.loads(response.text)

        except json.JSONDecodeError as exc:

            raise ValueError(
                "Gemini returned invalid JSON."
            ) from exc

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

        # Description
        if not isinstance(
            result["description"],
            str
        ):
            raise ValueError(
                "Transaction description must be text."
            )

        description = result["description"].strip()

        if not description:
            raise ValueError(
                "Transaction description cannot be empty."
            )

        # Amount
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

        # Category
        category = result["category"]

        if not isinstance(category, str):
            raise ValueError(
                "Transaction category must be text."
            )

        category = category.strip()

        # Match category case-insensitively so that
        # Gemini returning "food" doesn't fail when
        # the database contains "Food".
        matched_category = next(
            (
                item
                for item in categories
                if item.lower() == category.lower()
            ),
            None
        )

        if matched_category is None:
            raise ValueError(
                f"Invalid category: {category}"
            )

        # Entry type
        entry_type = result["entry_type"]

        if entry_type not in (
            "Expense",
            "Income"
        ):
            raise ValueError(
                f"Invalid entry type: {entry_type}"
            )

        return {
            "description": description,
            "amount": amount,
            "category": matched_category,
            "entry_type": entry_type
        }