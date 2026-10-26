"""
Top-level orchestrator: routes an analysis request to the right
engine and returns a single, consistent AnalysisResult.

Strategy:
- Python:       AST syntax + semantic linter always runs first (fast,
                free, 100% reliable for syntax). If AI is configured,
                its findings are layered in as the richer explanation.
- Other langs:  If AI is configured, Claude performs the review
                directly. Otherwise, fall back to structural
                heuristics (bracket balance, etc).
"""

from ai_engine import ai_client, python_analyzer, multi_lang
from ai_engine.result import AnalysisResult


def analyze(code, language):
    if language == "Python":
        static_result = python_analyzer.analyze(code)

        # Only spend an AI call on code that is at least syntactically
        # valid Python — no point asking the model to fix a parse error
        # our own AST-based fixer already handles deterministically.
        if not static_result.has_error:
            ai_payload = ai_client.review_code(code, language)
            if ai_payload:
                return AnalysisResult(source="ai", **ai_payload)
        return static_result

    ai_payload = ai_client.review_code(code, language)
    if ai_payload:
        return AnalysisResult(source="ai", **ai_payload)

    return multi_lang.analyze(code, language)
