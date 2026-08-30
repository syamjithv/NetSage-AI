# NetSage AI

NetSage AI is an AI-assisted troubleshooting helper for Cisco Packet Tracer/lab environments.

This repository currently contains **Phase 1: architecture and foundation only**.

## What exists in this phase

- Production-style modular Flask scaffold
- Health/status endpoint (`/health`)
- Placeholder route pages for troubleshooting, review, and dashboard
- Placeholder packages for checker, AI abstraction, services, models, and utilities
- Architecture and staged roadmap documentation

## Architecture summary

See `/docs/ARCHITECTURE.md` for complete architecture details. High-level separation:

- **Routes**: Flask blueprints in `netsage/routes/`
- **Deterministic checks**: `netsage/checker/` (placeholder)
- **AI abstraction**: `netsage/ai/` (placeholder, no live integration)
- **Workflow services**: `netsage/services/` (placeholder)
- **Templates/static assets**: `templates/`, `static/`

## Development stages

1. PHASE 1 — Architecture and foundation
2. PHASE 2 — Case dataset
3. PHASE 3 — Deterministic rule checker
4. PHASE 4 — Structured prompt engineering
5. PHASE 5 — AI diagnosis integration
6. PHASE 6 — Guided troubleshooting workflow
7. PHASE 7 — Human review and Responsible AI logging
8. PHASE 8 — Dashboard and analytics
9. PHASE 9 — Testing with deliberately broken Packet Tracer scenarios
10. PHASE 10 — Final demo and documentation

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python app.py
```

Then open:

- `http://127.0.0.1:5000/`
- `http://127.0.0.1:5000/health`

## Dependencies

- Flask
- python-dotenv

## Intentionally not implemented yet

- AI API integration
- deterministic rule logic implementation
- 30-case troubleshooting dataset
- human review persistence workflow
- verification persistence workflow
- dashboard analytics implementation
- production database schema

## Recommended next task after Phase 1 review

Proceed to **Phase 2: define and add the structured troubleshooting case dataset and evidence templates**.
