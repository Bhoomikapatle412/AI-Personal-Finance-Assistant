
from datetime import date
from decimal import InvalidOperation

from flask import (
    Blueprint,
    request,
    jsonify,
    render_template
)
from flask_login import login_required, current_user

from services.financial_goal_service import (
    create_financial_goal,
    get_user_goals,
    get_goal_by_id,
    get_goal_progress,
    add_goal_contribution,
    update_financial_goal,
    delete_financial_goal,
)


financial_goals_bp = Blueprint(
    "financial_goals",
    __name__,
    url_prefix="/financial-goals"
)


# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------

def parse_date(value, field_name):
    if value is None or value == "":
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


def goal_to_dict(goal):
    progress = get_goal_progress(goal)

    return {
        "id": goal.id,
        "name": goal.name,
        "description": goal.description,
        "target_amount": float(progress["target_amount"]),
        "saved_amount": float(progress["saved_amount"]),
        "remaining_amount": float(progress["remaining_amount"]),
        "progress_percentage": progress["progress_percentage"],
        "target_date": (
            goal.target_date.isoformat()
            if goal.target_date else None
        ),
        "monthly_savings_required": (
            float(progress["monthly_savings_required"])
            if progress["monthly_savings_required"] is not None
            else None
        ),
        "is_completed": progress["is_completed"],
        "is_overdue": progress["is_overdue"],
        "created_at": (
            goal.created_at.isoformat()
            if goal.created_at else None
        ),
        "updated_at": (
            goal.updated_at.isoformat()
            if goal.updated_at else None
        ),
    }


def contribution_to_dict(contribution):
    return {
        "id": contribution.id,
        "goal_id": contribution.goal_id,
        "amount": float(contribution.amount),
        "note": contribution.note,
        "contribution_date": (
            contribution.contribution_date.isoformat()
            if contribution.contribution_date else None
        ),
        "created_at": (
            contribution.created_at.isoformat()
            if contribution.created_at else None
        ),
    }


# ---------------------------------------------------------
# FINANCIAL GOALS PAGE
# ---------------------------------------------------------

@financial_goals_bp.route("/page", methods=["GET"])
@login_required
def financial_goals_page():

    goals = get_user_goals(current_user.id)

    return render_template(
        "financial_goals.html",
        goals=[
            goal_to_dict(goal)
            for goal in goals
        ]
    )


# ---------------------------------------------------------
# GET ALL FINANCIAL GOALS
# ---------------------------------------------------------

@financial_goals_bp.route("/", methods=["GET"])
@login_required
def list_financial_goals():

    goals = get_user_goals(current_user.id)

    return jsonify({
        "success": True,
        "count": len(goals),
        "goals": [
            goal_to_dict(goal)
            for goal in goals
        ]
    }), 200


# ---------------------------------------------------------
# CREATE FINANCIAL GOAL
# ---------------------------------------------------------

@financial_goals_bp.route("/", methods=["POST"])
@login_required
def create_goal():

    data = request.get_json(silent=True) or {}

    try:
        target_date = parse_date(
            data.get("target_date"),
            "target date"
        )

        goal = create_financial_goal(
            user_id=current_user.id,
            name=data.get("name"),
            description=data.get("description"),
            target_amount=data.get("target_amount"),
            target_date=target_date
        )

        return jsonify({
            "success": True,
            "message": "Financial goal created successfully.",
            "goal": goal_to_dict(goal)
        }), 201

    except (ValueError, TypeError, InvalidOperation) as error:

        return jsonify({
            "success": False,
            "error": str(error)
        }), 400


# ---------------------------------------------------------
# GET SINGLE FINANCIAL GOAL
# ---------------------------------------------------------

@financial_goals_bp.route("/<int:goal_id>", methods=["GET"])
@login_required
def get_financial_goal(goal_id):

    goal = get_goal_by_id(
        current_user.id,
        goal_id
    )

    if not goal:
        return jsonify({
            "success": False,
            "error": "Financial goal not found."
        }), 404

    return jsonify({
        "success": True,
        "goal": goal_to_dict(goal),
        "contributions": [
            contribution_to_dict(item)
            for item in goal.contributions
        ]
    }), 200


# ---------------------------------------------------------
# UPDATE FINANCIAL GOAL
# ---------------------------------------------------------

@financial_goals_bp.route("/<int:goal_id>", methods=["PUT"])
@login_required
def edit_financial_goal(goal_id):

    goal = get_goal_by_id(
        current_user.id,
        goal_id
    )

    if not goal:
        return jsonify({
            "success": False,
            "error": "Financial goal not found."
        }), 404

    data = request.get_json(silent=True) or {}

    updates = {}

    try:
        if "name" in data:
            updates["name"] = data["name"]

        if "description" in data:
            updates["description"] = data["description"]

        if "target_amount" in data:
            updates["target_amount"] = data["target_amount"]

        if "target_date" in data:
            updates["target_date"] = parse_date(
                data["target_date"],
                "target date"
            )

        updated_goal = update_financial_goal(
            current_user.id,
            goal_id,
            **updates
        )

        return jsonify({
            "success": True,
            "message": "Financial goal updated successfully.",
            "goal": goal_to_dict(updated_goal)
        }), 200

    except (ValueError, TypeError, InvalidOperation) as error:

        return jsonify({
            "success": False,
            "error": str(error)
        }), 400


# ---------------------------------------------------------
# ADD GOAL CONTRIBUTION
# ---------------------------------------------------------

@financial_goals_bp.route(
    "/<int:goal_id>/contributions",
    methods=["POST"]
)
@login_required
def add_contribution(goal_id):

    data = request.get_json(silent=True) or {}

    try:
        contribution_date = parse_date(
            data.get("contribution_date"),
            "contribution date"
        )

        contribution = add_goal_contribution(
            user_id=current_user.id,
            goal_id=goal_id,
            amount=data.get("amount"),
            note=data.get("note"),
            contribution_date=contribution_date
        )

        goal = get_goal_by_id(
            current_user.id,
            goal_id
        )

        return jsonify({
            "success": True,
            "message": "Contribution added successfully.",
            "contribution": contribution_to_dict(contribution),
            "goal": goal_to_dict(goal)
        }), 201

    except (ValueError, TypeError, InvalidOperation) as error:

        return jsonify({
            "success": False,
            "error": str(error)
        }), 400


# ---------------------------------------------------------
# DELETE FINANCIAL GOAL
# ---------------------------------------------------------

@financial_goals_bp.route(
    "/<int:goal_id>",
    methods=["DELETE"]
)
@login_required
def remove_financial_goal(goal_id):

    goal = get_goal_by_id(
        current_user.id,
        goal_id
    )

    if not goal:
        return jsonify({
            "success": False,
            "error": "Financial goal not found."
        }), 404

    try:
        deleted = delete_financial_goal(
            current_user.id,
            goal_id
        )

        if not deleted:
            return jsonify({
                "success": False,
                "error": "Financial goal not found."
            }), 404

        return jsonify({
            "success": True,
            "message": "Financial goal deleted successfully."
        }), 200

    except ValueError as error:

        return jsonify({
            "success": False,
            "error": str(error)
        }), 404

    except Exception:

        return jsonify({
            "success": False,
            "error": "Unable to delete financial goal."
        }), 500
