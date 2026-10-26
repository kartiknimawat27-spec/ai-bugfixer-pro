"""
JSON API used by the in-page analyzer widget (AJAX) and by the
report download endpoint.
"""

import difflib
import os

from flask import Blueprint, request, jsonify, session, send_file, abort

import models
from ai_engine import engine
from config import Config
from routes.dashboard import login_required

bp = Blueprint("api", __name__, url_prefix="/api")


def _build_diff(original, fixed):
    """
    Line-level diff so the UI can show exactly what was corrected,
    not just the two full versions side by side.
    """
    if original == fixed:
        return []

    diff = difflib.ndiff(original.splitlines(), fixed.splitlines())
    rows = []
    for line in diff:
        tag, text = line[0], line[2:]
        if tag == " ":
            rows.append({"type": "context", "text": text})
        elif tag == "-":
            rows.append({"type": "removed", "text": text})
        elif tag == "+":
            rows.append({"type": "added", "text": text})
        # '?' hint lines from ndiff are intentionally dropped
    return rows


@bp.route("/analyze", methods=["POST"])
@login_required
def analyze():
    data = request.get_json(silent=True) or request.form
    code = (data.get("code") or "").strip()
    language = data.get("language") or "Python"

    if not code:
        return jsonify({"error": "Please provide some code to analyze."}), 400

    if language not in Config.SUPPORTED_LANGUAGES:
        language = "Python"

    result = engine.analyze(code, language)
    analysis_id = models.save_analysis(session["user_id"], language, code, result)

    payload = result.to_dict()
    payload["id"] = analysis_id
    payload["language"] = language
    payload["ai_powered"] = result.source == "ai"
    payload["was_corrected"] = result.fixed_code != code
    payload["diff"] = _build_diff(code, result.fixed_code)
    return jsonify(payload)


@bp.route("/history/<int:analysis_id>")
@login_required
def history_detail(analysis_id):
    row = models.get_analysis_by_id(analysis_id, session["user_id"])
    if row is None:
        abort(404)
    return jsonify(dict(row))


@bp.route("/report/<int:analysis_id>")
@login_required
def report(analysis_id):
    row = models.get_analysis_by_id(analysis_id, session["user_id"])
    if row is None:
        abort(404)

    os.makedirs(Config.REPORTS_DIR, exist_ok=True)
    path = os.path.join(Config.REPORTS_DIR, f"analysis_{analysis_id}.txt")

    lines = [
        "AI BugFixer Pro — Analysis Report",
        "=" * 40,
        f"Report ID:   {row['id']}",
        f"Language:    {row['language']}",
        f"Date:        {row['created_at']}",
        f"Has Error:   {'Yes' if row['has_error'] else 'No'}",
        f"Severity:    {row['severity']}",
        f"Source:      {'AI-powered review' if row['source'] == 'ai' else 'Static analysis'}",
        "",
        "Summary",
        "-" * 40,
        row["summary"] or "",
        "",
        "Explanation",
        "-" * 40,
        row["explanation"] or "",
        "",
        "Original Code",
        "-" * 40,
        row["code"] or "",
        "",
        "Suggested / Fixed Code",
        "-" * 40,
        row["fixed_code"] or "",
        "",
    ]

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return send_file(path, as_attachment=True, download_name=f"bugfixer_report_{analysis_id}.txt")
