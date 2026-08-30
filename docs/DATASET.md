# NetSage AI Troubleshooting Case Dataset

## Purpose

`data/cases.csv` is a controlled evaluation dataset for NetSage AI.

It provides realistic Cisco Packet Tracer/Cisco-style troubleshooting scenarios with known answers. The dataset is used to evaluate diagnosis quality in later phases; it is not ML training data.

## Case schema

Each row is one troubleshooting case.

### Required fields

- `case_id` — unique case identifier (for example `NS-CASE-001`)
- `title` — short case summary
- `symptom` — user-observed issue and impact
- `topology_note` — minimal topology context required to reason correctly
- `show_outputs` — Cisco-style evidence snippets relevant to the issue
- `expected_fault` — known correct root cause for evaluation
- `osi_layer` — primary OSI layer for the fault
- `concept` — issue category
- `severity` — impact classification (`SEV-1`, `SEV-2`, `SEV-3`)

### Optional fields currently included

- `expected_next_command`
- `expected_fix`
- `verification_command`
- `difficulty`

## Issue categories covered

The dataset includes cases across these required categories:

- VLAN
- Default gateway
- DHCP
- DNS
- Routing
- ACL
- NAT
- Wireless

## Severity definitions

- `SEV-1`: Critical/widespread impact (major outage, broad service loss)
- `SEV-2`: Significant service or user impact (important function degraded for a team/site)
- `SEV-3`: Limited/localized impact (single user/host/segment issue)

## How this dataset is used later

In later phases, NetSage AI responses will be compared against the expected fields (`expected_fault`, `osi_layer`, `concept`, and related guidance fields).

Typical evaluation dimensions:

1. Root-cause accuracy
2. Correct OSI-layer mapping
3. Correct category mapping
4. Command guidance quality
5. Fix recommendation alignment with known expected fix

## Adding new cases

When adding cases:

1. Preserve CSV header names.
2. Add a unique `case_id`.
3. Keep evidence realistic to Cisco CLI style and relevant to the symptom.
4. Ensure `expected_fault` is singular, clear, and testable.
5. Assign a valid severity (`SEV-1`, `SEV-2`, `SEV-3`) based on impact.
6. Use non-empty required fields.
7. Keep category distribution balanced across required concepts.
8. Run `python -m unittest tests/test_cases.py` before submitting changes.

## Dataset quality considerations

- Avoid vague symptoms such as only “ping failed”.
- Avoid contradictory/impossible states in evidence.
- Keep each case distinct from others.
- Prefer concise but sufficient `show_outputs` excerpts over oversized dumps.
- Keep assumptions explicit in `topology_note`.
- Maintain Cisco Packet Tracer compatibility for lab reproducibility.
