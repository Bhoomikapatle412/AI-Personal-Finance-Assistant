
from flask import Flask

from config import Config
from extensions import db, login_manager, migrate

from models import (
    User,
    Category,
    Ledger,
    FinancialGoal,
    GoalContribution,
    SubscriptionBill,
    BillPayment
)

from routes.home import home_bp
from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from routes.transaction import transaction_bp
from routes.transactions import transactions_bp
from routes.budget import budget_bp
from routes.recurring import recurring_bp
from routes.financial_goals import financial_goals_bp
from routes.subscription_bills import subscription_bills_bp


def create_app():

    app = Flask(__name__)

    app.config.from_object(Config)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    # Login configuration
    login_manager.login_view = "auth.login"

    # Register blueprints
    app.register_blueprint(home_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(transaction_bp)
    app.register_blueprint(transactions_bp)
    app.register_blueprint(budget_bp)
    app.register_blueprint(recurring_bp)
    app.register_blueprint(financial_goals_bp)
    app.register_blueprint(subscription_bills_bp)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
