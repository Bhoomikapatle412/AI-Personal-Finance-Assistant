from datetime import datetime

from extensions import db
from .enums import EntryType, PaymentMethod


class Ledger(db.Model):
    __tablename__ = "ledger"

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

    entry_type = db.Column(
        db.Enum(EntryType),
        nullable=False
    )

    amount = db.Column(
        db.Numeric(10, 2),
        nullable=False
    )

    description = db.Column(
        db.String(255),
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

    payment_provider = db.Column(
        db.String(100),
        nullable=True
    )

    transaction_date = db.Column(
        db.Date,
        nullable=False
    )

    notes = db.Column(
        db.Text,
        nullable=True
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    user = db.relationship(
        "User",
        back_populates="ledger_entries"
    )

    category = db.relationship(
        "Category",
        back_populates="ledger_entries"
    )

    def __repr__(self):
        return f"<Ledger {self.description}>"