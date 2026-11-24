
from datetime import date
from decimal import Decimal, InvalidOperation
from math import ceil

from extensions import db
from models.financial_goal import FinancialGoal, GoalContribution


_UNSET = object()


# ---------------------------------------------------------
# VALIDATION HELPERS
# ---------------------------------------------------------

def _to_decimal(value):
    try:
        amount = Decimal(str(value))
    except (TypeError, ValueError, InvalidOperation):
        raise ValueError("Invalid monetary amount.")

    if not amount.is_finite():
        raise ValueError("Amount must be a finite number.")

    return amount


def _validate_text(value, field_name, max_length, required=False):
    if value is None:
        if required:
            raise ValueError(f"{field_name} is required.")
        return None

    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be text.")

    value = value.strip()

    if required and not value:
        raise ValueError(f"{field_name} is required.")

    if len(value) > max_length:
        raise ValueError(
            f"{field_name} cannot exceed {max_length} characters."
        )

    return value


# ---------------------------------------------------------
# CREATE FINANCIAL GOAL
# ---------------------------------------------------------

def create_financial_goal(
    user_id,
    name,
    target_amount,
    description=None,
    target_date=None
):
    name = _validate_text(name, "Goal name", 100, required=True)
    description = _validate_text(description, "Description", 10000)

    amount = _to_decimal(target_amount)

    if amount <= 0:
        raise ValueError("Target amount must be greater than zero.")

    if target_date is not None and not isinstance(target_date, date):
        raise ValueError("Invalid target date.")

    goal = FinancialGoal(
        user_id=user_id,
        name=name,
        description=description,
        target_amount=amount,
        target_date=target_date
    )

    try:
        db.session.add(goal)
        db.session.commit()
        return goal

    except Exception:
        db.session.rollback()
        raise


# ---------------------------------------------------------
# GET FINANCIAL GOALS
# ---------------------------------------------------------

def get_user_goals(user_id):
    return (
        FinancialGoal.query
        .filter_by(user_id=user_id)
        .order_by(FinancialGoal.created_at.desc())
        .all()
    )


def get_goal_by_id(user_id, goal_id):
    return FinancialGoal.query.filter_by(
        id=goal_id,
        user_id=user_id
    ).first()


# ---------------------------------------------------------
# CALCULATE GOAL PROGRESS
# ---------------------------------------------------------

def get_goal_progress(goal, today=None):
    today = today or date.today()

    saved_amount = sum(
        (
            Decimal(str(contribution.amount))
            for contribution in goal.contributions
        ),
        Decimal("0")
    )

    target_amount = Decimal(str(goal.target_amount))

    remaining_amount = max(
        target_amount - saved_amount,
        Decimal("0")
    )

    percentage = (
        saved_amount / target_amount * Decimal("100")
        if target_amount > 0
        else Decimal("0")
    )

    percentage = min(percentage, Decimal("100"))

    is_completed = saved_amount >= target_amount

    monthly_savings_required = None

    if (
        goal.target_date
        and goal.target_date > today
        and remaining_amount > 0
    ):
        days_remaining = (goal.target_date - today).days

        months_remaining = max(
            1,
            ceil(days_remaining / 30.4375)
        )

        monthly_savings_required = (
            remaining_amount / Decimal(months_remaining)
        ).quantize(Decimal("0.01"))

    is_overdue = (
        goal.target_date is not None
        and goal.target_date < today
        and not is_completed
    )

    return {
        "saved_amount": saved_amount,
        "target_amount": target_amount,
        "remaining_amount": remaining_amount,
        "progress_percentage": round(float(percentage), 2),
        "monthly_savings_required": monthly_savings_required,
        "is_completed": is_completed,
        "is_overdue": is_overdue
    }


# ---------------------------------------------------------
# ADD GOAL CONTRIBUTION
# ---------------------------------------------------------

def add_goal_contribution(
    user_id,
    goal_id,
    amount,
    note=None,
    contribution_date=None
):
    goal = get_goal_by_id(user_id, goal_id)

    if not goal:
        raise ValueError("Financial goal not found.")

    amount = _to_decimal(amount)

    if amount <= 0:
        raise ValueError("Contribution must be greater than zero.")

    note = _validate_text(note, "Contribution note", 255)

    if contribution_date is None:
        contribution_date = date.today()

    if not isinstance(contribution_date, date):
        raise ValueError("Invalid contribution date.")

    progress = get_goal_progress(goal)

    if progress["is_completed"]:
        raise ValueError("This financial goal is already completed.")

    if amount > progress["remaining_amount"]:
        raise ValueError(
            "Contribution exceeds the remaining goal amount."
        )

    contribution = GoalContribution(
        goal_id=goal.id,
        amount=amount,
        note=note,
        contribution_date=contribution_date
    )

    try:
        db.session.add(contribution)

        new_saved_amount = progress["saved_amount"] + amount

        goal.is_completed = (
            new_saved_amount >= Decimal(str(goal.target_amount))
        )

        db.session.commit()
        return contribution

    except Exception:
        db.session.rollback()
        raise


# ---------------------------------------------------------
# UPDATE FINANCIAL GOAL
# ---------------------------------------------------------

def update_financial_goal(
    user_id,
    goal_id,
    name=_UNSET,
    description=_UNSET,
    target_amount=_UNSET,
    target_date=_UNSET
):
    goal = get_goal_by_id(user_id, goal_id)

    if not goal:
        raise ValueError("Financial goal not found.")

    # Validate all supplied values before modifying the goal.

    new_name = (
        _validate_text(name, "Goal name", 100, required=True)
        if name is not _UNSET
        else goal.name
    )

    new_description = (
        _validate_text(description, "Description", 10000)
        if description is not _UNSET
        else goal.description
    )

    new_target_amount = (
        _to_decimal(target_amount)
        if target_amount is not _UNSET
        else Decimal(str(goal.target_amount))
    )

    if new_target_amount <= 0:
        raise ValueError("Target amount must be greater than zero.")

    progress = get_goal_progress(goal)

    if new_target_amount < progress["saved_amount"]:
        raise ValueError(
            "Target amount cannot be less than the amount already saved."
        )

    new_target_date = (
        target_date
        if target_date is not _UNSET
        else goal.target_date
    )

    if (
        new_target_date is not None
        and not isinstance(new_target_date, date)
    ):
        raise ValueError("Invalid target date.")

    try:
        goal.name = new_name
        goal.description = new_description
        goal.target_amount = new_target_amount
        goal.target_date = new_target_date

        goal.is_completed = (
            progress["saved_amount"] >= new_target_amount
        )

        db.session.commit()
        return goal

    except Exception:
        db.session.rollback()
        raise


# ---------------------------------------------------------
# DELETE FINANCIAL GOAL
# ---------------------------------------------------------

def delete_financial_goal(user_id, goal_id):
    goal = get_goal_by_id(user_id, goal_id)

    if not goal:
        raise ValueError("Financial goal not found.")

    try:
        db.session.delete(goal)
        db.session.commit()
        return True

    except Exception:
        db.session.rollback()
        raise
