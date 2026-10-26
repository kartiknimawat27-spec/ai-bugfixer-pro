"""Shared result object returned by every analyzer in this package."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class AnalysisResult:
    has_error: bool
    summary: str                 # one-line headline, e.g. "SyntaxError: ..."
    explanation: str             # plain-English explanation of the problem
    fixed_code: str              # best-effort corrected code (or original)
    severity: str = "info"       # info | low | medium | high | critical
    source: str = "static"       # "static" (rule engine) or "ai" (Claude)
    line_number: Optional[int] = None
    issues: Optional[list] = None  # list of dicts for multi-issue results

    def to_dict(self):
        return {
            "has_error": self.has_error,
            "summary": self.summary,
            "explanation": self.explanation,
            "fixed_code": self.fixed_code,
            "severity": self.severity,
            "source": self.source,
            "line_number": self.line_number,
            "issues": self.issues or [],
        }
