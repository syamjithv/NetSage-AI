from __future__ import annotations

from typing import Any, Callable

from .models import RuleFinding
from .rules import (
    check_default_gateway_mismatch,
    check_duplicate_ip_addresses,
    check_interface_administrative_state,
    check_missing_route,
    check_missing_vlan,
    check_subnet_mask_and_host_relationship,
    normalize_evidence,
)

RuleFn = Callable[[dict[str, Any]], RuleFinding]


class RuleChecker:
    """Deterministic, explainable network triage checker for NetSage AI Phase 3."""

    def __init__(self, rules: list[RuleFn] | None = None):
        self._rules = rules or [
            check_duplicate_ip_addresses,
            check_subnet_mask_and_host_relationship,
            check_default_gateway_mismatch,
            check_interface_administrative_state,
            check_missing_vlan,
            check_missing_route,
        ]

    def check(self, evidence: dict[str, Any] | None) -> dict[str, Any]:
        """Run all deterministic checks and return structured findings."""

        normalized = normalize_evidence(evidence or {})
        findings = [rule(normalized).to_dict() for rule in self._rules]

        status_counts: dict[str, int] = {
            "PASS": 0,
            "FAIL": 0,
            "WARNING": 0,
            "INSUFFICIENT_DATA": 0,
        }
        for finding in findings:
            status = finding["status"]
            status_counts[status] = status_counts.get(status, 0) + 1

        overall_status = "PASS"
        if status_counts["FAIL"] > 0:
            overall_status = "FAIL"
        elif status_counts["WARNING"] > 0:
            overall_status = "WARNING"
        elif status_counts["INSUFFICIENT_DATA"] > 0:
            overall_status = "INSUFFICIENT_DATA"

        return {
            "overall_status": overall_status,
            "summary": status_counts,
            "findings": findings,
        }
