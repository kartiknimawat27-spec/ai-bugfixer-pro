from functools import wraps

from flask import Blueprint, render_template, session, redirect, url_for, flash

import models

bp = Blueprint("dashboard", __name__)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please sign in first.", "error")
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)
    return wrapped


@bp.route("/dashboard")
@login_required
def dashboard():
    user = models.get_user_by_id(session["user_id"])
    if user is None:
        session.clear()
        return redirect(url_for("auth.login"))

    stats = models.get_stats(user["id"])
    history = models.get_history(user["id"], limit=10)

    return render_template(
        "dashboard.html",
        user=user,
        stats=stats,
        history=history,
    )
