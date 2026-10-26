"""
Thin wrapper around the Anthropic API for deep, natural-language code
review. This is what makes the platform genuinely "AI-based" rather
than purely rule-based.

Design notes:
- The API key is only ever read from the environment
  (ANTHROPIC_API_KEY). It is never hard-coded or logged.
- If no key is configured, or the request fails for any reason, the
  caller falls back to the static-analysis engine — the product never
  breaks because of a missing/expired key or a network hiccup.
- We ask the model to answer in strict JSON so the response can be
  parsed reliably and rendered in the UI.
"""

import json
import re

from config import Config

_client = None


def _get_client():
    global _client
    if _client is None and Config.AI_ENABLED:
        import anthropic
        _client = anthropic.Anthropic(api_key=Config.ANTHROPIC_API_KEY)
    return _client


SYSTEM_PROMPT = (
    "You are a senior software engineer performing a precise code "
    "review. You will be given a source file in a specific language. "
    "Respond ONLY with a single JSON object (no markdown fences, no "
    "prose before or after) with exactly these keys:\n"
    '  "has_error": boolean — true if there is a bug, syntax error, or '
    "significant issue\n"
    '  "summary": short one-line headline of the main finding\n'
    '  "explanation": 2-4 sentences explaining the problem(s) in plain '
    "English and why they matter\n"
    '  "fixed_code": the corrected full source code (same language). '
    "If nothing needs fixing, return the original code unchanged.\n"
    '  "severity": one of "info", "low", "medium", "high", "critical"\n'
    '  "line_number": integer line number of the primary issue, or null\n'
    '  "issues": array of objects {"line": int, "severity": string, '
    '"message": string} for every distinct issue found (may be empty)\n'
    "Be concise, accurate, and never invent issues that are not "
    "actually present in the code."
)


def _extract_json(text):
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    return json.loads(text)


def review_code(code, language):
    """
    Returns a dict matching the AnalysisResult fields, or None if AI
    review is unavailable / failed (caller should fall back).
    """
    client = _get_client()
    if client is None:
        return None

    try:
        response = client.messages.create(
            model=Config.CLAUDE_MODEL,
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": f"Language: {language}\n\nCode:\n```{language}\n{code}\n```",
            }],
        )
        text_parts = [b.text for b in response.content if getattr(b, "type", "") == "text"]
        payload = _extract_json("".join(text_parts))

        return {
            "has_error": bool(payload.get("has_error", False)),
            "summary": str(payload.get("summary", "AI review complete")),
            "explanation": str(payload.get("explanation", "")),
            "fixed_code": str(payload.get("fixed_code", code)) or code,
            "severity": payload.get("severity", "info"),
            "line_number": payload.get("line_number"),
            "issues": payload.get("issues", []),
        }
    except Exception as exc:  # noqa: BLE001 - deliberate broad fallback
        # Never let an AI/network failure break the analyzer.
        print(f"[ai_client] AI review unavailable, falling back: {exc}")
        return None
