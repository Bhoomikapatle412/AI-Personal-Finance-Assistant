from datetime import date
from decimal import Decimal

from sqlalchemy import func

from extensions import db
from models import Ledger, Category
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
def get_category_expenses(user_id):
    """
    Calculate total expenses grouped by category.
    Uses a single database query.
    """

    results = db.session.query(
        Category.name,
        func.sum(Ledger.amount)
    ).join(
        Category,
        Ledger.category_id == Category.id
    ).filter(
        Ledger.user_id == user_id,
        Ledger.entry_type == EntryType.EXPENSE
    ).group_by(
        Category.id,
        Category.name
    ).order_by(
        func.sum(Ledger.amount).desc()
    ).all()

    return {
        category_name: Decimal(str(total))
        for category_name, total in results
    }

def get_monthly_income_expenses(user_id):
    """
    Calculate monthly income and expenses.
    """

    results = db.session.query(
        Ledger.transaction_date,
        Ledger.entry_type,
        Ledger.amount
    ).filter(
        Ledger.user_id == user_id
    ).order_by(
        Ledger.transaction_date
    ).all()

    monthly_data = {}

    for transaction_date, entry_type, amount in results:

        month_key = transaction_date.strftime("%Y-%m")

        if month_key not in monthly_data:
            monthly_data[month_key] = {
                "income": Decimal("0"),
                "expenses": Decimal("0")
            }

        if entry_type == EntryType.INCOME:

            monthly_data[month_key]["income"] += Decimal(
                str(amount)
            )

        elif entry_type == EntryType.EXPENSE:

            monthly_data[month_key]["expenses"] += Decimal(
                str(amount)
            )

    return monthly_data