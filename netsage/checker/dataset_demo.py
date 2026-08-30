from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from .rule_checker import RuleChecker


def _extract_required_vlan(expected_fault: str) -> list[int]:
    lowered = expected_fault.lower()
    if "vlan" not in lowered:
        return []

    values: list[int] = []
    for token in expected_fault.replace(",", " ").split():
        token = token.strip().upper().replace("VLAN", "")
        if token.isdigit():
            values.append(int(token))

    return values[:1]


def _extract_required_route(expected_fault: str) -> list[str]:
    values: list[str] = []
    for token in expected_fault.replace(",", " ").split():
        if "/" in token and token.count(".") == 3:
            values.append(token.strip())
    return values


def build_structured_evidence(case_row: dict[str, str]) -> dict[str, Any]:
    """Build minimal structured evidence from a dataset row when possible."""

    show_outputs = case_row.get("show_outputs", "")
    expected_fault = case_row.get("expected_fault", "")

    return {
        "show_outputs": show_outputs,
        "required_vlans": _extract_required_vlan(expected_fault),
        "required_routes": _extract_required_route(expected_fault),
    }


def run_checker_on_dataset(
    csv_path: str | Path,
    *,
    limit: int | None = None,
) -> dict[str, Any]:
    """Run deterministic checker on dataset rows with available evidence.

    This utility intentionally does not invent missing host-level fields.
    Cases lacking structured evidence will produce INSUFFICIENT_DATA findings.
    """

    csv_file = Path(csv_path)
    checker = RuleChecker()

    processed_cases: list[dict[str, Any]] = []
    skipped_case_ids: list[str] = []

    with csv_file.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if limit is not None and len(processed_cases) >= limit:
                break

            evidence = build_structured_evidence(row)
            if not (evidence.get("show_outputs") or evidence.get("required_vlans") or evidence.get("required_routes")):
                skipped_case_ids.append(row.get("case_id", "UNKNOWN"))
                continue

            result = checker.check(evidence)
            processed_cases.append(
                {
                    "case_id": row.get("case_id"),
                    "concept": row.get("concept"),
                    "expected_fault": row.get("expected_fault"),
                    "checker_result": result,
                }
            )

    return {
        "processed_count": len(processed_cases),
        "skipped_count": len(skipped_case_ids),
        "skipped_case_ids": skipped_case_ids,
        "results": processed_cases,
        "note": (
            "Dataset rows are only partially structured for deterministic checking; "
            "INSUFFICIENT_DATA findings are expected where host-level fields are absent."
        ),
    }
