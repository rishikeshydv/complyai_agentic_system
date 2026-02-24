from __future__ import annotations

import hashlib
import hmac
import time
from typing import Any

import httpx

from core.config import settings
from core.utils.request_context import request_id_ctx


class ConnectorClient:
    def __init__(self, base_url: str | None = None):
        self.base_url = (base_url or settings.connector_base_url).rstrip("/")
        self.bank_url_map = {k: v.rstrip("/") for k, v in settings.connector_bank_url_map.items()}

    def _base_for_bank(self, bank_id: str | None) -> str:
        if bank_id and bank_id in self.bank_url_map:
            return self.bank_url_map[bank_id]
        return self.base_url

    def _signature(self, method: str, path: str, ts: str) -> str:
        payload = f"{method}\n{path}\n{ts}\n"
        return hmac.new(settings.connector_signed_secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()

    def _headers(self, method: str, path: str, bank_id: str | None = None) -> dict[str, str]:
        headers = {
            "X-API-Key": settings.connector_api_key,
            "X-Request-ID": request_id_ctx.get() or "",
        }
        if bank_id:
            # Simulator + multi-tenant demo connector can scope reads/writes per bank.
            headers["X-Bank-ID"] = bank_id
        if settings.connector_require_signed:
            ts = str(int(time.time()))
            headers["X-Signature-Timestamp"] = ts
            headers["X-Signature"] = self._signature(method, path, ts)
        return headers

    def _get(self, path: str, params: dict[str, Any] | None = None, bank_id: str | None = None) -> dict[str, Any]:
        url = f"{self._base_for_bank(bank_id)}{path}"
        with httpx.Client(timeout=20.0) as client:
            response = client.get(url, params=params, headers=self._headers("GET", path, bank_id=bank_id))
        response.raise_for_status()
        return response.json()

    def fetch_alert(self, alert_id: str, bank_id: str | None = None) -> dict[str, Any]:
        return self._get(f"/v1/bank/alerts/{alert_id}", bank_id=bank_id)

    def fetch_alert_feed(
        self,
        created_after: str | None = None,
        limit: int = 100,
        bank_id: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"limit": limit}
        if created_after:
            params["created_after"] = created_after
        return self._get("/v1/bank/alerts", params=params, bank_id=bank_id)

    def fetch_transaction(self, transaction_id: str, bank_id: str | None = None) -> dict[str, Any]:
        return self._get(f"/v1/bank/transactions/{transaction_id}", bank_id=bank_id)

    def fetch_customer(self, customer_id: str, bank_id: str | None = None) -> dict[str, Any]:
        return self._get(f"/v1/bank/customers/{customer_id}", bank_id=bank_id)

    def fetch_aggregates(
        self,
        customer_id: str,
        rule_triggered: str,
        window_days: int | None,
        bank_id: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"customer_id": customer_id, "rule_triggered": rule_triggered}
        if window_days is not None:
            params["window_days"] = window_days
        return self._get("/v1/bank/aggregates", params=params, bank_id=bank_id)

    def fetch_sanctions_hits(self, alert_id: str, bank_id: str | None = None) -> dict[str, Any]:
        return self._get(f"/v1/bank/sanctions/hits/{alert_id}", bank_id=bank_id)

    def fetch_transactions(
        self,
        customer_id: str | None = None,
        created_after: str | None = None,
        limit: int = 100,
        bank_id: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"limit": limit}
        if customer_id:
            params["customer_id"] = customer_id
        if created_after:
            params["created_after"] = created_after
        return self._get("/v1/bank/transactions", params=params, bank_id=bank_id)

    def fetch_customers(
        self,
        segment: str | None = None,
        limit: int = 100,
        bank_id: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"limit": limit}
        if segment:
            params["segment"] = segment
        return self._get("/v1/bank/customers", params=params, bank_id=bank_id)

    def simulator_status(self, bank_id: str | None = None) -> dict[str, Any]:
        return self._get("/v1/sim/status", bank_id=bank_id)

    def simulator_start(
        self,
        bank_id: str = "demo",
        seed_customers: int = 20,
        tx_per_tick: int = 12,
        aml_alert_rate: float = 0.2,
        sanctions_alert_rate: float = 0.05,
        reset_before_start: bool = True,
    ) -> dict[str, Any]:
        path = "/v1/sim/start"
        url = f"{self._base_for_bank(bank_id)}{path}"
        payload = {
            "bank_id": bank_id,
            "seed_customers": seed_customers,
            "tx_per_tick": tx_per_tick,
            "aml_alert_rate": aml_alert_rate,
            "sanctions_alert_rate": sanctions_alert_rate,
            "reset_before_start": reset_before_start,
        }
        with httpx.Client(timeout=20.0) as client:
            response = client.post(url, json=payload, headers=self._headers("POST", path, bank_id=bank_id))
        response.raise_for_status()
        return response.json()

    def simulator_stop(self, bank_id: str = "demo") -> dict[str, Any]:
        path = "/v1/sim/stop"
        url = f"{self._base_for_bank(bank_id)}{path}"
        with httpx.Client(timeout=20.0) as client:
            response = client.post(url, headers=self._headers("POST", path, bank_id=bank_id))
        response.raise_for_status()
        return response.json()

    def simulator_tick(self, count: int = 1, bank_id: str = "demo") -> dict[str, Any]:
        path = "/v1/sim/tick"
        url = f"{self._base_for_bank(bank_id)}{path}"
        with httpx.Client(timeout=20.0) as client:
            response = client.post(url, json={"count": count}, headers=self._headers("POST", path, bank_id=bank_id))
        response.raise_for_status()
        return response.json()

    def emit_demo_alert(self, kind: str, bank_id: str = "demo") -> dict[str, Any]:
        path = "/v1/sim/emit"
        url = f"{self._base_for_bank(bank_id)}{path}"
        payload = {"bank_id": bank_id, "kind": kind}
        with httpx.Client(timeout=20.0) as client:
            response = client.post(url, json=payload, headers=self._headers("POST", path, bank_id=bank_id))
        response.raise_for_status()
        return response.json()
