
from datetime import datetime

from flask import (
    Blueprint,
    render_template,
    request,
    jsonify
)

from flask_login import (
    login_required,
    current_user
)

from models import Category
from models.enums import EntryType

from services.transaction_service import search_transactions


transactions_bp = Blueprint(
    "transactions",
    __name__
)


# --------------------------------------------------------
# Categories API
# --------------------------------------------------------
@transactions_bp.route("/transactions/categories", methods=["GET"])
@login_required
def get_categories():
    categories = (
        Category.query
        .filter(
            (Category.is_default.is_(True)) |
            (Category.user_id == current_user.id)
        )
        .order_by(Category.name)
        .all()
    )

    return jsonify([
        {
            "id": category.id,
            "name": category.name
        }
        for category in categories
    ])


# --------------------------------------------------------
# Transactions Page
# --------------------------------------------------------
@transactions_bp.route("/transactions")
@login_required
def transactions():

    search = request.args.get(
        "search",
        ""
    ).strip()

    category_id = request.args.get(
        "category_id",
        ""
    ).strip()

    entry_type = request.args.get(
        "entry_type",
        ""
    ).strip()

    start_date = request.args.get(
        "start_date",
        ""
    ).strip()

    end_date = request.args.get(
        "end_date",
        ""
    ).strip()

    # --------------------------------------------------------
    # Category Filter
    # --------------------------------------------------------

    category_filter = None

    if category_id:
        try:
            category_filter = int(category_id)

        except (ValueError, TypeError):
            category_filter = None

    # --------------------------------------------------------
    # Entry Type Filter
    # --------------------------------------------------------

    entry_type_filter = None

    if entry_type:
        try:
            entry_type_filter = EntryType(entry_type)

        except (ValueError, TypeError):
            entry_type_filter = None

    # --------------------------------------------------------
    # Date Filters
    # --------------------------------------------------------

    parsed_start_date = None
    parsed_end_date = None

    if start_date:
        try:
            parsed_start_date = datetime.strptime(
                start_date,
                "%Y-%m-%d"
            ).date()

        except ValueError:
            parsed_start_date = None

    if end_date:
        try:
            parsed_end_date = datetime.strptime(
                end_date,
                "%Y-%m-%d"
            ).date()

        except ValueError:
            parsed_end_date = None

    # --------------------------------------------------------
    # Search Transactions
    # --------------------------------------------------------

    transaction_list = search_transactions(
        user_id=current_user.id,
        search=search or None,
        category_id=category_filter,
        entry_type=entry_type_filter,
        start_date=parsed_start_date,
        end_date=parsed_end_date
    )

    # --------------------------------------------------------
    # Categories for Transactions Template
    # --------------------------------------------------------

    categories = (
        Category.query
        .filter(
            (Category.is_default.is_(True)) |
            (Category.user_id == current_user.id)
        )
        .order_by(Category.name)
        .all()
    )

    # --------------------------------------------------------
    # Render Transactions Page
    # --------------------------------------------------------

    return render_template(
        "transactions.html",
        transactions=transaction_list,
        categories=categories,
        entry_types=EntryType,
        filters={
            "search": search,
            "category_id": category_id,
            "entry_type": entry_type,
            "start_date": start_date,
            "end_date": end_date
        }
    )
