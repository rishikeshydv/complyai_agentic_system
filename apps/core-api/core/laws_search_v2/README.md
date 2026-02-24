# laws_search_v2

Standalone v2 law search + law mapping package.

## Contents
- SQLAlchemy models: `models_sqlalchemy.py`
- Alembic migration: `alembic/versions/20260208_0001_law_kb_and_mapping.py`
- Post-processing pipeline: `postprocess/`
- Mapping engine: `law_mapping/`
- API routes: `api/routes.py`
- FastAPI app: `app.py`
- Seeds: `seeds/`
- Tests: `tests/`

## Quickstart
```bash
cd backend/laws_search_v2
docker compose up -d
export LAWS_V2_DATABASE_URL="postgresql+psycopg2://postgres:postgres@localhost:5432/comply_ai"
export LAWS_V2_ES_URL="http://localhost:9200"
alembic upgrade head
python -m laws_search_v2.backfill_existing_laws --use-es
python -m laws_search_v2.seeds.seed_law_mapping
pytest -q tests
```

## Existing Ingestion Integration
Use `IngestionOrchestratorV2` from `ingestion_adapter.py` as a drop-in replacement for the existing orchestrator.
It calls the legacy ingestion flow first, then runs post-processing for v2 knowledge-base artifacts.
