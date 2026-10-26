from flask import Blueprint, render_template, session
from config import Config

bp = Blueprint("main", __name__)


@bp.route("/")
def home():
    return render_template("index.html", ai_enabled=Config.AI_ENABLED)
