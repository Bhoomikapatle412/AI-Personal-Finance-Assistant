from datetime import date

from flask import Blueprint, render_template
from flask_login import login_required, current_user

from services.transaction_service import (
    get_dashboard_summary,
    get_category_expenses,
    get_monthly_income_expenses,
    get_current_month_metrics,
    get_month_over_month_comparison,
    get_financial_insights,
    get_budget_overview
)

from services.anomaly_detection_service import get_user_anomalies


dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/dashboard")
@login_required
def dashboard():
    today = date.today()

    summary = get_dashboard_summary(current_user.id)
    category_expenses = get_category_expenses(current_user.id)
    monthly_data = get_monthly_income_expenses(current_user.id)
    current_month_metrics = get_current_month_metrics(current_user.id)
    month_comparison = get_month_over_month_comparison(current_user.id)
    financial_insights = get_financial_insights(current_user.id)

    budget_overview = get_budget_overview(
        current_user.id,
        today.month,
        today.year
    )

    spending_anomalies = get_user_anomalies(current_user.id)

    return render_template(
        "dashboard.html",
        user=current_user,
        summary=summary,
        category_expenses=category_expenses,
        monthly_data=monthly_data,
        current_month_metrics=current_month_metrics,
        month_comparison=month_comparison,
        financial_insights=financial_insights,
        budget_overview=budget_overview,
        spending_anomalies=spending_anomalies
    )