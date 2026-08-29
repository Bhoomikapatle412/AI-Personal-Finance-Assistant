from app import create_app
from models import Category

from services.gemini_service import GeminiService


app = create_app()

with app.app_context():

    # Get categories from the database
    categories = [
        category.name
        for category in Category.query.filter(
            Category.is_default == True
        ).all()
    ]

    print("Database categories:")
    print(categories)

    # Initialize Gemini
    gemini = GeminiService()

    # Test natural-language transaction
    result = gemini.classify_transaction(
    "dosa 60",
    categories
)

validated_result = gemini.validate_transaction_result(
    result,
    categories
)

print("\nGemini result:")
print(result)

print("\nValidated result:")
print(validated_result)