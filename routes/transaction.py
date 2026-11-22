from datetime import datetime

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash
)

from flask_login import login_required, current_user

from models import Category
from models.enums import EntryType, PaymentMethod

from services.transaction_service import create_transaction
from services.gemini_service import GeminiService


transaction_bp = Blueprint(
    "transaction",
    __name__
)


# ============================================================
# HELPERS
# ============================================================

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


def render_manual_transaction_form():
    categories = get_user_categories()

    return render_template(
        "add_transaction.html",
        categories=categories,
        entry_types=EntryType,
        payment_methods=PaymentMethod
    )


# ============================================================
# MANUAL ADD TRANSACTION
# ============================================================

@transaction_bp.route(
    "/transactions/add",
    methods=["GET", "POST"]
)
@login_required
def add_transaction():

    if request.method == "GET":
        return render_manual_transaction_form()

    description = request.form.get(
        "description",
        ""
    ).strip()

    amount_value = request.form.get(
        "amount",
        ""
    ).strip()

    category_id_value = request.form.get(
        "category_id",
        ""
    ).strip()

    entry_type_value = request.form.get(
        "entry_type",
        ""
    ).strip()

    payment_method_value = request.form.get(
        "payment_method",
        ""
    ).strip()

    merchant = request.form.get(
        "merchant",
        ""
    ).strip()

    payment_provider = request.form.get(
        "payment_provider",
        ""
    ).strip()

    transaction_date_value = request.form.get(
        "transaction_date",
        ""
    ).strip()

    notes = request.form.get(
        "notes",
        ""
    ).strip()

    categories = get_user_categories()

    # --------------------------------------------------------
    # Description / amount
    # --------------------------------------------------------

    if not description or not amount_value:
        flash(
            "Description and amount are required.",
            "error"
        )

        return render_template(
            "add_transaction.html",
            categories=categories,
            entry_types=EntryType,
            payment_methods=PaymentMethod
        )

    try:
        amount = float(amount_value)

        if amount <= 0:
            raise ValueError

    except (ValueError, TypeError):

        flash(
            "Please enter a valid amount.",
            "error"
        )

        return render_template(
            "add_transaction.html",
            categories=categories,
            entry_types=EntryType,
            payment_methods=PaymentMethod
        )

    # --------------------------------------------------------
    # Category
    # --------------------------------------------------------

    try:
        category_id = int(category_id_value)

    except (ValueError, TypeError):

        flash(
            "Please select a valid category.",
            "error"
        )

        return render_template(
            "add_transaction.html",
            categories=categories,
            entry_types=EntryType,
            payment_methods=PaymentMethod
        )

    category = Category.query.filter(
        Category.id == category_id,
        (
            Category.is_default.is_(True) |
            (Category.user_id == current_user.id)
        )
    ).first()

    if not category:

        flash(
            "Please select a valid category.",
            "error"
        )

        return render_template(
            "add_transaction.html",
            categories=categories,
            entry_types=EntryType,
            payment_methods=PaymentMethod
        )

    # --------------------------------------------------------
    # Entry type
    # --------------------------------------------------------

    try:
        entry_type = EntryType(entry_type_value)

    except (ValueError, TypeError):

        flash(
            "Please select a valid transaction type.",
            "error"
        )

        return render_template(
            "add_transaction.html",
            categories=categories,
            entry_types=EntryType,
            payment_methods=PaymentMethod
        )

    # --------------------------------------------------------
    # Payment method
    # --------------------------------------------------------

    try:
        payment_method = PaymentMethod(payment_method_value)

    except (ValueError, TypeError):

        flash(
            "Please select a valid payment method.",
            "error"
        )

        return render_template(
            "add_transaction.html",
            categories=categories,
            entry_types=EntryType,
            payment_methods=PaymentMethod
        )

    # --------------------------------------------------------
    # Date
    # --------------------------------------------------------

    parsed_date = None

    if transaction_date_value:

        try:
            parsed_date = datetime.strptime(
                transaction_date_value,
                "%Y-%m-%d"
            ).date()

        except ValueError:

            flash(
                "Please enter a valid date.",
                "error"
            )

            return render_template(
                "add_transaction.html",
                categories=categories,
                entry_types=EntryType,
                payment_methods=PaymentMethod
            )

    # --------------------------------------------------------
    # Create transaction
    # --------------------------------------------------------

    try:

        create_transaction(
            user_id=current_user.id,
            category_id=category.id,
            entry_type=entry_type,
            amount=amount,
            description=description,
            payment_method=payment_method,
            merchant=merchant or None,
            payment_provider=payment_provider or None,
            transaction_date=parsed_date,
            notes=notes or None
        )

    except Exception as exc:

        print("Manual transaction error:", exc)

        flash(
            "Could not save the transaction.",
            "error"
        )

        return render_template(
            "add_transaction.html",
            categories=categories,
            entry_types=EntryType,
            payment_methods=PaymentMethod
        )

    flash(
        "Transaction added successfully!",
        "success"
    )

    return redirect(
        url_for("dashboard.dashboard")
    )


# ============================================================
# AI ADD TRANSACTION
# ============================================================

@transaction_bp.route(
    "/transactions/ai-add",
    methods=["GET", "POST"]
)
@login_required
def ai_add_transaction():

    if request.method == "GET":

        return render_template(
            "ai_transaction.html",
            payment_methods=PaymentMethod
        )

    user_input = request.form.get(
        "transaction_text",
        ""
    ).strip()

    payment_method_value = request.form.get(
        "payment_method",
        ""
    ).strip()

    transaction_date_value = request.form.get(
        "transaction_date",
        ""
    ).strip()

    # --------------------------------------------------------
    # Validate input
    # --------------------------------------------------------

    if not user_input:

        flash(
            "Please describe your transaction.",
            "error"
        )

        return render_template(
            "ai_transaction.html",
            payment_methods=PaymentMethod
        )

    # --------------------------------------------------------
    # Payment method
    # --------------------------------------------------------

    if not payment_method_value:
        payment_method_value = PaymentMethod.OTHER.value

    try:

        payment_method = PaymentMethod(
            payment_method_value
        )

    except (ValueError, TypeError):

        flash(
            "Please select a valid payment method.",
            "error"
        )

        return render_template(
            "ai_transaction.html",
            payment_methods=PaymentMethod
        )

    # --------------------------------------------------------
    # Date
    # --------------------------------------------------------

    parsed_date = None

    if transaction_date_value:

        try:

            parsed_date = datetime.strptime(
                transaction_date_value,
                "%Y-%m-%d"
            ).date()

        except ValueError:

            flash(
                "Invalid transaction date.",
                "error"
            )

            return render_template(
                "ai_transaction.html",
                payment_methods=PaymentMethod
            )

    # --------------------------------------------------------
    # Categories
    # --------------------------------------------------------

    categories = get_user_categories()

    category_names = [
        category.name
        for category in categories
    ]

    if not category_names:

        flash(
            "No transaction categories are available.",
            "error"
        )

        return render_template(
            "ai_transaction.html",
            payment_methods=PaymentMethod
        )

    # --------------------------------------------------------
    # Gemini
    # --------------------------------------------------------

    try:

        gemini = GeminiService()

        result = gemini.classify_transaction(
            user_input=user_input,
            categories=category_names
        )

        result = gemini.validate_transaction_result(
            result=result,
            categories=category_names
        )

    except Exception as exc:

        print("Gemini error:", exc)

        flash(
            "AI could not process the transaction. "
            "Please try again.",
            "error"
        )

        return render_template(
            "ai_transaction.html",
            payment_methods=PaymentMethod
        )

    # --------------------------------------------------------
    # Preview
    # --------------------------------------------------------

    return render_template(
        "ai_transaction_preview.html",
        result=result,
        payment_method=payment_method.value,
        transaction_date=(
            parsed_date.strftime("%Y-%m-%d")
            if parsed_date
            else ""
        )
    )


# ============================================================
# AI CONFIRM TRANSACTION
# ============================================================

@transaction_bp.route(
    "/transactions/ai-confirm",
    methods=["POST"]
)
@login_required
def ai_confirm_transaction():

    description = request.form.get(
        "description",
        ""
    ).strip()

    amount_value = request.form.get(
        "amount",
        ""
    ).strip()

    category_name = request.form.get(
        "category",
        ""
    ).strip()

    entry_type_value = request.form.get(
        "entry_type",
        ""
    ).strip()

    payment_method_value = request.form.get(
        "payment_method",
        PaymentMethod.OTHER.value
    ).strip()

    transaction_date_value = request.form.get(
        "transaction_date",
        ""
    ).strip()

    # --------------------------------------------------------
    # Basic validation
    # --------------------------------------------------------

    if not description or not amount_value or not category_name:

        flash(
            "Transaction information is incomplete.",
            "error"
        )

        return redirect(
            url_for("transaction.ai_add_transaction")
        )

    # --------------------------------------------------------
    # Amount
    # --------------------------------------------------------

    try:

        amount = float(amount_value)

        if amount <= 0:
            raise ValueError

    except (ValueError, TypeError):

        flash(
            "Invalid transaction amount.",
            "error"
        )

        return redirect(
            url_for("transaction.ai_add_transaction")
        )

    # --------------------------------------------------------
    # Category
    # --------------------------------------------------------

    category = Category.query.filter(
        Category.name.ilike(category_name),
        (
            Category.is_default.is_(True) |
            (Category.user_id == current_user.id)
        )
    ).first()

    if not category:

        flash(
            f"Category '{category_name}' was not found.",
            "error"
        )

        return redirect(
            url_for("transaction.ai_add_transaction")
        )

    # --------------------------------------------------------
    # Entry type
    # --------------------------------------------------------

    try:

        entry_type = EntryType(
            entry_type_value
        )

    except (ValueError, TypeError):

        flash(
            "Invalid transaction type returned by AI.",
            "error"
        )

        return redirect(
            url_for("transaction.ai_add_transaction")
        )

    # --------------------------------------------------------
    # Payment method
    # --------------------------------------------------------

    try:

        payment_method = PaymentMethod(
            payment_method_value
        )

    except (ValueError, TypeError):

        flash(
            "Invalid payment method.",
            "error"
        )

        return redirect(
            url_for("transaction.ai_add_transaction")
        )

    # --------------------------------------------------------
    # Date
    # --------------------------------------------------------

    parsed_date = None

    if transaction_date_value:

        try:

            parsed_date = datetime.strptime(
                transaction_date_value,
                "%Y-%m-%d"
            ).date()

        except ValueError:

            flash(
                "Invalid transaction date.",
                "error"
            )

            return redirect(
                url_for("transaction.ai_add_transaction")
            )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    try:

        create_transaction(
            user_id=current_user.id,
            category_id=category.id,
            entry_type=entry_type,
            amount=amount,
            description=description,
            payment_method=payment_method,
            transaction_date=parsed_date
        )

    except Exception as exc:

        print("Transaction save error:", exc)

        flash(
            "Could not save the transaction.",
            "error"
        )

        return redirect(
            url_for("transaction.ai_add_transaction")
        )

    flash(
        "AI transaction added successfully!",
        "success"
    )

    return redirect(
        url_for("dashboard.dashboard")
    )