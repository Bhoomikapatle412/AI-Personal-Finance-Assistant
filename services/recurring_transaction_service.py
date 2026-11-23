
import calendar
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from extensions import db
from models import Ledger
from models.recurring_transaction import RecurringTransaction
from models.enums import EntryType


SUPPORTED_FREQUENCIES = {
    "daily",
    "weekly",
    "monthly",
    "yearly",
}


# ---------------------------------------------------------
# DATE UTILITIES
# ---------------------------------------------------------

def calculate_next_due_date(current_date, frequency):
    """
    Calculate the next occurrence date for a recurring transaction.
    """

    if frequency == "daily":
        return current_date + timedelta(days=1)

    elif frequency == "weekly":
        return current_date + timedelta(weeks=1)

    elif frequency == "monthly":
        year = current_date.year
        month = current_date.month + 1

        if month > 12:
            month = 1
            year += 1

        day = min(
            current_date.day,
            calendar.monthrange(year, month)[1]
        )

        return date(year, month, day)

    elif frequency == "yearly":
        try:
            return date(
                current_date.year + 1,
                current_date.month,
                current_date.day
            )

        except ValueError:
            # Handles February 29 in non-leap years
            return date(current_date.year + 1, 2, 28)

    raise ValueError("Unsupported frequency.")


# ---------------------------------------------------------
# CREATE RECURRING TRANSACTION
# ---------------------------------------------------------

def create_recurring_transaction(
    user_id,
    category_id,
    description,
    amount,
    entry_type,
    payment_method,
    frequency,
    start_date,
    merchant=None,
    end_date=None
):
    """
    Create a new recurring transaction schedule.
    """

    if frequency not in SUPPORTED_FREQUENCIES:
        raise ValueError("Invalid recurring frequency.")

    try:
        amount = Decimal(str(amount))

    except (InvalidOperation, ValueError, TypeError):
        raise ValueError("Invalid amount.")

    if not amount.is_finite() or amount <= 0:
        raise ValueError("Amount must be greater than zero.")

    if not description or not description.strip():
        raise ValueError("Description is required.")

    if not isinstance(start_date, date):
        raise ValueError("Invalid start date.")

    if end_date and end_date < start_date:
        raise ValueError("End date cannot be before start date.")

    recurring_transaction = RecurringTransaction(
        user_id=user_id,
        category_id=category_id,
        description=description.strip(),
        amount=amount,
        entry_type=entry_type,
        payment_method=payment_method,
        frequency=frequency,
        start_date=start_date,
        next_due_date=start_date,
        end_date=end_date,
        merchant=merchant.strip() if merchant else None,
        is_active=True
    )

    db.session.add(recurring_transaction)
    db.session.commit()

    return recurring_transaction


# ---------------------------------------------------------
# GET RECURRING TRANSACTIONS
# ---------------------------------------------------------

def get_user_recurring_transactions(user_id, active_only=False):
    """
    Retrieve recurring transactions belonging to a user.
    """

    query = RecurringTransaction.query.filter_by(
        user_id=user_id
    )

    if active_only:
        query = query.filter_by(is_active=True)

    return query.order_by(
        RecurringTransaction.next_due_date.asc()
    ).all()


# ---------------------------------------------------------
# GET SINGLE RECURRING TRANSACTION
# ---------------------------------------------------------

def get_recurring_transaction(user_id, recurring_id):
    """
    Retrieve a recurring transaction owned by a user.
    """

    return RecurringTransaction.query.filter_by(
        id=recurring_id,
        user_id=user_id
    ).first()


# ---------------------------------------------------------
# UPDATE RECURRING TRANSACTION
# ---------------------------------------------------------

def update_recurring_transaction(
    user_id,
    recurring_id,
    **updates
):
    """
    Update an existing recurring transaction.
    """

    recurring_transaction = get_recurring_transaction(
        user_id,
        recurring_id
    )

    if not recurring_transaction:
        return None

    allowed_fields = {
        "description",
        "amount",
        "category_id",
        "merchant",
        "frequency",
        "payment_method",
        "entry_type",
        "end_date",
    }

    for field, value in updates.items():

        if field not in allowed_fields:
            continue

        if field == "amount":
            try:
                value = Decimal(str(value))

            except (InvalidOperation, ValueError, TypeError):
                raise ValueError("Invalid amount.")

            if not value.is_finite() or value <= 0:
                raise ValueError("Amount must be greater than zero.")

        elif field == "frequency":
            if value not in SUPPORTED_FREQUENCIES:
                raise ValueError("Invalid recurring frequency.")

        elif field == "description":
            if not value or not value.strip():
                raise ValueError("Description cannot be empty.")

            value = value.strip()

        elif field == "merchant":
            value = value.strip() if value else None

        elif field == "end_date":
            if value and value < recurring_transaction.start_date:
                raise ValueError(
                    "End date cannot be before start date."
                )

        setattr(recurring_transaction, field, value)

    db.session.commit()

    return recurring_transaction


# ---------------------------------------------------------
# ACTIVATE / DEACTIVATE RECURRING TRANSACTION
# ---------------------------------------------------------

def toggle_recurring_transaction(
    user_id,
    recurring_id,
    is_active
):
    """
    Activate or deactivate a recurring transaction.
    """

    recurring_transaction = get_recurring_transaction(
        user_id,
        recurring_id
    )

    if not recurring_transaction:
        return None

    recurring_transaction.is_active = bool(is_active)

    db.session.commit()

    return recurring_transaction


# ---------------------------------------------------------
# DELETE RECURRING TRANSACTION
# ---------------------------------------------------------

def delete_recurring_transaction(user_id, recurring_id):
    """
    Delete a recurring transaction schedule.
    """

    recurring_transaction = get_recurring_transaction(
        user_id,
        recurring_id
    )

    if not recurring_transaction:
        return False

    db.session.delete(recurring_transaction)
    db.session.commit()

    return True


# ---------------------------------------------------------
# PROCESS DUE RECURRING TRANSACTIONS
# ---------------------------------------------------------

def process_due_recurring_transactions(
    user_id=None,
    today=None
):
    """
    Generate transactions for recurring schedules that are due.

    If user_id is provided, only that user's schedules are processed.
    Otherwise, all users' schedules are processed.

    Returns the number of transactions generated.
    """

    if today is None:
        today = date.today()

    query = RecurringTransaction.query.filter(
        RecurringTransaction.is_active == True,
        RecurringTransaction.next_due_date <= today
    )

    if user_id is not None:
        query = query.filter_by(user_id=user_id)

    schedules = query.all()

    generated_count = 0

    try:

        for schedule in schedules:

            due_date = schedule.next_due_date

            while due_date <= today:

                # Stop if the schedule has passed its end date
                if schedule.end_date and due_date > schedule.end_date:
                    schedule.is_active = False
                    break

                # Prevent duplicate generation for the same date
                if schedule.last_generated_date != due_date:

                    transaction = Ledger(
                        user_id=schedule.user_id,
                        category_id=schedule.category_id,
                        entry_type=schedule.entry_type,
                        amount=schedule.amount,
                        description=schedule.description,
                        merchant=schedule.merchant,
                        payment_method=schedule.payment_method,
                        transaction_date=due_date
                    )

                    db.session.add(transaction)

                    schedule.last_generated_date = due_date

                    generated_count += 1

                # Calculate the next occurrence
                due_date = calculate_next_due_date(
                    due_date,
                    schedule.frequency
                )

                schedule.next_due_date = due_date

            # Deactivate schedule after final occurrence
            if schedule.end_date and schedule.next_due_date > schedule.end_date:
                schedule.is_active = False

        db.session.commit()

    except Exception:
        db.session.rollback()
        raise

    return generated_count
