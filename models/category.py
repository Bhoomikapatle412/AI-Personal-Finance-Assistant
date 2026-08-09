from datetime import datetime

from extensions import db


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(50), nullable=False)

    icon = db.Column(db.String(50), nullable=False)

    color = db.Column(db.String(20), nullable=False)

    is_default = db.Column(
        db.Boolean,
        default=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=True
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    # Relationships
    user = db.relationship(
        "User",
        back_populates="categories"
    )

    ledger_entries = db.relationship(
        "Ledger",
        back_populates="category",
        lazy=True
    )

    def __repr__(self):
        return f"<Category {self.name}>"