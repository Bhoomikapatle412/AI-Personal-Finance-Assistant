
from datetime import date
from decimal import InvalidOperation

from flask import (
    Blueprint,
    jsonify,
    render_template,
    request
)
from flask_login import login_required, current_user

from models import Category
from models.enums import PaymentMethod

from services.subscription_bill_service import (
    create_subscription_bill,
    get_subscription_bill,
    get_user_subscription_bills,
    update_subscription_bill,
    get_subscription_bill_status,
    get_upcoming_and_overdue_bills,
    record_bill_payment,
    get_bill_payment_history,
    get_user_bill_payments,
    toggle_subscription_bill,
    delete_subscription_bill,
)


subscription_bills_bp = Blueprint(
    "subscription_bills",
    __name__,
    url_prefix="/subscription-bills"
)


# ============================================================
# HELPERS
# ============================================================

def parse_date(value, field_name, required=False):
    if value is None or value == "":
        if required:
            raise ValueError(f"{field_name} is required.")
        return None

    if not isinstance(value, str):
        raise ValueError(
            f"Invalid {field_name}. Use YYYY-MM-DD format."
        )

    try:
        return date.fromisoformat(value)

    except ValueError:
        raise ValueError(
            f"Invalid {field_name}. Use YYYY-MM-DD format."
        )


def get_user_categories():
    return (
        Category.query
        .filter(
            (Category.is_default.is_(True)) |
            (Category.user_id == current_user.id)
        )
        .order_by(Category.name)
        .all()
    )


def bill_to_dict(bill):
    return {
        "id": bill.id,
        "name": bill.name,
        "description": bill.description,
        "item_type": bill.item_type,
        "expected_amount": float(bill.expected_amount),
        "frequency": bill.frequency,
        "category_id": bill.category_id,
        "category": bill.category.name if bill.category else None,
        "start_date": bill.start_date.isoformat(),
        "next_due_date": bill.next_due_date.isoformat(),
        "end_date": (
            bill.end_date.isoformat()
            if bill.end_date else None
        ),
        "reminder_days": bill.reminder_days,
        "is_active": bill.is_active,
        "status": get_subscription_bill_status(bill),
        "created_at": (
            bill.created_at.isoformat()
            if bill.created_at else None
        ),
        "updated_at": (
            bill.updated_at.isoformat()
            if bill.updated_at else None
        ),
    }


def payment_to_dict(payment):
    return {
        "id": payment.id,
        "subscription_bill_id": payment.subscription_bill_id,
        "amount": float(payment.amount),
        "due_date": payment.due_date.isoformat(),
        "payment_date": payment.payment_date.isoformat(),
        "payment_method": payment.payment_method.value,
        "ledger_id": payment.ledger_id,
        "notes": payment.notes,
        "created_at": (
            payment.created_at.isoformat()
            if payment.created_at else None
        ),
    }


# ============================================================
# SUBSCRIPTION & BILL MANAGER PAGE
# ============================================================

@subscription_bills_bp.route("/page", methods=["GET"])
@login_required
def subscription_bills_page():

    bills = get_user_subscription_bills(current_user.id)

    return render_template(
        "subscription_bills.html",
        bills=[
            bill_to_dict(bill)
            for bill in bills
        ],
        categories=get_user_categories(),
        payment_methods=PaymentMethod
    )


# ============================================================
# GET ALL SUBSCRIPTIONS AND BILLS
# ============================================================

@subscription_bills_bp.route("/", methods=["GET"])
@login_required
def list_subscription_bills():

    item_type = request.args.get("item_type")

    try:
        bills = get_user_subscription_bills(
            user_id=current_user.id,
            item_type=item_type
        )

        return jsonify({
            "success": True,
            "count": len(bills),
            "bills": [
                bill_to_dict(bill)
                for bill in bills
            ]
        }), 200

    except ValueError as error:
        return jsonify({
            "success": False,
            "error": str(error)
        }), 400


# ============================================================
# CREATE SUBSCRIPTION / BILL
# ============================================================

@subscription_bills_bp.route("/", methods=["POST"])
@login_required
def create_bill():

    data = request.get_json(silent=True) or {}

    try:
        category_id = int(data.get("category_id"))

        start_date = parse_date(
            data.get("start_date"),
            "start date",
            required=True
        )

        end_date = parse_date(
            data.get("end_date"),
            "end date"
        )

        bill = create_subscription_bill(
            user_id=current_user.id,
            category_id=category_id,
            name=data.get("name"),
            item_type=data.get("item_type"),
            expected_amount=data.get("expected_amount"),
            frequency=data.get("frequency"),
            start_date=start_date,
            description=data.get("description"),
            end_date=end_date,
            reminder_days=data.get("reminder_days", 3)
        )

        return jsonify({
            "success": True,
            "message": "Subscription or bill created successfully.",
            "bill": bill_to_dict(bill)
        }), 201

    except (ValueError, TypeError, InvalidOperation) as error:
        return jsonify({
            "success": False,
            "error": str(error)
        }), 400


# ============================================================
# GET SINGLE SUBSCRIPTION / BILL
# ============================================================

@subscription_bills_bp.route("/<int:bill_id>", methods=["GET"])
@login_required
def get_bill_details(bill_id):

    bill = get_subscription_bill(
        current_user.id,
        bill_id
    )

    if not bill:
        return jsonify({
            "success": False,
            "error": "Subscription or bill not found."
        }), 404

    history = get_bill_payment_history(
        current_user.id,
        bill_id
    )

    return jsonify({
        "success": True,
        "bill": bill_to_dict(bill),
        "payments": [
            payment_to_dict(payment)
            for payment in history
        ]
    }), 200


# ============================================================
# UPDATE SUBSCRIPTION / BILL
# ============================================================

@subscription_bills_bp.route("/<int:bill_id>", methods=["PUT"])
@login_required
def edit_bill(bill_id):

    bill = get_subscription_bill(
        current_user.id,
        bill_id
    )

    if not bill:
        return jsonify({
            "success": False,
            "error": "Subscription or bill not found."
        }), 404

    data = request.get_json(silent=True) or {}

    updates = {}

    try:
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

        for field in allowed_fields:
            if field not in data:
                continue

            value = data[field]

            if field in {"start_date", "next_due_date", "end_date"}:
                value = parse_date(value, field.replace("_", " "))

            elif field == "category_id":
                value = int(value)

            updates[field] = value

        updated_bill = update_subscription_bill(
            current_user.id,
            bill_id,
            **updates
        )

        return jsonify({
            "success": True,
            "message": "Subscription or bill updated successfully.",
            "bill": bill_to_dict(updated_bill)
        }), 200

    except (ValueError, TypeError, InvalidOperation) as error:
        return jsonify({
            "success": False,
            "error": str(error)
        }), 400


# ============================================================
# UPCOMING AND OVERDUE PAYMENTS
# ============================================================

@subscription_bills_bp.route("/reminders", methods=["GET"])
@login_required
def bill_reminders():

    reminders = get_upcoming_and_overdue_bills(
        current_user.id
    )

    return jsonify({
        "success": True,
        "count": len(reminders),
        "reminders": [
            {
                "bill": bill_to_dict(item["bill"]),
                "status": item["status"],
                "days_until_due": item["days_until_due"]
            }
            for item in reminders
        ]
    }), 200


# ============================================================
# RECORD PAYMENT
# ============================================================

@subscription_bills_bp.route(
    "/<int:bill_id>/payments",
    methods=["POST"]
)
@login_required
def pay_bill(bill_id):

    data = request.get_json(silent=True) or {}

    try:
        payment_date = parse_date(
            data.get("payment_date"),
            "payment date",
            required=True
        )

        due_date = parse_date(
            data.get("due_date"),
            "due date",
            required=True
        )

        payment = record_bill_payment(
            user_id=current_user.id,
            bill_id=bill_id,
            amount=data.get("amount"),
            payment_date=payment_date,
            payment_method=data.get("payment_method"),
            due_date=due_date,
            notes=data.get("notes")
        )

        bill = get_subscription_bill(
            current_user.id,
            bill_id
        )

        return jsonify({
            "success": True,
            "message": "Payment recorded and ledger expense created successfully.",
            "payment": payment_to_dict(payment),
            "bill": bill_to_dict(bill)
        }), 201

    except (ValueError, TypeError, InvalidOperation) as error:
        return jsonify({
            "success": False,
            "error": str(error)
        }), 400


# ============================================================
# GET PAYMENT HISTORY FOR A BILL
# ============================================================

@subscription_bills_bp.route(
    "/<int:bill_id>/payments",
    methods=["GET"]
)
@login_required
def bill_payment_history(bill_id):

    history = get_bill_payment_history(
        current_user.id,
        bill_id
    )

    if history is None:
        return jsonify({
            "success": False,
            "error": "Subscription or bill not found."
        }), 404

    return jsonify({
        "success": True,
        "count": len(history),
        "payments": [
            payment_to_dict(payment)
            for payment in history
        ]
    }), 200


# ============================================================
# GET ALL USER PAYMENTS
# ============================================================

@subscription_bills_bp.route(
    "/payments/history",
    methods=["GET"]
)
@login_required
def all_payment_history():

    payments = get_user_bill_payments(current_user.id)

    return jsonify({
        "success": True,
        "count": len(payments),
        "payments": [
            payment_to_dict(payment)
            for payment in payments
        ]
    }), 200


# ============================================================
# PAUSE / RESUME SUBSCRIPTION OR BILL
# ============================================================

@subscription_bills_bp.route(
    "/<int:bill_id>/status",
    methods=["PATCH"]
)
@login_required
def change_bill_status(bill_id):

    data = request.get_json(silent=True) or {}

    if "is_active" not in data or not isinstance(data["is_active"], bool):
        return jsonify({
            "success": False,
            "error": "is_active must be true or false."
        }), 400

    try:
        bill = toggle_subscription_bill(
            current_user.id,
            bill_id,
            data["is_active"]
        )

        if not bill:
            return jsonify({
                "success": False,
                "error": "Subscription or bill not found."
            }), 404

        return jsonify({
            "success": True,
            "message": (
                "Subscription or bill resumed successfully."
                if bill.is_active
                else "Subscription or bill paused successfully."
            ),
            "bill": bill_to_dict(bill)
        }), 200

    except ValueError as error:
        return jsonify({
            "success": False,
            "error": str(error)
        }), 400


# ============================================================
# DELETE SUBSCRIPTION / BILL
# ============================================================

@subscription_bills_bp.route(
    "/<int:bill_id>",
    methods=["DELETE"]
)
@login_required
def remove_bill(bill_id):

    try:
        deleted = delete_subscription_bill(
            current_user.id,
            bill_id
        )

        if not deleted:
            return jsonify({
                "success": False,
                "error": "Subscription or bill not found."
            }), 404

        return jsonify({
            "success": True,
            "message": "Subscription or bill deleted successfully."
        }), 200

    except ValueError as error:
        return jsonify({
            "success": False,
            "error": str(error)
        }), 400
