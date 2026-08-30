# NetSage AI Architecture

## System architecture

NetSage AI is structured as a layered Flask application:

1. **Presentation layer** — Flask routes/templates and static frontend assets
2. **Application layer** — orchestration services for cases, review, and verification
3. **Domain layer** — deterministic checker + AI diagnosis abstractions
4. **Data layer** — SQLite (planned) and CSV-based case datasets (planned)

## Major components

- `netsage/routes/` — HTTP endpoints and page routing via blueprints
- `netsage/checker/` — deterministic network rule checks (placeholder)
- `netsage/ai/` — provider abstraction, diagnosis schema, prompt stubs (placeholder)
- `netsage/services/` — case/review/verification orchestration (placeholder)
- `netsage/models/` — domain/persistence model placeholders
- `netsage/utils/` — shared helpers placeholder

## Data flow

1. User submits a network symptom and evidence.
2. Input is validated and normalized.
3. Deterministic checks run first.
4. Structured evidence is prepared for AI (future phase).
5. AI returns structured diagnosis (future phase).
6. Human reviewer accepts/edits/rejects diagnosis.
7. User applies approved fix manually in lab.
8. Verification evidence is captured.
9. Metrics update dashboard analytics.

## AI workflow

- AI is used **after** deterministic checks.
- AI must reason only from supplied evidence.
- AI must not invent topology details, commands, VLANs, routes, or outcomes.
- If evidence is insufficient, output confidence must be LOW and request more evidence.

## Human-review workflow

Every AI diagnosis must be reviewed before action:

- **ACCEPT**
- **EDIT**
- **REJECT**

Store both original AI output and final human-reviewed decision with rationale.

## Verification workflow

No recommendation is considered successful until user re-tests network behavior.

Verification records must capture:

- approved fix attempted
- post-fix evidence/command outputs
- resolved/unresolved outcome
- follow-up actions

## Development roadmap

1. **PHASE 1 — Architecture and foundation**
2. **PHASE 2 — Case dataset**
3. **PHASE 3 — Deterministic rule checker**
4. **PHASE 4 — Structured prompt engineering**
5. **PHASE 5 — AI diagnosis integration**
6. **PHASE 6 — Guided troubleshooting workflow**
7. **PHASE 7 — Human review and Responsible AI logging**
8. **PHASE 8 — Dashboard and analytics**
9. **PHASE 9 — Testing with deliberately broken Packet Tracer scenarios**
10. **PHASE 10 — Final demo and documentation**
