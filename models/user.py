
from datetime import datetime

from flask_login import UserMixin

from extensions import db, login_manager


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    full_name = db.Column(
        db.String(100),
        nullable=False
    )

    email = db.Column(
        db.String(120),
        unique=True,
        nullable=False
    )

    password_hash = db.Column(
        db.String(255),
        nullable=False
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

    categories = db.relationship(
        "Category",
        back_populates="user",
        lazy=True
    )

    ledger_entries = db.relationship(
        "Ledger",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy=True
    )

    financial_goals = db.relationship(
        "FinancialGoal",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy=True
    )

    subscription_bills = db.relationship(
        "SubscriptionBill",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy=True
    )

    def __repr__(self):
        return f"<User {self.email}>"


@login_manager.user_loader
def load_user(user_id):
    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        return None

    return db.session.get(User, user_id)
