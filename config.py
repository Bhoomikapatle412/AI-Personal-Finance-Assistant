import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Project root directory
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Instance folder path
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")

# Create the instance folder if it doesn't exist
os.makedirs(INSTANCE_DIR, exist_ok=True)


class Config:
    # Flask Configuration
    SECRET_KEY = os.getenv("SECRET_KEY")

    # Database Configuration
    SQLALCHEMY_DATABASE_URI = (
        "sqlite:///" + os.path.join(INSTANCE_DIR, "finance.db")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False