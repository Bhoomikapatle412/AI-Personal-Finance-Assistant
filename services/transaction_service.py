from datetime import date
from decimal import Decimal

from sqlalchemy import func

from extensions import db
from models import Ledger
from models.enums import EntryType


def create_transaction(
    user_id,
    category_id,
    entry_type,
    amount,
    description,
    payment_method,
    merchant=None,
    payment_provider=None,
    transaction_date=None,
    notes=None
):
    """
    Create and save a new transaction.
    """

    transaction = Ledger(
        user_id=user_id,
        category_id=category_id,
        entry_type=entry_type,
        amount=Decimal(str(amount)),
        description=description,
        payment_method=payment_method,
        merchant=merchant,
        payment_provider=payment_provider,
        transaction_date=transaction_date or date.today(),
        notes=notes
    )

    db.session.add(transaction)
    db.session.commit()

    return transaction


def get_user_transactions(user_id):
    """
    Get all transactions belonging to a user.
    Newest transactions appear first.
    """

    return Ledger.query.filter_by(
        user_id=user_id
    ).order_by(
        Ledger.transaction_date.desc(),
        Ledger.id.desc()
    ).all()


def get_recent_transactions(user_id, limit=10):
    """
    Get the most recent transactions for a user.
    """

    return Ledger.query.filter_by(
        user_id=user_id
    ).order_by(
        Ledger.transaction_date.desc(),
        Ledger.id.desc()
    ).limit(limit).all()


def get_total_income(user_id):
    """
    Calculate total income for a user.
    """

    total = db.session.query(
        func.coalesce(
            func.sum(Ledger.amount),
            0
        )
    ).filter(
        Ledger.user_id == user_id,
        Ledger.entry_type == EntryType.INCOME
    ).scalar()

    return Decimal(str(total))


def get_total_expenses(user_id):
    """
    Calculate total expenses for a user.
    """

    total = db.session.query(
        func.coalesce(
            func.sum(Ledger.amount),
            0
        )
    ).filter(
        Ledger.user_id == user_id,
        Ledger.entry_type == EntryType.EXPENSE
    ).scalar()

    return Decimal(str(total))


def get_balance(user_id):
    """
    Calculate current balance:

    Income - Expenses
    """

    income = get_total_income(user_id)
    expenses = get_total_expenses(user_id)

    return income - expenses


def get_dashboard_summary(user_id):
    """
    Get all financial information required
    by the dashboard.
    """

    total_income = get_total_income(user_id)
    total_expenses = get_total_expenses(user_id)

    return {
        "total_income": total_income,
        "total_expenses": total_expenses,
        "balance": total_income - total_expenses,
        "recent_transactions": get_recent_transactions(
            user_id
        )
    }