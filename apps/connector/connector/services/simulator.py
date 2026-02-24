from __future__ import annotations

import hashlib
import json
import random
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from connector.config import settings
from connector.db.models import Aggregate, Alert, Customer, SanctionsHit, Transaction
from connector.db.session import SessionLocal


def _utc_z(ts: datetime) -> str:
    return ts.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


def _stable_bank_seed(bank_id: str) -> int:
    digest = hashlib.sha256(bank_id.encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


def _bank_key(bank_id: str) -> str:
    digest = hashlib.sha1(bank_id.encode("utf-8")).hexdigest()  # nosec - non-cryptographic usage
    return digest[:6]


@dataclass(frozen=True)
class SimulatorConfig:
    seed_customers: int = 20
    tx_per_tick: int = 12
    aml_alert_rate: float = 0.2
    sanctions_alert_rate: float = 0.05


class BankSimulator:
    """Bank-scoped simulator that emits normal transactions and risk alerts."""

    def __init__(self, bank_id: str) -> None:
        self.bank_id = bank_id
        self._lock = threading.Lock()
        self._running = False
        self._config = SimulatorConfig()
        self._rng = random.Random(1024 + _stable_bank_seed(bank_id))
        self._id_counter = 0
        self._started_at: datetime | None = None
        self._last_tick_at: datetime | None = None
        self._tx_generated = 0
        self._alerts_generated = 0
        self._aml_alerts = 0
        self._sanctions_alerts = 0

    def is_running(self) -> bool:
        with self._lock:
            return self._running

    def start(
        self,
        seed_customers: int,
        tx_per_tick: int,
        aml_alert_rate: float,
        sanctions_alert_rate: float,
        reset_before_start: bool = True,
    ) -> dict[str, Any]:
        cfg = SimulatorConfig(
            seed_customers=max(1, int(seed_customers)),
            tx_per_tick=max(1, int(tx_per_tick)),
            aml_alert_rate=max(0.0, min(1.0, float(aml_alert_rate))),
            sanctions_alert_rate=max(0.0, min(1.0, float(sanctions_alert_rate))),
        )
        if reset_before_start:
            self.reset(seed_customers=0)
        self._ensure_seed_customers(target_count=cfg.seed_customers)
        with self._lock:
            self._config = cfg
            self._running = True
            self._started_at = datetime.utcnow()
        return self.status()

    def stop(self) -> dict[str, Any]:
        with self._lock:
            self._running = False
        return self.status()

    def reset(self, seed_customers: int = 0) -> dict[str, Any]:
        with self._lock:
            self._running = False
            self._started_at = None
            self._last_tick_at = None
            self._tx_generated = 0
            self._alerts_generated = 0
            self._aml_alerts = 0
            self._sanctions_alerts = 0
            self._id_counter = 0

        db = SessionLocal()
        try:
            db.query(SanctionsHit).filter(SanctionsHit.bank_id == self.bank_id).delete(synchronize_session=False)
            db.query(Alert).filter(Alert.bank_id == self.bank_id).delete(synchronize_session=False)
            db.query(Aggregate).filter(Aggregate.bank_id == self.bank_id).delete(synchronize_session=False)
            db.query(Transaction).filter(Transaction.bank_id == self.bank_id).delete(synchronize_session=False)
            db.query(Customer).filter(Customer.bank_id == self.bank_id).delete(synchronize_session=False)
            db.commit()
        finally:
            db.close()

        if seed_customers > 0:
            self._ensure_seed_customers(target_count=seed_customers)

        return self.status()

    def tick(self, count: int = 1) -> dict[str, Any]:
        loops = max(1, int(count))
        for _ in range(loops):
            self._run_tick()
        return self.status()

    def run_tick_once(self) -> None:
        # Used by the background manager loop; avoids per-tick status queries.
        self._run_tick()

    def status(self) -> dict[str, Any]:
        with self._lock:
            running = self._running
            cfg = self._config
            started_at = _utc_z(self._started_at) if self._started_at else None
            last_tick_at = _utc_z(self._last_tick_at) if self._last_tick_at else None
            tx_generated = self._tx_generated
            alerts_generated = self._alerts_generated
            aml_alerts = self._aml_alerts
            sanctions_alerts = self._sanctions_alerts

        db = SessionLocal()
        try:
            customer_count = len(db.scalars(select(Customer.customer_id).where(Customer.bank_id == self.bank_id)).all())
            tx_count = len(db.scalars(select(Transaction.transaction_id).where(Transaction.bank_id == self.bank_id)).all())
            alert_count = len(db.scalars(select(Alert.alert_id).where(Alert.bank_id == self.bank_id)).all())
            latest_alert = db.scalars(
                select(Alert).where(Alert.bank_id == self.bank_id).order_by(Alert.alert_id.desc())
            ).first()
            latest_alert_id = latest_alert.alert_id if latest_alert else None
        finally:
            db.close()

        return {
            "running": running,
            "config": {
                "bank_id": self.bank_id,
                "seed_customers": cfg.seed_customers,
                "tx_per_tick": cfg.tx_per_tick,
                "aml_alert_rate": cfg.aml_alert_rate,
                "sanctions_alert_rate": cfg.sanctions_alert_rate,
            },
            "started_at": started_at,
            "last_tick_at": last_tick_at,
            "totals": {
                "transactions_generated": tx_generated,
                "alerts_generated": alerts_generated,
                "aml_alerts_generated": aml_alerts,
                "sanctions_alerts_generated": sanctions_alerts,
                "customers_in_store": customer_count,
                "transactions_in_store": tx_count,
                "alerts_in_store": alert_count,
                "latest_alert_id": latest_alert_id,
            },
        }

    def _new_id(self, prefix: str) -> str:
        with self._lock:
            self._id_counter += 1
            counter = self._id_counter
        millis = int(time.time() * 1000)
        return f"{prefix}-{_bank_key(self.bank_id)}-{millis}-{counter:05d}"

    def _ensure_seed_customers(self, target_count: int) -> None:
        target = max(0, int(target_count))
        if target <= 0:
            return

        db = SessionLocal()
        try:
            rows = db.scalars(select(Customer).where(Customer.bank_id == self.bank_id)).all()
            if len(rows) >= target:
                return

            existing_ids = {row.customer_id for row in rows}
            add_count = target - len(rows)
            base_idx = len(rows) + 1

            segments = ["Retail", "Hospitality", "Construction", "Healthcare", "Logistics", "Food Services"]
            customer_types = ["Individual", "SMB"]
            risk_ratings = ["Low", "Medium", "High"]

            bank_key = _bank_key(self.bank_id)
            for i in range(add_count):
                idx = base_idx + i
                cid = f"CUST-SIM-{bank_key}-{idx:04d}"
                if cid in existing_ids:
                    continue
                db.add(
                    Customer(
                        customer_id=cid,
                        bank_id=self.bank_id,
                        snapshot={
                            "customer_id": cid,
                            "customer_type": self._rng.choice(customer_types),
                            "segment": self._rng.choice(segments),
                            "kyc_risk_rating": self._rng.choice(risk_ratings),
                            "edd": self._rng.choice([True, False]),
                            "prior_alerts_12m": self._rng.randint(0, 3),
                            "prior_sar_12m": self._rng.randint(0, 1),
                            "legal_name": f"Simulator Customer {idx}",
                            "country": self._rng.choice(["US", "US", "US", "GB", "AE"]),
                        },
                    )
                )

            db.commit()
        finally:
            db.close()

    def _run_tick(self) -> None:
        with self._lock:
            cfg = self._config

        self._ensure_seed_customers(target_count=cfg.seed_customers)

        db = SessionLocal()
        try:
            customers = db.scalars(select(Customer).where(Customer.bank_id == self.bank_id)).all()
            if not customers:
                return

            now = datetime.utcnow().replace(microsecond=0)
            generated_tx = 0
            generated_alerts = 0
            generated_aml = 0
            generated_sanctions = 0

            for _ in range(cfg.tx_per_tick):
                customer = self._rng.choice(customers)
                amount = round(self._rng.uniform(120, 4800), 2)
                tx = Transaction(
                    transaction_id=self._new_id("TX-SIM"),
                    bank_id=self.bank_id,
                    snapshot={
                        "transaction_id": "NOT PROVIDED",
                        "customer_id": customer.customer_id,
                        "type": self._rng.choice(["card_purchase", "wire_transfer", "ach_credit"]),
                        "amount": amount,
                        "currency": "USD",
                        "channel": self._rng.choice(["mobile", "online", "branch"]),
                        "occurred_at": _utc_z(now),
                        "description": "Simulator baseline activity",
                    },
                )
                tx.snapshot["transaction_id"] = tx.transaction_id
                db.add(tx)
                generated_tx += 1

            if self._rng.random() <= cfg.aml_alert_rate:
                customer = self._rng.choice(customers)
                burst_ids: list[str] = []
                burst_total = 0.0
                for _ in range(3):
                    amount = round(self._rng.uniform(8300, 9900), 2)
                    burst_total += amount
                    tx = Transaction(
                        transaction_id=self._new_id("TX-SIM"),
                        bank_id=self.bank_id,
                        snapshot={
                            "transaction_id": "NOT PROVIDED",
                            "customer_id": customer.customer_id,
                            "type": "cash_deposit",
                            "amount": amount,
                            "currency": "USD",
                            "channel": "branch",
                            "occurred_at": _utc_z(now),
                            "description": "Cash deposit near reporting threshold",
                        },
                    )
                    tx.snapshot["transaction_id"] = tx.transaction_id
                    burst_ids.append(tx.transaction_id)
                    db.add(tx)
                    generated_tx += 1

                rule = "STRUCTURING_RULE_03"
                agg = db.scalars(
                    select(Aggregate).where(
                        Aggregate.bank_id == self.bank_id,
                        Aggregate.customer_id == customer.customer_id,
                        Aggregate.rule_triggered == rule,
                        Aggregate.window_days == 7,
                    )
                ).first()
                if not agg:
                    agg = Aggregate(
                        bank_id=self.bank_id,
                        customer_id=customer.customer_id,
                        rule_triggered=rule,
                        window_days=7,
                        aggregates={
                            "cash_deposit_count_7d": 0,
                            "cash_deposit_total_7d": 0.0,
                            "max_single_cash_deposit_7d": 0.0,
                        },
                        linked_transactions=[],
                    )
                    db.add(agg)

                current_count = int(agg.aggregates.get("cash_deposit_count_7d", 0))
                current_total = float(agg.aggregates.get("cash_deposit_total_7d", 0.0))
                current_max = float(agg.aggregates.get("max_single_cash_deposit_7d", 0.0))

                current_count += len(burst_ids)
                current_total += burst_total
                current_max = max(current_max, burst_total / len(burst_ids))

                agg.aggregates = {
                    "cash_deposit_count_7d": current_count,
                    "cash_deposit_total_7d": round(current_total, 2),
                    "max_single_cash_deposit_7d": round(current_max, 2),
                }
                linked = list(agg.linked_transactions or [])
                linked.extend([{"transaction_id": txid, "description": "Cash deposit near threshold"} for txid in burst_ids])
                agg.linked_transactions = linked[-30:]

                alert_id = self._new_id("ALERT-SIM")
                source_event_id = f"{alert_id}:{_utc_z(now)}"
                alert = Alert(
                    alert_id=alert_id,
                    bank_id=self.bank_id,
                    alert_type="AML",
                    alert_metadata={
                        "source_system": "simulator",
                        "created_at": _utc_z(now),
                        "event_id": source_event_id,
                    },
                    rule_triggered=rule,
                    rule_description="Multiple cash deposits near threshold within short window.",
                    rule_thresholds={"cash_deposit_count_7d": 3, "cash_deposit_total_7d": 20000},
                    rule_evaluation={
                        "conditions_triggered": [
                            {
                                "field": "historical_aggregates.cash_deposit_count_7d",
                                "operator": ">=",
                                "threshold": 3,
                                "actual": current_count,
                                "window_days": 7,
                            },
                            {
                                "field": "historical_aggregates.cash_deposit_total_7d",
                                "operator": ">=",
                                "threshold": 20000,
                                "actual": round(current_total, 2),
                                "window_days": 7,
                            },
                        ]
                    },
                    transaction_id=burst_ids[-1],
                    customer_id=customer.customer_id,
                    sanctions_hit_preview=None,
                )
                db.add(alert)
                generated_alerts += 1
                generated_aml += 1
                self._notify_core(alert_id=alert_id, source_event_id=source_event_id, created_at=_utc_z(now))

            if self._rng.random() <= cfg.sanctions_alert_rate:
                customer = self._rng.choice(customers)
                if not customer.snapshot.get("legal_name"):
                    customer.snapshot["legal_name"] = f"Customer {customer.customer_id}"
                score = round(self._rng.uniform(0.88, 0.97), 2)
                alert_id = self._new_id("ALERT-SIM")
                source_event_id = f"{alert_id}:{_utc_z(now)}"
                alert = Alert(
                    alert_id=alert_id,
                    bank_id=self.bank_id,
                    alert_type="SANCTIONS",
                    alert_metadata={
                        "source_system": "simulator",
                        "created_at": _utc_z(now),
                        "event_id": source_event_id,
                    },
                    rule_triggered="OFAC_NAME_SCREEN_MATCH",
                    rule_description="Simulated high-confidence OFAC name match.",
                    rule_thresholds={"score_threshold": 0.85},
                    rule_evaluation={
                        "conditions_triggered": [
                            {
                                "field": "screening.score",
                                "operator": ">=",
                                "threshold": 0.85,
                                "actual": score,
                                "window_days": None,
                            }
                        ]
                    },
                    transaction_id=None,
                    customer_id=customer.customer_id,
                    sanctions_hit_preview={"hit_id": self._new_id("HIT-SIM"), "score": score},
                )
                db.add(alert)
                db.add(
                    SanctionsHit(
                        bank_id=self.bank_id,
                        alert_id=alert_id,
                        hit_id=self._new_id("HIT-SIM"),
                        list_source=self._rng.choice(["OFAC SDN", "OFAC Consolidated"]),
                        matched_fields=["full_name", "country"],
                        score=score,
                        features={"name_similarity": round(score + 0.02, 2), "country_match": True},
                        prior_decision="NOT PROVIDED",
                    )
                )
                generated_alerts += 1
                generated_sanctions += 1
                self._notify_core(alert_id=alert_id, source_event_id=source_event_id, created_at=_utc_z(now))

            db.commit()
        finally:
            db.close()

        with self._lock:
            self._last_tick_at = datetime.utcnow()
            self._tx_generated += generated_tx
            self._alerts_generated += generated_alerts
            self._aml_alerts += generated_aml
            self._sanctions_alerts += generated_sanctions

    def _notify_core(self, alert_id: str, source_event_id: str, created_at: str) -> None:
        callback = settings.core_alert_callback_url
        if not callback:
            return
        payload = json.dumps(
            {
                "bank_id": self.bank_id,
                "alert_id": alert_id,
                "source_event_id": source_event_id,
                "created_at": created_at,
            }
        ).encode("utf-8")
        url = f"{callback.rstrip('/')}/v1/alerts/events"
        request = urllib.request.Request(
            url=url,
            method="POST",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=2.0):
                pass
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
            return


class SimulatorManager:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._sims: dict[str, BankSimulator] = {}

    def ensure_thread_started(self) -> None:
        with self._lock:
            if self._thread and self._thread.is_alive():
                return
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._run_loop, name="connector-simulator", daemon=True)
            self._thread.start()

    def shutdown(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

    def _get_sim(self, bank_id: str) -> BankSimulator:
        with self._lock:
            sim = self._sims.get(bank_id)
            if sim:
                return sim
            sim = BankSimulator(bank_id=bank_id)
            self._sims[bank_id] = sim
            return sim

    def status(self, bank_id: str) -> dict[str, Any]:
        return self._get_sim(bank_id).status()

    def start(self, **kwargs: Any) -> dict[str, Any]:
        bank_id = str(kwargs.get("bank_id") or "demo")
        self.ensure_thread_started()
        sim = self._get_sim(bank_id)
        return sim.start(
            seed_customers=int(kwargs.get("seed_customers", 20)),
            tx_per_tick=int(kwargs.get("tx_per_tick", 12)),
            aml_alert_rate=float(kwargs.get("aml_alert_rate", 0.2)),
            sanctions_alert_rate=float(kwargs.get("sanctions_alert_rate", 0.05)),
            reset_before_start=bool(kwargs.get("reset_before_start", True)),
        )

    def stop(self, bank_id: str) -> dict[str, Any]:
        return self._get_sim(bank_id).stop()

    def tick(self, bank_id: str, count: int = 1) -> dict[str, Any]:
        return self._get_sim(bank_id).tick(count=count)

    def reset(self, bank_id: str, seed_customers: int = 0) -> dict[str, Any]:
        return self._get_sim(bank_id).reset(seed_customers=seed_customers)

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            sims: list[BankSimulator] = []
            with self._lock:
                sims = list(self._sims.values())
            for sim in sims:
                if sim.is_running():
                    sim.run_tick_once()
            time.sleep(1.0)


simulator_engine = SimulatorManager()
