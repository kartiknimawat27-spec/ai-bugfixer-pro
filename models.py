"""
Data-access helpers. Thin wrappers around SQL so routes stay readable.
"""

import secrets
from datetime import datetime, timedelta

from werkzeug.security import generate_password_hash, check_password_hash

from database import get_db


# ------------------------------------------------------------------ users --

def create_user(name, email, password):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, generate_password_hash(password)),
        )


def get_user_by_email(email):
    with get_db() as conn:
        return conn.execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ).fetchone()


def get_user_by_id(user_id):
    with get_db() as conn:
        return conn.execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        ).fetchone()


def verify_password(user_row, password):
    return check_password_hash(user_row["password_hash"], password)


def update_password(user_id, new_password):
    with get_db() as conn:
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (generate_password_hash(new_password), user_id),
        )


# --------------------------------------------------------- password resets --

def create_reset_token(user_id, ttl_minutes=30):
    token = secrets.token_urlsafe(32)
    expires_at = (datetime.utcnow() + timedelta(minutes=ttl_minutes)).isoformat()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO password_resets (user_id, token, expires_at) "
            "VALUES (?, ?, ?)",
            (user_id, token, expires_at),
        )
    return token


def get_valid_reset(token):
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM password_resets WHERE token = ? AND used = 0",
            (token,),
        ).fetchone()
    if not row:
        return None
    if datetime.fromisoformat(row["expires_at"]) < datetime.utcnow():
        return None
    return row


def consume_reset_token(token):
    with get_db() as conn:
        conn.execute(
            "UPDATE password_resets SET used = 1 WHERE token = ?", (token,)
        )


# ------------------------------------------------------- analysis history --

def save_analysis(user_id, language, code, result):
    """`result` is an AnalysisResult (see ai_engine.result)."""
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO analysis_history
                (user_id, language, code, summary, explanation, fixed_code,
                 has_error, severity, source, line_number)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id, language, code, result.summary, result.explanation,
                result.fixed_code, int(result.has_error), result.severity,
                result.source, result.line_number,
            ),
        )
        return conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]


def get_history(user_id, limit=10):
    with get_db() as conn:
        return conn.execute(
            """
            SELECT * FROM analysis_history
            WHERE user_id = ? ORDER BY id DESC LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()


def get_analysis_by_id(analysis_id, user_id):
    with get_db() as conn:
        return conn.execute(
            "SELECT * FROM analysis_history WHERE id = ? AND user_id = ?",
            (analysis_id, user_id),
        ).fetchone()


def get_stats(user_id):
    with get_db() as conn:
        total = conn.execute(
            "SELECT COUNT(*) AS c FROM analysis_history WHERE user_id = ?",
            (user_id,),
        ).fetchone()["c"]

        bugs = conn.execute(
            "SELECT COUNT(*) AS c FROM analysis_history "
            "WHERE user_id = ? AND has_error = 1",
            (user_id,),
        ).fetchone()["c"]

        by_day = conn.execute(
            """
            SELECT date(created_at) AS day,
                   COUNT(*) AS total,
                   SUM(has_error) AS bugs
            FROM analysis_history
            WHERE user_id = ?
            GROUP BY date(created_at)
            ORDER BY day DESC
            LIMIT 14
            """,
            (user_id,),
        ).fetchall()

        by_language = conn.execute(
            """
            SELECT language, COUNT(*) AS c
            FROM analysis_history
            WHERE user_id = ?
            GROUP BY language
            ORDER BY c DESC
            """,
            (user_id,),
        ).fetchall()

    clean = total - bugs
    success_rate = round((clean / total) * 100, 1) if total else 0.0

    # Convert sqlite3.Row -> plain dict so it can be JSON-serialized
    # for the dashboard charts.
    by_day_list = [dict(r) for r in reversed(by_day)]
    by_language_list = [dict(r) for r in by_language]

    return {
        "total_analyses": total,
        "bugs_detected": bugs,
        "fixes_suggested": bugs,
        "success_rate": success_rate,
        "by_day": by_day_list,
        "by_language": by_language_list,
    }
