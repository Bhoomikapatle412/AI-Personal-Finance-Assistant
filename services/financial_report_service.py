
from calendar import monthrange
from datetime import date
from decimal import Decimal

from extensions import db
from models import Ledger, Category
from models.budget import Budget
from models.enums import EntryType


ZERO = Decimal("0.00")


def _validate_date_range(start_date, end_date):
    """Validate the requested reporting period."""

    if not isinstance(start_date, date) or not isinstance(end_date, date):
        raise ValueError("Start date and end date must be valid dates.")

    if start_date > end_date:
        raise ValueError("Start date cannot be after end date.")


def _to_decimal(value):
    """Convert monetary values safely to Decimal."""

    if value is None:
        return ZERO

    return Decimal(str(value))


def _get_user_transactions(user_id, start_date, end_date):
    """Fetch transactions belonging only to the specified user."""

    _validate_date_range(start_date, end_date)

    return (
        Ledger.query
        .filter(
            Ledger.user_id == user_id,
            Ledger.transaction_date >= start_date,
            Ledger.transaction_date <= end_date
        )
        .order_by(Ledger.transaction_date.asc())
        .all()
    )


def _get_period_key(transaction_date, group_by):
    """Generate a sortable key for the requested reporting frequency."""

    year = transaction_date.year
    month = transaction_date.month

    if group_by == "daily":
        return transaction_date.isoformat()

    if group_by == "monthly":
        return f"{year}-{month:02d}"

    if group_by == "quarterly":
        quarter = ((month - 1) // 3) + 1
        return f"{year}-Q{quarter}"

    if group_by == "yearly":
        return str(year)

    raise ValueError(
        "Invalid group_by value. Choose daily, monthly, quarterly or yearly."
    )


def _calculate_transaction_totals(transactions):
    """Calculate financial totals using the agreed reporting rules."""

    income = ZERO
    expenses = ZERO
    refunds = ZERO
    savings = ZERO
    investments = ZERO
    loans = ZERO

    for transaction in transactions:
        amount = _to_decimal(transaction.amount)

        if transaction.entry_type == EntryType.INCOME:
            income += amount

        elif transaction.entry_type == EntryType.EXPENSE:
            expenses += amount

        elif transaction.entry_type == EntryType.REFUND:
            refunds += amount

        elif transaction.entry_type == EntryType.SAVINGS:
            savings += amount

        elif transaction.entry_type == EntryType.INVESTMENT:
            investments += amount

        elif transaction.entry_type == EntryType.LOAN:
            loans += amount

        # TRANSFER is deliberately excluded.

    net_expenses = expenses - refunds
    net_cash_flow = income - net_expenses

    savings_rate = (
        (net_cash_flow / income) * Decimal("100")
        if income > ZERO
        else ZERO
    )

    return {
        "income": income,
        "expenses": expenses,
        "refunds": refunds,
        "net_expenses": net_expenses,
        "net_cash_flow": net_cash_flow,
        "savings": savings,
        "investments": investments,
        "loans": loans,
        "savings_rate": savings_rate
    }


def get_financial_summary(user_id, start_date, end_date):
    """
    Return the financial summary for a selected date range.

    Refunds reduce net expenses.
    Savings, investments and loans are reported separately.
    Transfers are excluded.
    """

    transactions = _get_user_transactions(
        user_id,
        start_date,
        end_date
    )

    summary = _calculate_transaction_totals(transactions)

    summary["transaction_count"] = len(transactions)
    summary["start_date"] = start_date
    summary["end_date"] = end_date

    return summary


def get_income_expense_trend(
    user_id,
    start_date,
    end_date,
    group_by="monthly"
):
    """
    Return income and expense trends grouped by day, month,
    quarter or year.
    """

    allowed_groupings = {
        "daily",
        "monthly",
        "quarterly",
        "yearly"
    }

    if group_by not in allowed_groupings:
        raise ValueError(
            "Invalid group_by value. Choose daily, monthly, quarterly or yearly."
        )

    transactions = _get_user_transactions(
        user_id,
        start_date,
        end_date
    )

    grouped_data = {}

    for transaction in transactions:
        if transaction.entry_type not in (
            EntryType.INCOME,
            EntryType.EXPENSE,
            EntryType.REFUND
        ):
            continue

        period = _get_period_key(
            transaction.transaction_date,
            group_by
        )

        if period not in grouped_data:
            grouped_data[period] = {
                "period": period,
                "income": ZERO,
                "expenses": ZERO,
                "refunds": ZERO
            }

        amount = _to_decimal(transaction.amount)

        if transaction.entry_type == EntryType.INCOME:
            grouped_data[period]["income"] += amount

        elif transaction.entry_type == EntryType.EXPENSE:
            grouped_data[period]["expenses"] += amount

        elif transaction.entry_type == EntryType.REFUND:
            grouped_data[period]["refunds"] += amount

    results = []

    for period in sorted(grouped_data):
        item = grouped_data[period]

        item["net_expenses"] = (
            item["expenses"] - item["refunds"]
        )

        item["net_cash_flow"] = (
            item["income"] - item["net_expenses"]
        )

        results.append(item)

    return results


def get_category_expense_breakdown(user_id, start_date, end_date):
    """Return expense and refund totals grouped by category."""

    transactions = _get_user_transactions(
        user_id,
        start_date,
        end_date
    )

    category_totals = {}

    for transaction in transactions:
        if transaction.entry_type not in (
            EntryType.EXPENSE,
            EntryType.REFUND
        ):
            continue

        category = transaction.category

        if category is None:
            continue

        category_id = category.id

        if category_id not in category_totals:
            category_totals[category_id] = {
                "category_id": category.id,
                "category_name": category.name,
                "icon": category.icon,
                "color": category.color,
                "expenses": ZERO,
                "refunds": ZERO
            }

        amount = _to_decimal(transaction.amount)

        if transaction.entry_type == EntryType.EXPENSE:
            category_totals[category_id]["expenses"] += amount

        else:
            category_totals[category_id]["refunds"] += amount

    results = []

    for item in category_totals.values():
        item["net_expenses"] = (
            item["expenses"] - item["refunds"]
        )

        results.append(item)

    return sorted(
        results,
        key=lambda item: item["net_expenses"],
        reverse=True
    )


def get_payment_method_breakdown(user_id, start_date, end_date):
    """Return expense and refund totals grouped by payment method."""

    transactions = _get_user_transactions(
        user_id,
        start_date,
        end_date
    )

    payment_totals = {}

    for transaction in transactions:
        if transaction.entry_type not in (
            EntryType.EXPENSE,
            EntryType.REFUND
        ):
            continue

        method = transaction.payment_method

        method_name = (
            method.value if method else "Unknown"
        )

        if method_name not in payment_totals:
            payment_totals[method_name] = {
                "payment_method": method_name,
                "expenses": ZERO,
                "refunds": ZERO
            }

        amount = _to_decimal(transaction.amount)

        if transaction.entry_type == EntryType.EXPENSE:
            payment_totals[method_name]["expenses"] += amount

        else:
            payment_totals[method_name]["refunds"] += amount

    results = []

    for item in payment_totals.values():
        item["net_expenses"] = (
            item["expenses"] - item["refunds"]
        )

        results.append(item)

    return sorted(
        results,
        key=lambda item: item["net_expenses"],
        reverse=True
    )


def _get_complete_months(start_date, end_date):
    """
    Return only calendar months completely contained
    within the selected date range.
    """

    complete_months = []

    year = start_date.year
    month = start_date.month

    while (year, month) <= (end_date.year, end_date.month):
        first_day = date(year, month, 1)

        last_day = date(
            year,
            month,
            monthrange(year, month)[1]
        )

        if start_date <= first_day and end_date >= last_day:
            complete_months.append((year, month))

        month += 1

        if month > 12:
            month = 1
            year += 1

    return complete_months


def get_budget_vs_actual(user_id, start_date, end_date):
    """
    Compare monthly budgets with actual category spending.

    Only complete calendar months within the selected date
    range are included.

    Actual spending is calculated as expenses minus refunds
    for the corresponding category and month.
    """

    _validate_date_range(start_date, end_date)

    complete_months = _get_complete_months(
        start_date,
        end_date
    )

    if not complete_months:
        return []

    budget_conditions = [
        db.and_(
            Budget.year == year,
            Budget.month == month
        )
        for year, month in complete_months
    ]

    budgets = (
        Budget.query
        .filter(
            Budget.user_id == user_id,
            db.or_(*budget_conditions)
        )
        .all()
    )

    if not budgets:
        return []

    actual_transactions = []

    for year, month in complete_months:
        first_day = date(year, month, 1)

        last_day = date(
            year,
            month,
            monthrange(year, month)[1]
        )

        month_transactions = (
            Ledger.query
            .filter(
                Ledger.user_id == user_id,
                Ledger.transaction_date >= first_day,
                Ledger.transaction_date <= last_day,
                Ledger.entry_type.in_([
                    EntryType.EXPENSE,
                    EntryType.REFUND
                ])
            )
            .all()
        )

        actual_transactions.extend(month_transactions)

    actual_totals = {}

    for transaction in actual_transactions:
        key = (
            transaction.transaction_date.year,
            transaction.transaction_date.month,
            transaction.category_id
        )

        if key not in actual_totals:
            actual_totals[key] = {
                "expenses": ZERO,
                "refunds": ZERO
            }

        amount = _to_decimal(transaction.amount)

        if transaction.entry_type == EntryType.EXPENSE:
            actual_totals[key]["expenses"] += amount

        else:
            actual_totals[key]["refunds"] += amount

    results = []

    for budget in budgets:
        key = (
            budget.year,
            budget.month,
            budget.category_id
        )

        totals = actual_totals.get(
            key,
            {
                "expenses": ZERO,
                "refunds": ZERO
            }
        )

        budget_amount = _to_decimal(budget.amount)

        actual_amount = (
            totals["expenses"] - totals["refunds"]
        )

        remaining = budget_amount - actual_amount

        percentage_used = (
            (actual_amount / budget_amount) * Decimal("100")
            if budget_amount > ZERO
            else ZERO
        )

        results.append({
            "year": budget.year,
            "month": budget.month,
            "category_id": budget.category_id,
            "category_name": budget.category.name,
            "budget_amount": budget_amount,
            "actual_amount": actual_amount,
            "remaining": remaining,
            "percentage_used": percentage_used,
            "is_over_budget": actual_amount > budget_amount
        })

    return sorted(
        results,
        key=lambda item: (
            item["year"],
            item["month"],
            item["category_name"]
        )
    )
