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
# HELPER
# ============================================================

def get_available_categories():
    """
    Get default categories and categories
    created by the current user.
    """

    return Category.query.filter(
        (Category.is_default == True) |
        (Category.user_id == current_user.id)
    ).order_by(
        Category.name
    ).all()


# ============================================================
# MANUAL TRANSACTION
# ============================================================

@transaction_bp.route(
    "/transactions/add",
    methods=["GET", "POST"]
)
@login_required
def add_transaction():

    categories = get_available_categories()

    # --------------------------------------------------------
    # GET
    # --------------------------------------------------------

    if request.method == "GET":

        return render_template(
            "add_transaction.html",
            categories=categories,
            entry_types=EntryType,
            payment_methods=PaymentMethod
        )

    # --------------------------------------------------------
    # POST
    # --------------------------------------------------------

    description = request.form.get(
        "description",
        ""
    ).strip()

    amount = request.form.get(
        "amount",
        ""
    ).strip()

    category_id = request.form.get(
        "category_id"
    )

    entry_type = request.form.get(
        "entry_type"
    )

    payment_method = request.form.get(
        "payment_method"
    )

    merchant = request.form.get(
        "merchant",
        ""
    ).strip()

    payment_provider = request.form.get(
        "payment_provider",
        ""
    ).strip()

    transaction_date = request.form.get(
        "transaction_date"
    )

    notes = request.form.get(
        "notes",
        ""
    ).strip()

    # --------------------------------------------------------
    # Required fields
    # --------------------------------------------------------

    if not description or not amount or not category_id:

        flash(
            "Please fill in all required fields.",
            "error"
        )

        return render_template(
            "add_transaction.html",
            categories=categories,
            entry_types=EntryType,
            payment_methods=PaymentMethod
        )

    # --------------------------------------------------------
    # Amount
    # --------------------------------------------------------

    try:

        amount = float(amount)

    except ValueError:

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

    if amount <= 0:

        flash(
            "Amount must be greater than zero.",
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

        category_id = int(category_id)

    except ValueError:

        flash(
            "Invalid category.",
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
            (Category.is_default == True) |
            (Category.user_id == current_user.id)
        )
    ).first()

    if not category:

        flash(
            "Invalid category.",
            "error"
        )

        return render_template(
            "add_transaction.html",
            categories=categories,
            entry_types=EntryType,
            payment_methods=PaymentMethod
        )

    # --------------------------------------------------------
    # Enums
    # --------------------------------------------------------

    try:

        selected_entry_type = EntryType(
            entry_type
        )

        selected_payment_method = PaymentMethod(
            payment_method
        )

    except ValueError:

        flash(
            "Invalid transaction type or payment method.",
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

    if transaction_date:

        try:

            parsed_date = datetime.strptime(
                transaction_date,
                "%Y-%m-%d"
            ).date()

        except ValueError:

            flash(
                "Invalid transaction date.",
                "error"
            )

            return render_template(
                "add_transaction.html",
                categories=categories,
                entry_types=EntryType,
                payment_methods=PaymentMethod
            )

    # --------------------------------------------------------
    # Save transaction
    # --------------------------------------------------------

    create_transaction(
        user_id=current_user.id,
        category_id=category.id,
        entry_type=selected_entry_type,
        amount=amount,
        description=description,
        payment_method=selected_payment_method,
        merchant=merchant or None,
        payment_provider=payment_provider or None,
        transaction_date=parsed_date,
        notes=notes or None
    )

    flash(
        "Transaction added successfully.",
        "success"
    )

    return redirect(
        url_for("dashboard.dashboard")
    )


# ============================================================
# AI TRANSACTION
# ============================================================

@transaction_bp.route(
    "/transactions/ai-add",
    methods=["GET", "POST"]
)
@login_required
def ai_add_transaction():

    categories = get_available_categories()

    # --------------------------------------------------------
    # GET
    # Show the AI transaction form
    # --------------------------------------------------------

    if request.method == "GET":

        return render_template(
            "ai_transaction.html",
            payment_methods=PaymentMethod
        )

    # --------------------------------------------------------
    # POST
    # --------------------------------------------------------

    user_input = request.form.get(
        "transaction_text",
        ""
    ).strip()

    payment_method = request.form.get(
        "payment_method"
    )

    transaction_date = request.form.get(
        "transaction_date"
    )

    # --------------------------------------------------------
    # Validate user input
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
    # Validate payment method
    # --------------------------------------------------------

    try:

        selected_payment_method = PaymentMethod(
            payment_method
        )

    except ValueError:

        flash(
            "Please select a valid payment method.",
            "error"
        )

        return render_template(
            "ai_transaction.html",
            payment_methods=PaymentMethod
        )

    # --------------------------------------------------------
    # Get categories from database
    # --------------------------------------------------------

    category_names = [
        category.name
        for category in categories
    ]

    # --------------------------------------------------------
    # Gemini
    # --------------------------------------------------------

    try:

        gemini = GeminiService()

        result = gemini.classify_transaction(
            user_input,
            category_names
        )

        result = gemini.validate_transaction_result(
            result,
            category_names
        )

    except Exception as error:

        print(
            f"Gemini transaction error: {error}"
        )

        flash(
            "Unable to understand the transaction. "
            "Please try again.",
            "error"
        )

        return render_template(
            "ai_transaction.html",
            payment_methods=PaymentMethod
        )

    # --------------------------------------------------------
    # Find category in database
    # --------------------------------------------------------

    category = Category.query.filter(
        Category.name == result["category"],
        (
            (Category.is_default == True) |
            (Category.user_id == current_user.id)
        )
    ).first()

    if not category:

        flash(
            "The AI selected an unavailable category.",
            "error"
        )

        return render_template(
            "ai_transaction.html",
            payment_methods=PaymentMethod
        )

    # --------------------------------------------------------
    # Parse date
    # --------------------------------------------------------

    parsed_date = None

    if transaction_date:

        try:

            parsed_date = datetime.strptime(
                transaction_date,
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
    # IMPORTANT:
    # Do NOT save the transaction yet.
    #
    # Show Gemini's result to the user first.
    # --------------------------------------------------------

    return render_template(
        "ai_transaction_preview.html",
        result=result,
        category=category,
        payment_method=selected_payment_method,
        transaction_date=parsed_date,
        original_text=user_input
    )


# ============================================================
# CONFIRM AI TRANSACTION
# ============================================================

@transaction_bp.route(
    "/transactions/ai-confirm",
    methods=["POST"]
)
@login_required
def confirm_ai_transaction():

    description = request.form.get(
        "description",
        ""
    ).strip()

    amount = request.form.get(
        "amount",
        ""
    ).strip()

    category_id = request.form.get(
        "category_id"
    )

    entry_type = request.form.get(
        "entry_type"
    )

    payment_method = request.form.get(
        "payment_method"
    )

    transaction_date = request.form.get(
        "transaction_date"
    )

    # --------------------------------------------------------
    # Required fields
    # --------------------------------------------------------

    if (
        not description
        or not amount
        or not category_id
        or not entry_type
        or not payment_method
    ):

        flash(
            "Transaction information is incomplete.",
            "error"
        )

        return redirect(
            url_for(
                "transaction.ai_add_transaction"
            )
        )

    # --------------------------------------------------------
    # Amount
    # --------------------------------------------------------

    try:

        amount = float(amount)

        if amount <= 0:
            raise ValueError

    except ValueError:

        flash(
            "Invalid transaction amount.",
            "error"
        )

        return redirect(
            url_for(
                "transaction.ai_add_transaction"
            )
        )

    # --------------------------------------------------------
    # Category
    # --------------------------------------------------------

    try:

        category_id = int(category_id)

    except ValueError:

        flash(
            "Invalid category.",
            "error"
        )

        return redirect(
            url_for(
                "transaction.ai_add_transaction"
            )
        )

    category = Category.query.filter(
        Category.id == category_id,
        (
            (Category.is_default == True) |
            (Category.user_id == current_user.id)
        )
    ).first()

    if not category:

        flash(
            "Invalid category.",
            "error"
        )

        return redirect(
            url_for(
                "transaction.ai_add_transaction"
            )
        )

    # --------------------------------------------------------
    # Enums
    # --------------------------------------------------------

    try:

        selected_entry_type = EntryType(
            entry_type
        )

        selected_payment_method = PaymentMethod(
            payment_method
        )

    except ValueError:

        flash(
            "Invalid transaction type or payment method.",
            "error"
        )

        return redirect(
            url_for(
                "transaction.ai_add_transaction"
            )
        )

    # --------------------------------------------------------
    # Date
    # --------------------------------------------------------

    parsed_date = None

    if transaction_date:

        try:

            parsed_date = datetime.strptime(
                transaction_date,
                "%Y-%m-%d"
            ).date()

        except ValueError:

            flash(
                "Invalid transaction date.",
                "error"
            )

            return redirect(
                url_for(
                    "transaction.ai_add_transaction"
                )
            )

    # --------------------------------------------------------
    # SAVE TO DATABASE
    # --------------------------------------------------------

    create_transaction(
        user_id=current_user.id,
        category_id=category.id,
        entry_type=selected_entry_type,
        amount=amount,
        description=description,
        payment_method=selected_payment_method,
        transaction_date=parsed_date
    )

    flash(
        "AI transaction added successfully.",
        "success"
    )

    return redirect(
        url_for(
            "dashboard.dashboard"
        )
    )