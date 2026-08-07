from flask import Flask

from config import Config
from extensions import db, migrate

# Import models so Flask-Migrate can discover them
from models import User

from routes.home import home_bp


def create_app():
    app = Flask(__name__)

    app.config.from_object(Config)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)

    # Register blueprints
    app.register_blueprint(home_bp)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)