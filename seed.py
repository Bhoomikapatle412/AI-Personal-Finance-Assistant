from app import app
from extensions import db
from models import Category

DEFAULT_CATEGORIES = [
    ("Food", "bi-cup-hot", "#FF6B6B"),
    ("Shopping", "bi-bag", "#4ECDC4"),
    ("Travel", "bi-car-front", "#45B7D1"),
    ("Recharge", "bi-phone", "#96CEB4"),
    ("Entertainment", "bi-film", "#F7B267"),
    ("Healthcare", "bi-heart-pulse", "#E63946"),
    ("Education", "bi-book", "#3A86FF"),
    ("Utilities", "bi-lightning", "#6A4C93"),
    ("Income", "bi-cash-stack", "#2ECC71"),
    ("Transfer", "bi-arrow-left-right", "#6C757D"),
    ("Savings", "bi-piggy-bank", "#F4A261")
]

with app.app_context():

    for name, icon, color in DEFAULT_CATEGORIES:

        exists = Category.query.filter_by(name=name).first()

        if not exists:

            category = Category(
                name=name,
                icon=icon,
                color=color,
                is_default=True
            )

            db.session.add(category)

    db.session.commit()

    print("✅ Default categories added successfully!")