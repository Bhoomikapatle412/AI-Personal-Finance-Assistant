
from datetime import date
from decimal import Decimal

from sqlalchemy import func, or_

from extensions import db
from models import Ledger, Category
from models.enums import EntryType


# ============================================================
# CREATE TRANSACTION
# ============================================================

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

    if transaction_date is None:
        transaction_date = date.today()

    transaction = Ledger(
        user_id=user_id,
        category_id=category_id,
        entry_type=entry_type,
        amount=Decimal(str(amount)),
        description=description,
        merchant=merchant,
        payment_method=payment_method,
        payment_provider=payment_provider,
        transaction_date=transaction_date,
        notes=notes
    )

    try:

        db.session.add(transaction)
        db.session.commit()

        return transaction

    except Exception:

        db.session.rollback()
        raise


# ============================================================
# DASHBOARD SUMMARY
# ============================================================

def get_dashboard_summary(user_id):

    total_income = (
        db.session.query(
            func.coalesce(
                func.sum(Ledger.amount),
                0
            )
        )
        .filter(
            Ledger.user_id == user_id,
            Ledger.entry_type == EntryType.INCOME
        )
        .scalar()
    )

    total_expenses = (
        db.session.query(
            func.coalesce(
                func.sum(Ledger.amount),
                0
            )
        )
        .filter(
            Ledger.user_id == user_id,
            Ledger.entry_type == EntryType.EXPENSE
        )
        .scalar()
    )

    total_income = Decimal(str(total_income))
    total_expenses = Decimal(str(total_expenses))

    balance = total_income - total_expenses

    recent_transactions = (
        Ledger.query
        .filter(
            Ledger.user_id == user_id
        )
        .order_by(
            Ledger.transaction_date.desc(),
            Ledger.id.desc()
        )
        .limit(10)
        .all()
    )

    return {
        "total_income": total_income,
        "total_expenses": total_expenses,
        "balance": balance,
        "recent_transactions": recent_transactions
    }


# ============================================================
# CURRENT MONTH FINANCIAL METRICS
# ============================================================

def get_current_month_metrics(user_id):

    today = date.today()

    month_start = today.replace(day=1)

    if today.month == 12:

        next_month_start = date(
            today.year + 1,
            1,
            1
        )

    else:

        next_month_start = date(
            today.year,
            today.month + 1,
            1
        )

    monthly_income = (
        db.session.query(
            func.coalesce(
                func.sum(Ledger.amount),
                0
            )
        )
        .filter(
            Ledger.user_id == user_id,
            Ledger.entry_type == EntryType.INCOME,
            Ledger.transaction_date >= month_start,
            Ledger.transaction_date < next_month_start
        )
        .scalar()
    )

    monthly_expenses = (
        db.session.query(
            func.coalesce(
                func.sum(Ledger.amount),
                0
            )
        )
        .filter(
            Ledger.user_id == user_id,
            Ledger.entry_type == EntryType.EXPENSE,
            Ledger.transaction_date >= month_start,
            Ledger.transaction_date < next_month_start
        )
        .scalar()
    )

    monthly_income = Decimal(str(monthly_income))
    monthly_expenses = Decimal(str(monthly_expenses))

    monthly_savings = monthly_income - monthly_expenses

    if monthly_income > 0:

        savings_rate = (
            monthly_savings / monthly_income
        ) * Decimal("100")

    else:

        savings_rate = Decimal("0")

    return {
        "income": monthly_income,
        "expenses": monthly_expenses,
        "savings": monthly_savings,
        "savings_rate": savings_rate
    }
# ============================================================
# MONTH-OVER-MONTH COMPARISON
# ============================================================

def get_month_over_month_comparison(user_id):

    today = date.today()

    current_month_start = today.replace(day=1)

    if today.month == 1:
        previous_month_start = date(
            today.year - 1,
            12,
            1
        )
    else:
        previous_month_start = date(
            today.year,
            today.month - 1,
            1
        )

    # ========================================================
    # CURRENT MONTH TOTALS
    # ========================================================

    current_income = (
        db.session.query(
            func.coalesce(func.sum(Ledger.amount), 0)
        )
        .filter(
            Ledger.user_id == user_id,
            Ledger.entry_type == EntryType.INCOME,
            Ledger.transaction_date >= current_month_start,
            Ledger.transaction_date <= today
        )
        .scalar()
    )

    current_expenses = (
        db.session.query(
            func.coalesce(func.sum(Ledger.amount), 0)
        )
        .filter(
            Ledger.user_id == user_id,
            Ledger.entry_type == EntryType.EXPENSE,
            Ledger.transaction_date >= current_month_start,
            Ledger.transaction_date <= today
        )
        .scalar()
    )

    # ========================================================
    # PREVIOUS MONTH TOTALS
    # ========================================================

    previous_month_end = current_month_start

    previous_income = (
        db.session.query(
            func.coalesce(func.sum(Ledger.amount), 0)
        )
        .filter(
            Ledger.user_id == user_id,
            Ledger.entry_type == EntryType.INCOME,
            Ledger.transaction_date >= previous_month_start,
            Ledger.transaction_date < previous_month_end
        )
        .scalar()
    )

    previous_expenses = (
        db.session.query(
            func.coalesce(func.sum(Ledger.amount), 0)
        )
        .filter(
            Ledger.user_id == user_id,
            Ledger.entry_type == EntryType.EXPENSE,
            Ledger.transaction_date >= previous_month_start,
            Ledger.transaction_date < previous_month_end
        )
        .scalar()
    )

    current_income = Decimal(str(current_income))
    current_expenses = Decimal(str(current_expenses))

    previous_income = Decimal(str(previous_income))
    previous_expenses = Decimal(str(previous_expenses))

    # ========================================================
    # PERCENTAGE CHANGE
    # ========================================================

    if previous_income > 0:

        income_change = (
            (current_income - previous_income)
            / previous_income
        ) * Decimal("100")

    else:

        income_change = Decimal("0")

    if previous_expenses > 0:

        expense_change = (
            (current_expenses - previous_expenses)
            / previous_expenses
        ) * Decimal("100")

    else:

        expense_change = Decimal("0")

    return {
        "current_income": current_income,
        "previous_income": previous_income,
        "income_change": income_change,

        "current_expenses": current_expenses,
        "previous_expenses": previous_expenses,
        "expense_change": expense_change
    }

# ============================================================
# CATEGORY-WISE EXPENSES
# ============================================================

def get_category_expenses(user_id):

    results = (
        db.session.query(
            Category.name,
            func.sum(Ledger.amount)
        )
        .join(
            Category,
            Ledger.category_id == Category.id
        )
        .filter(
            Ledger.user_id == user_id,
            Ledger.entry_type == EntryType.EXPENSE
        )
        .group_by(
            Category.id,
            Category.name
        )
        .order_by(
            func.sum(Ledger.amount).desc()
        )
        .all()
    )

    return {
        category_name: Decimal(str(total))
        for category_name, total in results
    }


# ============================================================
# MONTHLY INCOME / EXPENSES
# ============================================================

def get_monthly_income_expenses(user_id):

    results = (
        db.session.query(
            Ledger.transaction_date,
            Ledger.entry_type,
            Ledger.amount
        )
        .filter(
            Ledger.user_id == user_id
        )
        .order_by(
            Ledger.transaction_date
        )
        .all()
    )

    monthly_data = {}

    for transaction_date, entry_type, amount in results:

        if transaction_date is None:
            continue

        month_key = transaction_date.strftime("%Y-%m")

        if month_key not in monthly_data:

            monthly_data[month_key] = {
                "income": Decimal("0"),
                "expenses": Decimal("0")
            }

        amount = Decimal(str(amount))

        if entry_type == EntryType.INCOME:

            monthly_data[month_key]["income"] += amount

        elif entry_type == EntryType.EXPENSE:

            monthly_data[month_key]["expenses"] += amount

    return monthly_data


# ============================================================
# SEARCH / FILTER TRANSACTIONS
# ============================================================

def search_transactions(
    user_id,
    search=None,
    category_id=None,
    entry_type=None,
    start_date=None,
    end_date=None
):

    query = Ledger.query.filter(
        Ledger.user_id == user_id
    )

    # --------------------------------------------------------
    # SEARCH BY DESCRIPTION OR MERCHANT
    # --------------------------------------------------------

    if search:

        search_term = f"%{search.strip()}%"

        query = query.filter(
            or_(
                Ledger.description.ilike(search_term),
                Ledger.merchant.ilike(search_term)
            )
        )

    # --------------------------------------------------------
    # FILTER BY CATEGORY
    # --------------------------------------------------------

    if category_id is not None:

        query = query.filter(
            Ledger.category_id == category_id
        )

    # --------------------------------------------------------
    # FILTER BY ENTRY TYPE
    # --------------------------------------------------------

    if entry_type is not None:

        query = query.filter(
            Ledger.entry_type == entry_type
        )

    # --------------------------------------------------------
    # FILTER BY START DATE
    # --------------------------------------------------------

    if start_date is not None:

        query = query.filter(
            Ledger.transaction_date >= start_date
        )

    # --------------------------------------------------------
    # FILTER BY END DATE
    # --------------------------------------------------------

    if end_date is not None:

        query = query.filter(
            Ledger.transaction_date <= end_date
        )

    # --------------------------------------------------------
    # RETURN FILTERED TRANSACTIONS
    # --------------------------------------------------------

    return (
        query
        .order_by(
            Ledger.transaction_date.desc(),
            Ledger.id.desc()
        )
        .all()
    )
def get_financial_insights(user_id):
    """
    Generate rule-based financial insights from user transaction data.
    """
    insights = []

    monthly_metrics = get_current_month_metrics(user_id)
    comparison = get_month_over_month_comparison(user_id)
    category_expenses = get_category_expenses(user_id)

    income = float(monthly_metrics.get("income", 0))
    expenses = float(monthly_metrics.get("expenses", 0))
    savings = float(monthly_metrics.get("savings", 0))
    savings_rate = float(monthly_metrics.get("savings_rate", 0))

    # Spending insight
    if expenses > income and income > 0:
        insights.append({
            "type": "warning",
            "title": "Spending exceeds income",
            "message": "Your expenses are higher than your income this month."
        })

    elif income > 0 and expenses < income:
        insights.append({
            "type": "success",
            "title": "You're saving money",
            "message": f"You saved ₹{savings:.2f} this month."
        })

    # Savings rate insight
    if income > 0:
        if savings_rate >= 30:
            insights.append({
                "type": "success",
                "title": "Excellent savings rate",
                "message": f"You saved {savings_rate:.1f}% of your income this month."
            })
        elif savings_rate > 0:
            insights.append({
                "type": "info",
                "title": "Savings opportunity",
                "message": "Consider increasing your savings this month."
            })

    # Month-over-month expense comparison
    expense_change = float(comparison.get("expense_change", 0))

    if expense_change > 10:
        insights.append({
            "type": "warning",
            "title": "Expenses increased",
            "message": f"Your expenses increased by {expense_change:.1f}% compared to last month."
        })

    elif expense_change < -10:
        insights.append({
            "type": "success",
            "title": "Expenses decreased",
            "message": f"Your expenses decreased by {abs(expense_change):.1f}% compared to last month."
        })

    # Highest spending category
    if category_expenses:
        highest_category = max(category_expenses.items(), key=lambda item: item[1])

        insights.append({
            "type": "info",
            "title": "Top spending category",
            "message": f"{highest_category[0]} is your highest spending category."
        })

    # No transaction data
    if income == 0 and expenses == 0:
        insights.append({
            "type": "info",
            "title": "Start tracking your finances",
            "message": "Add transactions to receive personalized financial insights."
        })

    return insights
