from __future__ import annotations

import os

from fastapi.testclient import TestClient

os.environ["CORE_DB_URL"] = "sqlite:///file:core_test?mode=memory&cache=shared&uri=true"
os.environ["LLM_PROVIDER"] = "mock"
os.environ["CELERY_TASK_ALWAYS_EAGER"] = "true"

from core.db.models import Base
from core.db.seed import seed
from core.db.session import engine
from core.main import app


def setup_module() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    seed()


def test_laws_v2_search_returns_seeded_citations() -> None:
    client = TestClient(app)
    resp = client.get(
        "/v1/laws-v2/search",
        params={
            "q": "currency transactions suspicious reports",
            "alert_type": "AML",
            "top_k": 5,
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["total"] >= 1
    citation_ids = {row["citation_id"] for row in payload["results"]}
    assert "AML-US-31CFR1010.311" in citation_ids or "AML-US-31CFR1010.320" in citation_ids


def test_laws_v2_map_event_returns_deterministic_mapping() -> None:
    client = TestClient(app)
    resp = client.post(
        "/v1/laws-v2/map-event",
        json={
            "bank_id": "default",
            "alert_id": "ALERT-TEST-001",
            "event_type": "AML_ALERT",
            "rule_triggered": "CASH_SPIKE_30D",
            "rule_description": "30-day cash deposits exceeded profile threshold",
            "conditions_triggered": [
                {
                    "field": "historical_aggregates.cash_deposit_total_30d",
                    "operator": ">=",
                    "threshold": 25000,
                    "actual": 31250,
                    "window_days": 30,
                }
            ],
            "jurisdiction_context": "federal+NJ",
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["mapping_mode"] == "deterministic"
    assert payload["citations"]
    assert payload["controls"]
    assert any(item["citation_id"] == "AML-US-31CFR1010.311" for item in payload["citations"])
