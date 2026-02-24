from __future__ import annotations

import os

from fastapi.testclient import TestClient

os.environ["CONNECTOR_DB_URL"] = "sqlite:///file:connector_test?mode=memory&cache=shared&uri=true"
os.environ["CONNECTOR_API_KEY"] = "dev-connector-key"
os.environ["FIELD_ALLOWLIST_PATH"] = "apps/connector/connector/allowlist.yaml"

from connector.db.models import Base
from connector.db.seed import seed
from connector.db.session import engine
from connector.main import app


def setup_module() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    seed()


def _client() -> TestClient:
    return TestClient(app)


def test_alert_endpoint_contract() -> None:
    response = _client().get("/v1/bank/alerts/ALERT-001", headers={"X-API-Key": "dev-connector-key"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["alert_type"] == "AML"
    assert payload["rule_evaluation"]["conditions_triggered"]


def test_alert_feed_endpoint_contract() -> None:
    response = _client().get("/v1/bank/alerts?limit=10", headers={"X-API-Key": "dev-connector-key"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] >= 2
    assert payload["items"][0]["alert_id"].startswith("ALERT-")
    assert payload["items"][0]["created_at"].endswith("Z")
    assert payload["items"][0]["source_event_id"]


def test_sanctions_hits_endpoint_contract() -> None:
    response = _client().get("/v1/bank/sanctions/hits/ALERT-002", headers={"X-API-Key": "dev-connector-key"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["alert_id"] == "ALERT-002"
    assert isinstance(payload["hits"], list)
    assert payload["hits"][0]["hit_id"] == "HIT-OFAC-7781"


def test_simulator_and_list_endpoints() -> None:
    client = _client()
    headers = {"X-API-Key": "dev-connector-key"}

    start_resp = client.post(
        "/v1/sim/start",
        headers=headers,
        json={
            "bank_id": "demo",
            "seed_customers": 20,
            "tx_per_tick": 5,
            "aml_alert_rate": 0.3,
            "sanctions_alert_rate": 0.1,
        },
    )
    assert start_resp.status_code == 200
    assert start_resp.json()["running"] is True

    tick_resp = client.post("/v1/sim/tick", headers=headers, json={"count": 2})
    assert tick_resp.status_code == 200
    assert tick_resp.json()["totals"]["transactions_generated"] >= 10

    customers_resp = client.get("/v1/bank/customers?limit=10", headers=headers)
    assert customers_resp.status_code == 200
    assert customers_resp.json()["count"] >= 2

    tx_resp = client.get("/v1/bank/transactions?limit=10", headers=headers)
    assert tx_resp.status_code == 200
    assert tx_resp.json()["count"] >= 1

    stop_resp = client.post("/v1/sim/stop", headers=headers)
    assert stop_resp.status_code == 200
    assert stop_resp.json()["running"] is False
