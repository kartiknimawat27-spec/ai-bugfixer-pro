import time

from flask import Blueprint, render_template, request, redirect, url_for, flash, session

import models

bp = Blueprint("auth", __name__)

# Very small in-memory login throttle: {email: [attempt_timestamps]}
_login_attempts = {}
MAX_ATTEMPTS = 5
LOCKOUT_SECONDS = 300


def _is_locked_out(email):
    attempts = [t for t in _login_attempts.get(email, []) if time.time() - t < LOCKOUT_SECONDS]
    _login_attempts[email] = attempts
    return len(attempts) >= MAX_ATTEMPTS


def _record_attempt(email):
    _login_attempts.setdefault(email, []).append(time.time())


@bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if not name or not email or not password:
            flash("Please fill in all fields.", "error")
            return redirect(url_for("auth.register"))

        if len(password) < 8:
            flash("Password must be at least 8 characters.", "error")
            return redirect(url_for("auth.register"))

        if password != confirm:
            flash("Passwords do not match.", "error")
            return redirect(url_for("auth.register"))

        if models.get_user_by_email(email):
            flash("An account with this email already exists.", "error")
            return redirect(url_for("auth.register"))

        models.create_user(name, email, password)
        flash("Account created successfully. Please sign in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("register.html")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Please enter your email and password.", "error")
            return redirect(url_for("auth.login"))

        if _is_locked_out(email):
            flash("Too many failed attempts. Try again in a few minutes.", "error")
            return redirect(url_for("auth.login"))

        user = models.get_user_by_email(email)

        if user and models.verify_password(user, password):
            session.clear()
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            return redirect(url_for("dashboard.dashboard"))

        _record_attempt(email)
        flash("Invalid email or password.", "error")
        return redirect(url_for("auth.login"))

    return render_template("login.html")


@bp.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("auth.login"))


@bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        user = models.get_user_by_email(email)

        # Always show the same message, whether or not the account
        # exists, so the form can't be used to enumerate registered emails.
        flash(
            "If an account exists for that email, a reset link has been generated.",
            "success",
        )

        if user:
            token = models.create_reset_token(user["id"])
            reset_url = url_for("auth.reset_password", token=token, _external=False)
            # No SMTP server is configured in this project, so the
            # reset link is surfaced directly instead of emailed.
            return render_template(
                "forgot_password.html", demo_reset_url=reset_url
            )

        return redirect(url_for("auth.forgot_password"))

    return render_template("forgot_password.html")


@bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    reset = models.get_valid_reset(token)
    if not reset:
        flash("This reset link is invalid or has expired.", "error")
        return redirect(url_for("auth.forgot_password"))

    if request.method == "POST":
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if len(password) < 8:
            flash("Password must be at least 8 characters.", "error")
            return redirect(url_for("auth.reset_password", token=token))

        if password != confirm:
            flash("Passwords do not match.", "error")
            return redirect(url_for("auth.reset_password", token=token))

        models.update_password(reset["user_id"], password)
        models.consume_reset_token(token)
        flash("Password updated. Please sign in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("reset_password.html", token=token)
