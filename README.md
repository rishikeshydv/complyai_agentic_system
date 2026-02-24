# Comply AI Agentic System

Production-grade monorepo for an evidence-first AML/BSA + sanctions platform with two deployable services:

1. **Bank Connector (pull mode)** (`apps/connector`)
2. **Comply AI Core Platform** (`apps/core-api`, `apps/core-worker`, `apps/web`)

## Key Guarantees

- No external web calls for laws/citations. All citation content is curated and shipped in `packages/shared/laws`.
- Evidence-first output policy: AI-generated sections use only evidence graph facts.
- Missing values are rendered as `NOT PROVIDED`.
- Non-trivial statements include evidence pointers.
- Reproducibility metadata is persisted: model/provider, prompt version, schema version, evidence hash, casefile hash.
- Source payload hash is persisted for every evidence snapshot and export bundle.
- Local first runtime through `docker-compose` with `MockLLM` default.
- New alerts are ingested automatically in the background (no analyst click required), via feed polling and optional connector callback.

## Monorepo Structure

```text
agentic_system/
  apps/
    connector/          # bank-side pull API + mock bank data
    core-api/           # FastAPI orchestration, evidence, governance, auth, endpoints
    core-worker/        # Celery worker for async tasks
    web/                # Next.js analyst portal
  packages/
    shared/
      schemas/          # JSON schemas (connector/evidence/casefile/action)
      laws/             # curated citations + mappings
      templates/        # casefile markdown rendering
      prompts/          # strict prompt templates
      seed_scripts/
  infra/
    docker-compose.yml
```

## Quick Start

1. From `agentic_system/`:

```bash
docker compose -f infra/docker-compose.yml up --build
```

If port `3000` is already in use:

```bash
WEB_PORT=3001 docker compose -f infra/docker-compose.yml up --build
```

2. Authentication is disabled in this environment. No token is required.

3. Wait for automatic ingestion (default every 30s), or run one manual fallback poll:

```bash
curl -X POST "http://localhost:8000/v1/alerts/ingestion/poll"
```

4. Open analyst UI:

- `http://localhost:3000/cases`
- `http://localhost:3000/playground`
- Legacy seeded users still exist in DB, but no login is required.

5. Cases page:

- `http://localhost:3000/cases`

## Core API Endpoints

### Alerts/Cases
- `POST /v1/alerts/{alert_id}/pull?bank_id=demo&sync=false|true` (manual fallback)
- `POST /v1/alerts/ingestion/poll` (one-shot ingestion cycle)
- `POST /v1/alerts/events` (push-style ingestion event from bank connector/backends)
- `GET /v1/cases?status=&alert_type=&created_after=`
- `GET /v1/cases/{case_id}`
- `GET /v1/cases/{case_id}/export/markdown`
- `GET /v1/cases/{case_id}/export/json`
- `GET /v1/cases/{case_id}/audit-events`
- `GET /v1/cases/{case_id}/llm-invocations`
- `POST /v1/cases/{case_id}/actions`
- `POST /v1/cases/{case_id}/replay?apply_changes=false|true` (admin)

### Admin
- `GET /v1/admin/regulatory-mappings`
- `PUT /v1/admin/regulatory-mappings`
- `GET /v1/admin/rule-maps`
- `PUT /v1/admin/rule-maps`
- `GET /v1/admin/proposed-rule-maps`

### Laws v2
- `GET /v1/laws-v2/status`
- `GET /v1/laws-v2/search?q=...&bank_id=...&alert_type=...&jurisdiction=...&rule_triggered=...`
- `POST /v1/laws-v2/map-event`

### Playground
- `GET /v1/playground/status?bank_id=demo`
- `POST /v1/playground/start`
- `POST /v1/playground/stop?bank_id=demo`
- `POST /v1/playground/tick`

### Simulation Bank API Usage

When simulation emits an alert, core pulls evidence from connector with these bank APIs:

- `GET /v1/bank/alerts?created_after=&limit=` (discover new alerts)
- `GET /v1/bank/alerts/{alert_id}` (alert payload + triggered rule context)
- `GET /v1/bank/transactions/{transaction_id}` (primary transaction evidence)
- `GET /v1/bank/customers/{customer_id}` (customer/KYC evidence)
- `GET /v1/bank/aggregates?customer_id=&rule_triggered=&window_days=` (lookback aggregates for threshold comparison)
- `GET /v1/bank/sanctions/hits/{alert_id}` (sanctions match evidence for sanctions alerts)

## Connector Endpoints

All under `/v1/bank` with API key auth (`X-API-Key`):

- `GET /alerts/{alert_id}`
- `GET /alerts?created_after=&limit=` (alert feed for background ingestion)
- `GET /transactions?customer_id=&created_after=&limit=` (list transactions for playground/tools)
- `GET /transactions/{transaction_id}`
- `GET /customers?segment=&limit=` (list customers for playground/tools)
- `GET /customers/{customer_id}`
- `GET /aggregates?customer_id=...&rule_triggered=...&window_days=...`
- `GET /sanctions/hits/{alert_id}`

Simulator control endpoints:
- `GET /v1/sim/status`
- `POST /v1/sim/start`
- `POST /v1/sim/stop`
- `POST /v1/sim/tick`

Connector enforces:
- field allowlist from YAML (`apps/connector/connector/allowlist.yaml`)
- fetch audit logging with request_id
- API key auth + signed-request option (mTLS-ready design documented)

## Workflow States

- `RECEIVED_ALERT_EVENT`
- `FETCHING_EVIDENCE`
- `EVIDENCE_READY`
- `EXPLAINING_TRIGGER`
- `BUILDING_CASEFILE`
- `SAR_DRAFTING` (conditional)
- `READY_FOR_REVIEW`
- `ERROR`

## Worker Tasks

- `pull_and_generate_case(alert_id, bank_id, workflow_run_id)`
- `poll_connector_alerts()`
- `generate_sar(case_id)`
- `repair_casefile(case_id)`

## Tests

Pytest suites are included for:
- connector endpoint contract checks
- evidence graph required node/edge generation
- orchestrator case generation with MockLLM
- governance audit event creation

## Notes

- OpenAI provider is intentionally a placeholder.
- Curated citation dataset is configurable and intended for legal-team customization.
- Deterministic law mapping v2 dataset is seeded from `packages/shared/laws/mapping_v2.yaml`.
