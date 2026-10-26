"""
AI BugFixer Pro — application entry point.

Run locally:
    pip install -r requirements.txt
    python app.py

The app works fully out of the box using the built-in static
analysis engine. Set ANTHROPIC_API_KEY (see .env.example) to enable
full AI-powered code review across all supported languages.
"""

from flask import Flask

from config import Config
from database import init_db
from routes.main import bp as main_bp
from routes.auth import bp as auth_bp
from routes.dashboard import bp as dashboard_bp
from routes.api import bp as api_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(api_bp)

    @app.context_processor
    def inject_globals():
        return {"ai_enabled": Config.AI_ENABLED}

    with app.app_context():
        init_db()

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=Config.DEBUG)
