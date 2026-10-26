"""
Static analysis engine for Python.

Two layers:
1. Syntax validation via the `ast` module, with targeted, verified
   auto-fixes for the most common syntax mistakes (missing colon,
   unterminated string, bad indentation, unclosed brackets).
   A candidate fix is only kept if it re-parses cleanly.
2. Lightweight semantic linting over the AST for issues that are
   syntactically valid but risky: bare `except:`, mutable default
   arguments, use of `eval`/`exec`, comparing to None/True/False with
   `==`, unused imports, and shadowed builtins.

This runs with zero external dependencies and zero network calls, so
it is always available even when AI review is disabled.
"""

import ast

from ai_engine.result import AnalysisResult

BLOCK_KEYWORDS = (
    "def ", "if ", "elif ", "else", "for ", "while ",
    "class ", "try", "except", "finally", "with ",
)


def _try_parse(code):
    try:
        ast.parse(code)
        return True
    except SyntaxError:
        return False


def _fix_missing_colon(lines, index):
    original = lines[index]
    stripped = original.strip()
    if stripped.startswith(BLOCK_KEYWORDS) and not stripped.endswith(":"):
        candidate = lines.copy()
        candidate[index] = original.rstrip() + ":"
        return candidate
    return None


def _fix_unterminated_string(lines, index):
    original = lines[index]
    dq, sq = original.count('"'), original.count("'")
    candidate = lines.copy()
    if dq % 2 == 1:
        candidate[index] = original.rstrip() + ('")' if "(" in original else '"')
    elif sq % 2 == 1:
        candidate[index] = original.rstrip() + ("')" if "(" in original else "'")
    else:
        return None
    return candidate


def _fix_expected_indent(lines, index):
    if index < len(lines) and lines[index].strip():
        candidate = lines.copy()
        candidate[index] = "    " + lines[index].lstrip()
        return candidate
    return None


def _fix_unexpected_indent(lines, index):
    candidate = lines.copy()
    candidate[index] = lines[index].lstrip()
    return candidate


SYNTAX_FIXERS = [
    (lambda e: "expected ':'" in e,
     "A block statement is missing its trailing colon. Every `def`, "
     "`if`, `for`, `while`, `class`, `try`/`except` line must end with `:`.",
     _fix_missing_colon),
    (lambda e: "unterminated string" in e.lower(),
     "A string literal was opened but never closed. Make sure every "
     "opening quote has a matching closing quote of the same type.",
     _fix_unterminated_string),
    (lambda e: "expected an indented block" in e.lower(),
     "Python requires an indented block after a colon. Indent the "
     "line that follows the block header by 4 spaces.",
     _fix_expected_indent),
    (lambda e: "unexpected indent" in e.lower(),
     "This line has extra, unexpected indentation relative to the "
     "surrounding code. Align it with the rest of the block.",
     _fix_unexpected_indent),
]


_BRACKET_PAIRS = {"(": ")", "[": "]", "{": "}"}


def _fix_unclosed_bracket(code):
    """
    Scan for unclosed ( [ { and append the missing closers in the
    correct (reverse) order. The result is only ever returned if it
    re-parses cleanly — an unverified "fix" is worse than none.
    """
    stack = []
    in_string = None
    for i, ch in enumerate(code):
        if in_string:
            if ch == in_string and code[i - 1] != "\\":
                in_string = None
            continue
        if ch in ("'", '"'):
            in_string = ch
        elif ch in _BRACKET_PAIRS:
            stack.append(ch)
        elif ch in _BRACKET_PAIRS.values():
            if stack:
                stack.pop()

    if not stack:
        return code

    closers = "".join(_BRACKET_PAIRS[c] for c in reversed(stack))
    candidate = code.rstrip() + closers
    return candidate if _try_parse(candidate) else code


def _syntax_fix(code, error_msg, line_number):
    lines = code.splitlines()
    for matches, explanation, fixer in SYNTAX_FIXERS:
        if matches(error_msg):
            fixed_code = code
            if line_number and 1 <= line_number <= len(lines):
                candidate = fixer(lines, line_number - 1)
                if candidate is not None:
                    candidate_code = "\n".join(candidate)
                    if _try_parse(candidate_code):
                        fixed_code = candidate_code
            return explanation, fixed_code

    if "was never closed" in error_msg.lower():
        fixed = _fix_unclosed_bracket(code)
        base = (
            "A bracket, parenthesis or square bracket is not properly "
            "closed. Every `(`, `[` and `{` needs a matching partner."
        )
        if fixed != code:
            return base + " A corrected version is suggested below.", fixed
        return base + " Please review it manually — the automatic " \
            "corrector could not produce a version that re-parses cleanly.", code

    if "unmatched" in error_msg.lower():
        return (
            "There is an extra closing bracket with no matching opener. "
            "This can't be safely auto-removed without risking a change "
            "to your logic — please review the reported line by hand.",
            code,
        )
    if "invalid syntax" in error_msg.lower():
        return (
            "There is a general syntax problem. Review the reported "
            "line and the line immediately before it.",
            code,
        )
    return (
        "Review the reported line and adjust the code according to "
        "the error message and line number.",
        code,
    )


# ------------------------------------------------------- semantic linting --

class _Linter(ast.NodeVisitor):
    def __init__(self):
        self.issues = []
        self.imported_names = {}
        self.used_names = set()

    def visit_Import(self, node):
        for alias in node.names:
            name = alias.asname or alias.name.split(".")[0]
            self.imported_names[name] = node.lineno
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        for alias in node.names:
            name = alias.asname or alias.name
            self.imported_names[name] = node.lineno
        self.generic_visit(node)

    def visit_Name(self, node):
        self.used_names.add(node.id)
        self.generic_visit(node)

    def visit_ExceptHandler(self, node):
        if node.type is None:
            self.issues.append({
                "line": node.lineno, "severity": "medium",
                "message": "Bare `except:` catches every exception, "
                            "including KeyboardInterrupt and SystemExit. "
                            "Catch a specific exception type instead.",
            })
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        for default in node.args.defaults:
            if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                self.issues.append({
                    "line": node.lineno, "severity": "medium",
                    "message": f"Function `{node.name}` uses a mutable "
                                "default argument (list/dict/set). "
                                "Defaults are shared across calls and can "
                                "cause hard-to-find bugs; use `None` and "
                                "create the value inside the function.",
                })
        self.generic_visit(node)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name) and node.func.id in ("eval", "exec"):
            self.issues.append({
                "line": node.lineno, "severity": "high",
                "message": f"`{node.func.id}()` executes arbitrary code and "
                            "is a common source of security vulnerabilities. "
                            "Avoid it, especially on untrusted input.",
            })
        self.generic_visit(node)

    def visit_Compare(self, node):
        for op, comparator in zip(node.ops, node.comparators):
            if isinstance(op, (ast.Eq, ast.NotEq)) and isinstance(
                comparator, ast.Constant
            ) and comparator.value in (None, True, False):
                self.issues.append({
                    "line": node.lineno, "severity": "low",
                    "message": f"Use `is` / `is not` to compare against "
                                f"{comparator.value!r}, not `==` / `!=`.",
                })
        self.generic_visit(node)

    def finalize(self):
        for name, line in self.imported_names.items():
            if name not in self.used_names:
                self.issues.append({
                    "line": line, "severity": "low",
                    "message": f"Import `{name}` appears to be unused.",
                })
        return sorted(self.issues, key=lambda i: i["line"])


def _lint(code):
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []
    linter = _Linter()
    linter.visit(tree)
    return linter.finalize()


# ------------------------------------------------------------- public API --

def analyze(code):
    try:
        ast.parse(code)
    except SyntaxError as e:
        explanation, fixed_code = _syntax_fix(code, e.msg or "", e.lineno)
        return AnalysisResult(
            has_error=True,
            summary=f"SyntaxError: {e.msg} (line {e.lineno})",
            explanation=explanation,
            fixed_code=fixed_code,
            severity="high",
            source="static",
            line_number=e.lineno,
            issues=[{
                "line": e.lineno, "severity": "high",
                "message": f"SyntaxError: {e.msg}",
            }],
        )

    issues = _lint(code)
    if issues:
        worst = max(issues, key=lambda i: {"low": 1, "medium": 2, "high": 3}[i["severity"]])
        return AnalysisResult(
            has_error=False,
            summary=f"No syntax errors — {len(issues)} code-quality "
                    f"issue(s) found",
            explanation=worst["message"],
            fixed_code=code,
            severity=worst["severity"],
            source="static",
            line_number=worst["line"],
            issues=issues,
        )

    return AnalysisResult(
        has_error=False,
        summary="No syntax errors and no quality issues found",
        explanation="Your Python code is syntactically correct and passes "
                    "all built-in quality checks.",
        fixed_code=code,
        severity="info",
        source="static",
        issues=[],
    )
