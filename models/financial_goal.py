
from datetime import datetime

from extensions import db


class FinancialGoal(db.Model):
    __tablename__ = "financial_goals"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)

    target_amount = db.Column(
        db.Numeric(10, 2),
        nullable=False
    )

    target_date = db.Column(db.Date, nullable=True)

    is_completed = db.Column(
        db.Boolean,
        default=False,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    user = db.relationship(
        "User",
        back_populates="financial_goals"
    )

    contributions = db.relationship(
        "GoalContribution",
        back_populates="goal",
        cascade="all, delete-orphan",
        lazy=True,
        order_by="GoalContribution.contribution_date.desc()"
    )

    def __repr__(self):
        return f"<FinancialGoal {self.name}>"


class GoalContribution(db.Model):
    __tablename__ = "goal_contributions"

    id = db.Column(db.Integer, primary_key=True)

    goal_id = db.Column(
        db.Integer,
        db.ForeignKey("financial_goals.id"),
        nullable=False,
        index=True
    )

    amount = db.Column(
        db.Numeric(10, 2),
        nullable=False
    )

    note = db.Column(db.String(255), nullable=True)

    contribution_date = db.Column(
        db.Date,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    goal = db.relationship(
        "FinancialGoal",
        back_populates="contributions"
    )

    def __repr__(self):
        return f"<GoalContribution {self.amount} for goal {self.goal_id}>"
