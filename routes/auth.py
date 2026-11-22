from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash

from extensions import db
from models import User


auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not full_name or not email or not password:
            flash("All fields are required.", "error")
            return render_template("register.html")

        existing_user = User.query.filter_by(email=email).first()

        if existing_user:
            flash(
                "An account with this email already exists.",
                "error"
            )
            return render_template("register.html")

        user = User(
            full_name=full_name,
            email=email,
            password_hash=generate_password_hash(password)
        )

        try:
            db.session.add(user)
            db.session.commit()

        except Exception:
            db.session.rollback()

            flash(
                "Could not create your account. Please try again.",
                "error"
            )

            return render_template("register.html")

        flash(
            "Account created successfully. You can now log in.",
            "success"
        )

        return redirect(url_for("auth.login"))

    return render_template("register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            flash(
                "Email and password are required.",
                "error"
            )
            return render_template("login.html")

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(
            user.password_hash,
            password
        ):
            login_user(user)

            return redirect(
                url_for("dashboard.dashboard")
            )

        flash(
            "Invalid email or password.",
            "error"
        )

    return render_template("login.html")


@auth_bp.route("/logout")
@login_required
def logout():

    logout_user()

    flash(
        "You have been logged out.",
        "success"
    )

    return redirect(
        url_for("home.home")
    )