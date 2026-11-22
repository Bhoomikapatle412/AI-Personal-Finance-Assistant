from flask import Blueprint, render_template
from flask_login import login_required, current_user

from services.transaction_service import (
    get_dashboard_summary,
    get_category_expenses,
    get_monthly_income_expenses,
    get_current_month_metrics,
    get_month_over_month_comparison,
    get_financial_insights
)

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/dashboard")
@login_required
def dashboard():
    summary = get_dashboard_summary(current_user.id)
    category_expenses = get_category_expenses(current_user.id)
    monthly_data = get_monthly_income_expenses(current_user.id)
    current_month_metrics = get_current_month_metrics(current_user.id)
    month_comparison = get_month_over_month_comparison(current_user.id)
    financial_insights = get_financial_insights(current_user.id)

    return render_template(
        "dashboard.html",
        user=current_user,
        summary=summary,
        category_expenses=category_expenses,
        monthly_data=monthly_data,
        current_month_metrics=current_month_metrics,
        month_comparison=month_comparison,
        financial_insights=financial_insights
    )