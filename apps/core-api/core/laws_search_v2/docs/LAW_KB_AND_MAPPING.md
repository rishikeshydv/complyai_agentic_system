# Law KB And Mapping (V2)

## Overview
`laws_search_v2` adds a two-layer architecture on top of existing document ingestion:

1. **Law Knowledge Base (LKB)**
- `regulatory_chunks`: deterministic text chunks with traceable spans
- `obligation_cards`: structured obligations grounded to chunk spans/excerpts

2. **Law-Mapping Engine**
- Deterministic-first mapping: `rule_to_typology_map -> control_objectives -> control_to_obligation_map`
- Retrieval/LLM fallback only when deterministic mapping is missing
- Strict grounding checks on all explanations and mappings

## Data Flow
1. Existing ingestion fetches and stores `regulatory_documents`.
2. `PostProcessor` runs after ingestion and:
- chunks document text (`postprocess/chunker.py`)
- extracts obligations (`postprocess/obligation_extractor.py`)
- validates grounding (`chunk_id + span OR chunk_id + excerpt`)
- writes `regulatory_chunks` / `obligation_cards`
- indexes `reg_chunks` and `reg_obligations`
3. Mapping service (`law_mapping/service.py`) maps events to controls/obligations/citations.

## Grounding Rules
An obligation/explanation is valid only if:
- it references a `chunk_id`, and
- it has valid `span_start/span_end` OR an `excerpt` present in the chunk text.

Invalid grounding is dropped and never returned in mapping results.

## Deterministic-First Mapping
`LawMappingService` executes:
1. Load latest rule map by `(bank_id, rule_triggered)`.
2. Resolve typology and control IDs.
3. Resolve obligations through `control_to_obligation_map`.
4. Return obligations + citations with event evidence pointer and grounding pointer.

Fallback path (only if deterministic mapping misses):
1. Search `reg_obligations` by rule description + conditions.
2. Mock/LLM explainer reranks and generates grounded `why_relevant`.
3. Save suggestion in `proposed_rule_map` for manual approval.

## Seeding Controls/Typologies/Maps
Use either:
- SQL seed: `seeds/seed_law_mapping.sql`
- Python seed: `python -m laws_search_v2.seeds.seed_law_mapping`

Example seeded typologies:
- `TYPO_STRUCTURING`
- `TYPO_OFAC_NAME_MATCH`

Example seeded controls:
- `CTRL_SAR_FILE`
- `CTRL_STRUCTURING_MONITOR`
- `CTRL_OFAC_SCREEN`

## API Endpoints
### `GET /v1/laws/search`
Params:
- `q`
- `jurisdiction` (optional)
- `agency` (optional)
- `type` (optional)

Returns obligation-first results with:
- summary bullets
- `must_do`
- `artifacts_required`
- highlighted excerpt
- citation + source URL
- confidence + review status

### `POST /v1/laws/map-event`
Request:
```json
{
  "bank_id": "bank_demo",
  "event_id": "alert_123",
  "event_type": "AML_ALERT",
  "rule_triggered": "RULE_STRUCTURING_001",
  "rule_description": "Repeated cash deposits below threshold",
  "conditions_triggered": [
    {
      "field": "cash_deposit_count_7d",
      "operator": ">=",
      "threshold": 3,
      "actual": 5,
      "window_days": 7
    }
  ],
  "jurisdiction_context": "federal + NJ"
}
```

Response (shape):
```json
{
  "event_id": "alert_123",
  "mapping_mode": "deterministic",
  "controls": [
    {"control_id": "CTRL_SAR_FILE", "name": "SAR Filing"}
  ],
  "obligations": [
    {
      "obligation_id": "...",
      "must_do": "...",
      "conditions": "...",
      "artifacts_required": ["..."],
      "summary_bullets": ["..."],
      "grounding": {"chunk_id": "...", "span_start": 12, "span_end": 84}
    }
  ],
  "citations": [
    {
      "citation": "31 CFR 1020.320",
      "title": "Reports by banks of suspicious transactions",
      "jurisdiction": "federal",
      "agency": "fincen",
      "excerpt": "...",
      "source_url": "...",
      "why_relevant": "Evidence condition[0]=... Pointer grounding(chunk_id=...,span=12-84)."
    }
  ]
}
```

## Local Dev (Postgres + Elasticsearch)
Use `laws_search_v2/docker-compose.yml`:
- Postgres on `localhost:5432`
- Elasticsearch on `localhost:9200`

Then:
1. Run alembic migration in `laws_search_v2`
2. Run post-processing to generate chunks and obligations
3. Run seed script to initialize mappings
