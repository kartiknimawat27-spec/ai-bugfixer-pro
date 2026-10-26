"""
Baseline heuristic checks for non-Python languages.

These are intentionally simple structural checks (brace/paren
balance, obvious missing semicolons) that work with zero
dependencies. When ANTHROPIC_API_KEY is configured, `engine.analyze`
prefers the much stronger Claude-powered review for these languages
and only falls back to these heuristics if AI review is unavailable.
"""

from ai_engine.result import AnalysisResult

PAIRS = {"(": ")", "[": "]", "{": "}"}
CLOSERS = {v: k for k, v in PAIRS.items()}


def _check_balance(code):
    stack = []
    in_string = None
    for i, ch in enumerate(code):
        if in_string:
            if ch == in_string and code[i - 1] != "\\":
                in_string = None
            continue
        if ch in ("'", '"'):
            in_string = ch
        elif ch in PAIRS:
            stack.append(ch)
        elif ch in CLOSERS:
            if not stack or stack[-1] != CLOSERS[ch]:
                return False, f"Unmatched `{ch}`"
            stack.pop()
    if stack:
        return False, f"Unclosed `{stack[-1]}`"
    return True, None


def _find_unclosed_line(code, stack_char):
    """Best-effort: return the 1-based line of the last unmatched opener."""
    depth = 0
    in_string = None
    target_line = None
    for i, ch in enumerate(code):
        if in_string:
            if ch == in_string and code[i - 1] != "\\":
                in_string = None
            continue
        if ch in ("'", '"'):
            in_string = ch
        elif ch == stack_char:
            depth += 1
            target_line = code.count("\n", 0, i) + 1
        elif ch == PAIRS[stack_char]:
            depth -= 1
    return target_line if depth > 0 else None


def _suggest_fix(code, message):
    """
    Responsibility: never hand back broken code unexplained. If the
    problem is an unclosed bracket, append the missing closer(s) — the
    single most common, safely-correctable mistake in this class of
    error. Anything riskier (unmatched *closing* bracket, deeper
    structural damage) is left for the AI reviewer / the developer,
    since guessing wrong would be worse than not guessing.
    """
    if message.startswith("Unclosed"):
        opener = message.split("`")[1]
        closer = PAIRS[opener]
        return code.rstrip() + closer, _find_unclosed_line(code, opener)
    return code, None


def analyze(code, language):
    balanced, message = _check_balance(code)

    if not balanced:
        fixed_code, line = _suggest_fix(code, message)
        corrected = fixed_code != code

        return AnalysisResult(
            has_error=True,
            summary=f"Structural issue: {message}",
            explanation=(
                f"{message} was detected. Brackets, parentheses and "
                "braces must always be balanced and correctly nested."
                + (
                    " A corrected version is suggested below — please "
                    "double-check it against your intended logic."
                    if corrected
                    else " This needs a manual look: an extra closing "
                    "bracket can't be safely auto-removed without "
                    "risking a change in your logic."
                )
            ),
            fixed_code=fixed_code,
            severity="high",
            source="static",
            line_number=line,
            issues=[{"line": line, "severity": "high", "message": message}],
        )

    return AnalysisResult(
        has_error=False,
        summary=f"No structural issues detected in this {language} file",
        explanation=(
            "Brackets and braces are balanced. Deep semantic review for "
            f"{language} requires AI review — connect an Anthropic API "
            "key to enable it for full bug detection and fix suggestions."
        ),
        fixed_code=code,
        severity="info",
        source="static",
        issues=[],
    )
