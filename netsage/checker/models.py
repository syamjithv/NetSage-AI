from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal


RuleStatus = Literal["PASS", "FAIL", "WARNING", "INSUFFICIENT_DATA"]
RuleSeverity = Literal["LOW", "MEDIUM", "HIGH"]


@dataclass(frozen=True)
class RuleFinding:
    """Single deterministic rule-check result."""

    rule: str
    status: RuleStatus
    severity: RuleSeverity
    message: str
    evidence: dict[str, Any]
    recommendation: str

    def to_dict(self) -> dict[str, Any]:
        """Return a machine-readable finding payload."""

        return asdict(self)
