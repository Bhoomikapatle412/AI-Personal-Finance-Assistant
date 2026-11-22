from datetime import datetime
from extensions import db


class Budget(db.Model):
    __tablename__ = "budgets"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )
    category_id = db.Column(
        db.Integer,
        db.ForeignKey("categories.id"),
        nullable=False
    )
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    month = db.Column(db.Integer, nullable=False)
    year = db.Column(db.Integer, nullable=False)

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    category = db.relationship("Category")
    user = db.relationship("User")

    __table_args__ = (
        db.UniqueConstraint(
            "user_id",
            "category_id",
            "month",
            "year",
            name="unique_monthly_category_budget"
        ),
    )

    def __repr__(self):
        return f"<Budget {self.category_id}: {self.amount} ({self.month}/{self.year})>"