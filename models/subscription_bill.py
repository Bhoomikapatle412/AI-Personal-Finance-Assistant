
from datetime import datetime

from sqlalchemy import UniqueConstraint

from extensions import db
from .enums import PaymentMethod


class SubscriptionBill(db.Model):
    __tablename__ = "subscription_bills"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    category_id = db.Column(
        db.Integer,
        db.ForeignKey("categories.id"),
        nullable=False
    )

    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)

    item_type = db.Column(db.String(20), nullable=False)

    expected_amount = db.Column(
        db.Numeric(10, 2),
        nullable=False
    )

    frequency = db.Column(db.String(20), nullable=False)

    start_date = db.Column(db.Date, nullable=False)
    next_due_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=True)

    reminder_days = db.Column(
        db.Integer,
        nullable=False,
        default=3
    )

    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )

    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    user = db.relationship(
        "User",
        back_populates="subscription_bills"
    )

    category = db.relationship("Category")

    # Do not cascade-delete payment history.
    payments = db.relationship(
        "BillPayment",
        back_populates="subscription_bill",
        order_by="BillPayment.payment_date.desc()"
    )

    def __repr__(self):
        return f"<SubscriptionBill {self.name}>"


class BillPayment(db.Model):
    __tablename__ = "bill_payments"

    __table_args__ = (
        UniqueConstraint(
            "subscription_bill_id",
            "due_date",
            name="uq_bill_payment_schedule_due_date"
        ),
    )

    id = db.Column(db.Integer, primary_key=True)

    subscription_bill_id = db.Column(
        db.Integer,
        db.ForeignKey("subscription_bills.id"),
        nullable=False,
        index=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    amount = db.Column(
        db.Numeric(10, 2),
        nullable=False
    )

    due_date = db.Column(
        db.Date,
        nullable=False
    )

    payment_date = db.Column(
        db.Date,
        nullable=False
    )

    payment_method = db.Column(
        db.Enum(PaymentMethod),
        nullable=False
    )

    ledger_id = db.Column(
        db.Integer,
        db.ForeignKey("ledger.id"),
        nullable=False,
        unique=True
    )

    notes = db.Column(db.Text, nullable=True)

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )

    subscription_bill = db.relationship(
        "SubscriptionBill",
        back_populates="payments"
    )

    user = db.relationship("User")

    ledger_entry = db.relationship(
        "Ledger",
        uselist=False
    )

    def __repr__(self):
        return f"<BillPayment {self.id}: {self.amount}>"
