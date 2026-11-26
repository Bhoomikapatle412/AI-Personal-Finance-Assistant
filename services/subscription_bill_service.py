
import calendar
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from sqlalchemy.exc import IntegrityError

from extensions import db
from models import Category, Ledger
from models.enums import EntryType, PaymentMethod
from models.subscription_bill import SubscriptionBill, BillPayment


SUPPORTED_FREQUENCIES = {
    "daily",
    "weekly",
    "monthly",
    "quarterly",
    "yearly",
}

SUPPORTED_ITEM_TYPES = {
    "subscription",
    "bill",
}


# ============================================================
# VALIDATION UTILITIES
# ============================================================

def _validate_amount(amount):
    """Convert an amount to Decimal and validate it."""

    try:
        amount = Decimal(str(amount))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError("Invalid amount.")

    if not amount.is_finite() or amount <= 0:
        raise ValueError("Amount must be greater than zero.")

    if amount.as_tuple().exponent < -2:
        raise ValueError("Amount cannot have more than two decimal places.")

    if amount >= Decimal("100000000"):
        raise ValueError("Amount exceeds the supported limit.")

    return amount


def _validate_date(value, field_name):
    """Validate that a value is a date."""

    if not isinstance(value, date):
        raise ValueError(f"Invalid {field_name}.")

    return value


def _validate_frequency(frequency):
    """Validate billing frequency."""

    if not isinstance(frequency, str):
        raise ValueError("Invalid frequency.")

    frequency = frequency.strip().lower()

    if frequency not in SUPPORTED_FREQUENCIES:
        raise ValueError("Unsupported billing frequency.")

    return frequency


def _validate_item_type(item_type):
    """Validate whether the item is a subscription or bill."""

    if not isinstance(item_type, str):
        raise ValueError("Invalid item type.")

    item_type = item_type.strip().lower()

    if item_type not in SUPPORTED_ITEM_TYPES:
        raise ValueError("Item type must be subscription or bill.")

    return item_type


def _validate_payment_method(payment_method):
    """Validate payment method."""

    if isinstance(payment_method, PaymentMethod):
        return payment_method

    if not isinstance(payment_method, str):
        raise ValueError("Invalid payment method.")

    try:
        return PaymentMethod(payment_method)
    except ValueError:
        raise ValueError("Unsupported payment method.")


def _validate_category(user_id, category_id):
    """
    Ensure the category is either a default category
    or belongs to the current user.
    """

    category = Category.query.filter(
        Category.id == category_id,
        db.or_(
            Category.is_default.is_(True),
            Category.user_id == user_id
        )
    ).first()

    if not category:
        raise ValueError("Invalid category selected.")

    return category


# ============================================================
# DATE UTILITIES
# ============================================================

def calculate_next_due_date(
    current_date,
    frequency,
    anchor_day=None,
    anchor_month=None
):
    """
    Calculate the next billing date.

    Monthly, quarterly and yearly schedules preserve the
    original billing day/month to avoid date drift.

    Example:
        January 31 -> February 28 -> March 31
    """

    current_date = _validate_date(current_date, "current date")
    frequency = _validate_frequency(frequency)

    if frequency == "daily":
        return current_date + timedelta(days=1)

    if frequency == "weekly":
        return current_date + timedelta(weeks=1)

    if frequency in {"monthly", "quarterly"}:
        months_to_add = 1 if frequency == "monthly" else 3

        total_months = (
            current_date.year * 12
            + current_date.month - 1
            + months_to_add
        )

        year = total_months // 12
        month = total_months % 12 + 1

        day = anchor_day or current_date.day
        day = min(day, calendar.monthrange(year, month)[1])

        return date(year, month, day)

    if frequency == "yearly":
        year = current_date.year + 1
        month = anchor_month or current_date.month
        day = anchor_day or current_date.day

        day = min(day, calendar.monthrange(year, month)[1])

        return date(year, month, day)

    raise ValueError("Unsupported billing frequency.")


# ============================================================
# GET SUBSCRIPTION / BILL
# ============================================================

def get_subscription_bill(user_id, bill_id):
    """Retrieve a subscription or bill belonging to a user."""

    return SubscriptionBill.query.filter_by(
        id=bill_id,
        user_id=user_id
    ).first()


def get_user_subscription_bills(
    user_id,
    active_only=False,
    item_type=None
):
    """Retrieve all subscriptions and bills belonging to a user."""

    query = SubscriptionBill.query.filter_by(user_id=user_id)

    if active_only:
        query = query.filter_by(is_active=True)

    if item_type:
        item_type = _validate_item_type(item_type)
        query = query.filter_by(item_type=item_type)

    return query.order_by(
        SubscriptionBill.next_due_date.asc(),
        SubscriptionBill.id.desc()
    ).all()


# ============================================================
# CREATE SUBSCRIPTION / BILL
# ============================================================

def create_subscription_bill(
    user_id,
    category_id,
    name,
    item_type,
    expected_amount,
    frequency,
    start_date,
    description=None,
    end_date=None,
    reminder_days=3
):
    """Create a subscription or bill schedule."""

    if not isinstance(name, str) or not name.strip():
        raise ValueError("Name is required.")

    name = name.strip()

    if len(name) > 150:
        raise ValueError("Name cannot exceed 150 characters.")

    expected_amount = _validate_amount(expected_amount)
    frequency = _validate_frequency(frequency)
    item_type = _validate_item_type(item_type)

    start_date = _validate_date(start_date, "start date")

    if end_date is not None:
        end_date = _validate_date(end_date, "end date")

        if end_date < start_date:
            raise ValueError("End date cannot be before start date.")

    try:
        reminder_days = int(reminder_days)
    except (ValueError, TypeError):
        raise ValueError("Invalid reminder days.")

    if not 0 <= reminder_days <= 30:
        raise ValueError("Reminder days must be between 0 and 30.")

    _validate_category(user_id, category_id)

    bill = SubscriptionBill(
        user_id=user_id,
        category_id=category_id,
        name=name,
        description=description.strip() if description else None,
        item_type=item_type,
        expected_amount=expected_amount,
        frequency=frequency,
        start_date=start_date,
        next_due_date=start_date,
        end_date=end_date,
        reminder_days=reminder_days,
        is_active=True
    )

    try:
        db.session.add(bill)
        db.session.commit()
        return bill

    except Exception:
        db.session.rollback()
        raise


# ============================================================
# UPDATE SUBSCRIPTION / BILL
# ============================================================

def update_subscription_bill(user_id, bill_id, **updates):
    """Update an existing subscription or bill."""

    bill = get_subscription_bill(user_id, bill_id)

    if not bill:
        return None

    allowed_fields = {
        "name",
        "description",
        "category_id",
        "item_type",
        "expected_amount",
        "frequency",
        "start_date",
        "next_due_date",
        "end_date",
        "reminder_days",
    }

    unknown_fields = set(updates) - allowed_fields

    if unknown_fields:
        raise ValueError(
            f"Unsupported fields: {', '.join(sorted(unknown_fields))}"
        )

    proposed_start = updates.get("start_date", bill.start_date)
    proposed_end = updates.get("end_date", bill.end_date)
    proposed_due = updates.get("next_due_date", bill.next_due_date)

    _validate_date(proposed_start, "start date")
    _validate_date(proposed_due, "next due date")

    if proposed_end is not None:
        _validate_date(proposed_end, "end date")

        if proposed_end < proposed_start:
            raise ValueError("End date cannot be before start date.")

    if "name" in updates:
        name = updates["name"]

        if not isinstance(name, str) or not name.strip():
            raise ValueError("Name cannot be empty.")

        if len(name.strip()) > 150:
            raise ValueError("Name cannot exceed 150 characters.")

        bill.name = name.strip()

    if "description" in updates:
        description = updates["description"]
        bill.description = description.strip() if description else None

    if "category_id" in updates:
        _validate_category(user_id, updates["category_id"])
        bill.category_id = updates["category_id"]

    if "item_type" in updates:
        bill.item_type = _validate_item_type(updates["item_type"])

    if "expected_amount" in updates:
        bill.expected_amount = _validate_amount(
            updates["expected_amount"]
        )

    if "frequency" in updates:
        bill.frequency = _validate_frequency(updates["frequency"])

    if "start_date" in updates:
        bill.start_date = proposed_start

    if "next_due_date" in updates:
        bill.next_due_date = proposed_due

    if "end_date" in updates:
        bill.end_date = proposed_end

    if "reminder_days" in updates:
        try:
            reminder_days = int(updates["reminder_days"])
        except (ValueError, TypeError):
            raise ValueError("Invalid reminder days.")

        if not 0 <= reminder_days <= 30:
            raise ValueError("Reminder days must be between 0 and 30.")

        bill.reminder_days = reminder_days

    try:
        db.session.commit()
        return bill

    except Exception:
        db.session.rollback()
        raise


# ============================================================
# UPCOMING / OVERDUE STATUS
# ============================================================

def get_subscription_bill_status(bill, today=None):
    """Calculate the current status of a subscription or bill."""

    if today is None:
        today = date.today()

    if bill.end_date and bill.next_due_date > bill.end_date:
        return "completed"

    if not bill.is_active:
        return "paused"

    if bill.next_due_date < today:
        return "overdue"

    reminder_date = bill.next_due_date - timedelta(
        days=bill.reminder_days
    )

    if reminder_date <= today <= bill.next_due_date:
        return "due_soon"

    return "upcoming"


def get_upcoming_and_overdue_bills(user_id, today=None):
    """Retrieve active bills with their calculated payment status."""

    if today is None:
        today = date.today()

    bills = get_user_subscription_bills(
        user_id,
        active_only=True
    )

    results = []

    for bill in bills:
        status = get_subscription_bill_status(bill, today)

        if status in {"due_soon", "overdue"}:
            results.append({
                "bill": bill,
                "status": status,
                "days_until_due": (bill.next_due_date - today).days
            })

    return results


# ============================================================
# RECORD PAYMENT
# ============================================================

def record_bill_payment(
    user_id,
    bill_id,
    amount,
    payment_date,
    payment_method,
    due_date,
    notes=None
):
    """
    Record a confirmed payment.

    Creates a Ledger expense and BillPayment record together.
    Both operations succeed or both are rolled back.

    The actual payment amount may differ from expected_amount.

    The submitted due_date must match the schedule's current
    next_due_date. This prevents an outdated request from
    accidentally recording a second payment for the next cycle.
    """

    bill = get_subscription_bill(user_id, bill_id)

    if not bill:
        raise ValueError("Subscription or bill not found.")

    if not bill.is_active:
        raise ValueError("Cannot record payment for a paused item.")

    if bill.end_date and bill.next_due_date > bill.end_date:
        raise ValueError("This billing schedule has ended.")

    amount = _validate_amount(amount)
    payment_date = _validate_date(payment_date, "payment date")
    submitted_due_date = _validate_date(due_date, "due date")
    payment_method = _validate_payment_method(payment_method)

    # Reject stale requests before creating any records.
    if submitted_due_date != bill.next_due_date:
        raise ValueError(
            "This payment request is outdated. "
            "Refresh the page and check the current due date."
        )

    # Prevent duplicate payment for the current billing cycle.
    existing_payment = BillPayment.query.filter_by(
        subscription_bill_id=bill.id,
        due_date=submitted_due_date
    ).first()

    if existing_payment:
        raise ValueError("This billing cycle has already been paid.")

    category = _validate_category(user_id, bill.category_id)

    clean_notes = notes.strip() if notes else None

    ledger_entry = Ledger(
        user_id=user_id,
        category_id=category.id,
        entry_type=EntryType.EXPENSE,
        amount=amount,
        description=f"Payment: {bill.name}",
        payment_method=payment_method,
        transaction_date=payment_date,
        notes=clean_notes
    )

    try:
        db.session.add(ledger_entry)
        db.session.flush()

        payment = BillPayment(
            subscription_bill_id=bill.id,
            user_id=user_id,
            amount=amount,
            due_date=submitted_due_date,
            payment_date=payment_date,
            payment_method=payment_method,
            ledger_id=ledger_entry.id,
            notes=clean_notes
        )

        db.session.add(payment)

        # Advance from the scheduled due date, not the actual
        # payment date, so early/late payments do not shift the cycle.
        bill.next_due_date = calculate_next_due_date(
            submitted_due_date,
            bill.frequency,
            anchor_day=bill.start_date.day,
            anchor_month=bill.start_date.month
        )

        if bill.end_date and bill.next_due_date > bill.end_date:
            bill.is_active = False

        db.session.commit()

        return payment

    except IntegrityError:
        db.session.rollback()
        raise ValueError(
            "This billing cycle has already been recorded."
        )

    except Exception:
        db.session.rollback()
        raise


# ============================================================
# PAYMENT HISTORY
# ============================================================

def get_bill_payment_history(user_id, bill_id):
    """Retrieve payment history for a user's subscription or bill."""

    bill = get_subscription_bill(user_id, bill_id)

    if not bill:
        return None

    return BillPayment.query.filter_by(
        user_id=user_id,
        subscription_bill_id=bill.id
    ).order_by(
        BillPayment.payment_date.desc(),
        BillPayment.id.desc()
    ).all()


def get_user_bill_payments(user_id):
    """Retrieve payment history across all subscriptions and bills."""

    return BillPayment.query.filter_by(
        user_id=user_id
    ).order_by(
        BillPayment.payment_date.desc(),
        BillPayment.id.desc()
    ).all()


# ============================================================
# PAUSE / RESUME
# ============================================================

def toggle_subscription_bill(user_id, bill_id, is_active):
    """Pause or resume a subscription or bill."""

    bill = get_subscription_bill(user_id, bill_id)

    if not bill:
        return None

    if not isinstance(is_active, bool):
        raise ValueError("Invalid active status.")

    if is_active and bill.end_date:
        if bill.next_due_date > bill.end_date:
            raise ValueError("Cannot resume a completed billing schedule.")

    bill.is_active = is_active

    try:
        db.session.commit()
        return bill

    except Exception:
        db.session.rollback()
        raise


# ============================================================
# DELETE SUBSCRIPTION / BILL
# ============================================================

def delete_subscription_bill(user_id, bill_id):
    """
    Delete a schedule only if it has no payment history.

    Schedules with payment history should be paused instead,
    preserving their financial records.
    """

    bill = get_subscription_bill(user_id, bill_id)

    if not bill:
        return False

    if bill.payments:
        raise ValueError(
            "This item has payment history. Pause it instead of deleting it."
        )

    try:
        db.session.delete(bill)
        db.session.commit()
        return True

    except Exception:
        db.session.rollback()
        raise
