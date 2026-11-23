
from datetime import date
from decimal import InvalidOperation

from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user

from models import Category
from models.enums import EntryType, PaymentMethod

from services.recurring_transaction_service import (
    create_recurring_transaction,
    get_user_recurring_transactions,
    get_recurring_transaction,
    update_recurring_transaction,
    toggle_recurring_transaction,
    delete_recurring_transaction,
    process_due_recurring_transactions,
)


recurring_bp = Blueprint(
    "recurring",
    __name__,
    url_prefix="/recurring"
)


# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------

def parse_date(value, field_name):
    """Convert an ISO date string into a date object."""

    if not value:
        return None

    try:
        return date.fromisoformat(value)

    except (ValueError, TypeError):
        raise ValueError(
            f"Invalid {field_name}. Use YYYY-MM-DD format."
        )


def parse_enum(enum_class, value, field_name):
    """Accept enum names or enum values."""

    if value is None:
        raise ValueError(f"{field_name} is required.")

    if isinstance(value, enum_class):
        return value

    for member in enum_class:
        if member.name == str(value).upper():
            return member

        if member.value.lower() == str(value).lower():
            return member

    raise ValueError(f"Invalid {field_name}.")


def recurring_to_dict(recurring):
    """Convert recurring transaction object into JSON-friendly data."""

    return {
        "id": recurring.id,
        "category_id": recurring.category_id,
        "description": recurring.description,
        "amount": float(recurring.amount),
        "entry_type": recurring.entry_type.value,
        "merchant": recurring.merchant,
        "payment_method": recurring.payment_method.value,
        "frequency": recurring.frequency,
        "start_date": recurring.start_date.isoformat(),
        "next_due_date": recurring.next_due_date.isoformat(),
        "end_date": (
            recurring.end_date.isoformat()
            if recurring.end_date
            else None
        ),
        "last_generated_date": (
            recurring.last_generated_date.isoformat()
            if recurring.last_generated_date
            else None
        ),
        "is_active": recurring.is_active,
        "created_at": (
            recurring.created_at.isoformat()
            if recurring.created_at
            else None
        ),
        "updated_at": (
            recurring.updated_at.isoformat()
            if recurring.updated_at
            else None
        ),
    }


def validate_category(category_id):
    """Ensure the category belongs to the current user or is default."""

    category = Category.query.filter(
        Category.id == category_id,
        (
            (Category.user_id == current_user.id)
            | (Category.user_id.is_(None))
        )
    ).first()

    if not category:
        raise ValueError("Invalid category.")

    return category


# ---------------------------------------------------------
# RECURRING TRANSACTIONS PAGE
# ---------------------------------------------------------

@recurring_bp.route("/page", methods=["GET"])
@login_required
def recurring_page():
    categories = Category.query.filter(
        (
            (Category.user_id == current_user.id)
            | (Category.user_id.is_(None))
        )
    ).order_by(Category.name.asc()).all()

    return render_template(
        "recurring.html",
        categories=categories,
        entry_types=list(EntryType),
        payment_methods=list(PaymentMethod)
    )


# ---------------------------------------------------------
# GET ALL RECURRING TRANSACTIONS
# ---------------------------------------------------------

@recurring_bp.route("/", methods=["GET"])
@login_required
def list_recurring_transactions():
    active_only = (
        request.args.get("active_only", "false").lower()
        == "true"
    )

    recurring_transactions = get_user_recurring_transactions(
        current_user.id,
        active_only=active_only
    )

    return jsonify({
        "success": True,
        "count": len(recurring_transactions),
        "recurring_transactions": [
            recurring_to_dict(item)
            for item in recurring_transactions
        ]
    }), 200


# ---------------------------------------------------------
# CREATE RECURRING TRANSACTION
# ---------------------------------------------------------

@recurring_bp.route("/", methods=["POST"])
@login_required
def create_recurring():
    data = request.get_json(silent=True) or {}

    try:
        category_id = int(data.get("category_id"))
        validate_category(category_id)

        entry_type = parse_enum(
            EntryType,
            data.get("entry_type"),
            "entry type"
        )

        payment_method = parse_enum(
            PaymentMethod,
            data.get("payment_method"),
            "payment method"
        )

        start_date = parse_date(
            data.get("start_date"),
            "start date"
        )

        end_date = parse_date(
            data.get("end_date"),
            "end date"
        )

        if start_date is None:
            raise ValueError("Start date is required.")

        recurring = create_recurring_transaction(
            user_id=current_user.id,
            category_id=category_id,
            description=data.get("description"),
            amount=data.get("amount"),
            entry_type=entry_type,
            payment_method=payment_method,
            frequency=str(
                data.get("frequency", "")
            ).lower(),
            start_date=start_date,
            merchant=data.get("merchant"),
            end_date=end_date
        )

        return jsonify({
            "success": True,
            "message": "Recurring transaction created successfully.",
            "recurring_transaction": recurring_to_dict(recurring)
        }), 201

    except (ValueError, TypeError, InvalidOperation) as error:
        return jsonify({
            "success": False,
            "error": str(error)
        }), 400


# ---------------------------------------------------------
# UPDATE RECURRING TRANSACTION
# ---------------------------------------------------------

@recurring_bp.route("/<int:recurring_id>", methods=["PUT"])
@login_required
def update_recurring(recurring_id):
    recurring = get_recurring_transaction(
        current_user.id,
        recurring_id
    )

    if not recurring:
        return jsonify({
            "success": False,
            "error": "Recurring transaction not found."
        }), 404

    data = request.get_json(silent=True) or {}

    updates = {}

    try:
        if "description" in data:
            updates["description"] = data["description"]

        if "amount" in data:
            updates["amount"] = data["amount"]

        if "merchant" in data:
            updates["merchant"] = data["merchant"]

        if "frequency" in data:
            updates["frequency"] = str(
                data["frequency"]
            ).lower()

        if "category_id" in data:
            category_id = int(data["category_id"])
            validate_category(category_id)
            updates["category_id"] = category_id

        if "entry_type" in data:
            updates["entry_type"] = parse_enum(
                EntryType,
                data["entry_type"],
                "entry type"
            )

        if "payment_method" in data:
            updates["payment_method"] = parse_enum(
                PaymentMethod,
                data["payment_method"],
                "payment method"
            )

        if "end_date" in data:
            updates["end_date"] = parse_date(
                data["end_date"],
                "end date"
            )

        updated = update_recurring_transaction(
            current_user.id,
            recurring_id,
            **updates
        )

        if not updated:
            return jsonify({
                "success": False,
                "error": "Recurring transaction not found."
            }), 404

        return jsonify({
            "success": True,
            "message": "Recurring transaction updated successfully.",
            "recurring_transaction": recurring_to_dict(updated)
        }), 200

    except (ValueError, TypeError, InvalidOperation) as error:
        return jsonify({
            "success": False,
            "error": str(error)
        }), 400


# ---------------------------------------------------------
# PAUSE / RESUME RECURRING TRANSACTION
# ---------------------------------------------------------

@recurring_bp.route(
    "/<int:recurring_id>/toggle",
    methods=["PATCH"]
)
@login_required
def toggle_recurring(recurring_id):
    data = request.get_json(silent=True) or {}

    if "is_active" not in data:
        return jsonify({
            "success": False,
            "error": "is_active is required."
        }), 400

    is_active = data["is_active"]

    if not isinstance(is_active, bool):
        return jsonify({
            "success": False,
            "error": "is_active must be true or false."
        }), 400

    recurring = toggle_recurring_transaction(
        current_user.id,
        recurring_id,
        is_active
    )

    if not recurring:
        return jsonify({
            "success": False,
            "error": "Recurring transaction not found."
        }), 404

    action = "activated" if is_active else "paused"

    return jsonify({
        "success": True,
        "message": f"Recurring transaction {action} successfully.",
        "recurring_transaction": recurring_to_dict(recurring)
    }), 200


# ---------------------------------------------------------
# DELETE RECURRING TRANSACTION
# ---------------------------------------------------------

@recurring_bp.route(
    "/<int:recurring_id>",
    methods=["DELETE"]
)
@login_required
def delete_recurring(recurring_id):
    deleted = delete_recurring_transaction(
        current_user.id,
        recurring_id
    )

    if not deleted:
        return jsonify({
            "success": False,
            "error": "Recurring transaction not found."
        }), 404

    return jsonify({
        "success": True,
        "message": "Recurring transaction deleted successfully."
    }), 200


# ---------------------------------------------------------
# PROCESS DUE TRANSACTIONS
# ---------------------------------------------------------

@recurring_bp.route(
    "/process-due",
    methods=["POST"]
)
@login_required
def process_due():
    try:
        generated_count = process_due_recurring_transactions(
            user_id=current_user.id
        )

        return jsonify({
            "success": True,
            "message": "Due recurring transactions processed.",
            "generated_count": generated_count
        }), 200

    except Exception:
        return jsonify({
            "success": False,
            "error": "Unable to process recurring transactions."
        }), 500
