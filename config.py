"""
Application configuration.

Values are read from environment variables (see .env.example).
Nothing sensitive is hard-coded here.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-key-change-me")
    DEBUG = os.environ.get("FLASK_DEBUG", "False").lower() == "true"

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATABASE_PATH = os.path.join(BASE_DIR, "database", "app.db")
    REPORTS_DIR = os.path.join(BASE_DIR, "reports")

    ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5")

    AI_ENABLED = bool(ANTHROPIC_API_KEY)

    SUPPORTED_LANGUAGES = [
        "Python", "JavaScript", "TypeScript", "Java",
        "C", "C++", "C#", "Go", "PHP", "Ruby",
    ]

    # Basic login throttling
    MAX_LOGIN_ATTEMPTS = 5
    LOGIN_LOCKOUT_SECONDS = 300
