
from datetime import datetime

from extensions import db
from .enums import EntryType, PaymentMethod


class RecurringTransaction(db.Model):
    __tablename__ = "recurring_transactions"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

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

    description = db.Column(
        db.String(255),
        nullable=False
    )

    amount = db.Column(
        db.Numeric(10, 2),
        nullable=False
    )

    entry_type = db.Column(
        db.Enum(EntryType),
        nullable=False
    )

    merchant = db.Column(
        db.String(100),
        nullable=True
    )

    payment_method = db.Column(
        db.Enum(PaymentMethod),
        nullable=False
    )

    frequency = db.Column(
        db.String(20),
        nullable=False
    )

    start_date = db.Column(
        db.Date,
        nullable=False
    )

    next_due_date = db.Column(
        db.Date,
        nullable=False
    )

    end_date = db.Column(
        db.Date,
        nullable=True
    )

    last_generated_date = db.Column(
        db.Date,
        nullable=True
    )

    is_active = db.Column(
        db.Boolean,
        default=True,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    user = db.relationship(
        "User"
    )

    category = db.relationship(
        "Category"
    )

    def __repr__(self):
        return f"<RecurringTransaction {self.description}>"
