
from datetime import date

from flask import Blueprint, render_template, request, abort
from flask_login import login_required, current_user

from services.financial_report_service import (
    get_financial_summary,
    get_income_expense_trend,
    get_category_expense_breakdown,
    get_payment_method_breakdown,
    get_budget_vs_actual
)


financial_reports_bp = Blueprint(
    "financial_reports",
    __name__,
    url_prefix="/reports"
)


# --------------------------------------------------------
# Financial Reports Page
# --------------------------------------------------------
@financial_reports_bp.route("/", methods=["GET"])
@login_required
def financial_reports_page():

    today = date.today()

    # Default reporting period: current month to today
    default_start_date = date(today.year, today.month, 1)

    start_date_value = request.args.get(
        "start_date",
        default_start_date.isoformat()
    )

    end_date_value = request.args.get(
        "end_date",
        today.isoformat()
    )

    group_by = request.args.get(
        "group_by",
        "monthly"
    )

    # Validate reporting frequency
    allowed_groupings = {
        "daily",
        "monthly",
        "quarterly",
        "yearly"
    }

    if group_by not in allowed_groupings:
        abort(400, description="Invalid reporting frequency.")

    # Validate dates
    try:
        start_date = date.fromisoformat(start_date_value)
        end_date = date.fromisoformat(end_date_value)

    except (TypeError, ValueError):
        abort(400, description="Invalid date format. Use YYYY-MM-DD.")

    if start_date > end_date:
        abort(
            400,
            description="Start date cannot be after end date."
        )

    # Generate financial reports
    summary = get_financial_summary(
        current_user.id,
        start_date,
        end_date
    )

    income_expense_trend = get_income_expense_trend(
        current_user.id,
        start_date,
        end_date,
        group_by=group_by
    )

    category_breakdown = get_category_expense_breakdown(
        current_user.id,
        start_date,
        end_date
    )

    payment_method_breakdown = get_payment_method_breakdown(
        current_user.id,
        start_date,
        end_date
    )

    budget_comparison = get_budget_vs_actual(
        current_user.id,
        start_date,
        end_date
    )

    return render_template(
        "financial_reports.html",
        user=current_user,
        summary=summary,
        income_expense_trend=income_expense_trend,
        category_breakdown=category_breakdown,
        payment_method_breakdown=payment_method_breakdown,
        budget_comparison=budget_comparison,
        start_date=start_date,
        end_date=end_date,
        group_by=group_by
    )
