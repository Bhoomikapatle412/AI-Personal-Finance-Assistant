
from datetime import date
from decimal import Decimal, InvalidOperation

from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user

from models import Category
from services.transaction_service import create_budget, get_user_budgets


budget_bp = Blueprint("budget", __name__, url_prefix="/budgets")


# --------------------------------------------------------
# Budget Management Page
# --------------------------------------------------------
@budget_bp.route("/page")
@login_required
def budget_page():
    return render_template("budgets.html")


# --------------------------------------------------------
# Get Monthly Budgets
# --------------------------------------------------------
@budget_bp.route("/", methods=["GET"])
@login_required
def budgets():
    today = date.today()

    month = request.args.get("month", default=today.month, type=int)
    year = request.args.get("year", default=today.year, type=int)

    if not 1 <= month <= 12:
        return jsonify({"error": "Invalid month"}), 400

    budgets = get_user_budgets(current_user.id, month, year)

    return jsonify([
        {
            "id": budget.id,
            "category": budget.category.name,
            "category_id": budget.category_id,
            "amount": float(budget.amount),
            "month": budget.month,
            "year": budget.year
        }
        for budget in budgets
    ])


# --------------------------------------------------------
# Create or Update Budget
# --------------------------------------------------------
@budget_bp.route("/", methods=["POST"])
@login_required
def save_budget():
    data = request.get_json(silent=True)

    if not data:
        return jsonify({"error": "Request body is required"}), 400

    try:
        category_id = int(data.get("category_id"))
        amount = Decimal(str(data.get("amount")))
        month = int(data.get("month"))
        year = int(data.get("year"))

    except (TypeError, ValueError, InvalidOperation):
        return jsonify({"error": "Invalid budget data"}), 400

    if not amount.is_finite() or amount <= 0:
        return jsonify({"error": "Budget amount must be greater than zero"}), 400

    if not 1 <= month <= 12:
        return jsonify({"error": "Invalid month"}), 400

    if not 2000 <= year <= 2100:
        return jsonify({"error": "Invalid year"}), 400

    # Allow default categories or categories owned by the current user
    category = Category.query.filter(
        Category.id == category_id,
        (
            Category.is_default.is_(True) |
            (Category.user_id == current_user.id)
        )
    ).first()

    if not category:
        return jsonify({"error": "Category not found"}), 404

    try:
        budget = create_budget(
            user_id=current_user.id,
            category_id=category_id,
            amount=amount,
            month=month,
            year=year
        )

        return jsonify({
            "message": "Budget saved successfully",
            "budget_id": budget.id
        }), 201

    except Exception as e:
        print("Budget save error:", e)
        return jsonify({"error": "Unable to save budget"}), 500
