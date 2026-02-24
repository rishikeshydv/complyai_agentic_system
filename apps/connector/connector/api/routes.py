from __future__ import annotations

from datetime import datetime, timezone
import uuid
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from connector.db.models import Aggregate, Alert, Customer, SanctionsHit, Transaction
from connector.db.session import get_db
from connector.schemas.shared_loader import validate_against_schema
from connector.services.allowlist_service import load_allowlist
from connector.services.audit_service import log_fetch
from connector.services.auth import verify_connector_auth
from connector.services.simulator import simulator_engine
from connector.utils.allowlist import filter_with_allowlist
from connector.utils.request_context import request_id_ctx

router = APIRouter(prefix="/v1/bank", tags=["bank"])
sim_router = APIRouter(prefix="/v1/sim", tags=["simulator"])


class SimulatorStartRequest(BaseModel):
    bank_id: str = "demo"
    seed_customers: int = Field(default=20, ge=1, le=200)
    tx_per_tick: int = Field(default=12, ge=1, le=100)
    aml_alert_rate: float = Field(default=0.2, ge=0, le=1)
    sanctions_alert_rate: float = Field(default=0.05, ge=0, le=1)
    reset_before_start: bool = True


class SimulatorTickRequest(BaseModel):
    count: int = Field(default=1, ge=1, le=50)


class DemoEmitRequest(BaseModel):
    bank_id: str = Field(default="demo", min_length=1)
    kind: Literal["AML", "SANCTIONS"]


def _parse_iso8601(value: str | None) -> datetime | None:
    if not value:
        return None
    raw = value.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def _as_utc_z(value: datetime) -> str:
    return value.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


def _alert_created_at(alert: Alert) -> datetime:
    meta = alert.alert_metadata if isinstance(alert.alert_metadata, dict) else {}
    created_raw = meta.get("created_at")
    parsed = _parse_iso8601(created_raw)
    if parsed:
        return parsed
    return datetime.utcnow()


def _tx_created_at(tx: Transaction) -> datetime:
    snap = tx.snapshot if isinstance(tx.snapshot, dict) else {}
    occurred = snap.get("occurred_at")
    parsed = _parse_iso8601(occurred)
    if parsed:
        return parsed
    return datetime.utcnow()


@router.get("/alerts")
def list_alerts(
    request: Request,
    bank_id: str = Header(default="demo", alias="X-Bank-ID"),
    created_after: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    _: None = Depends(verify_connector_auth),
    db: Session = Depends(get_db),
):
    cutoff = _parse_iso8601(created_after)
    if created_after and cutoff is None:
        raise HTTPException(status_code=400, detail="created_after must be ISO datetime")

    rows = db.scalars(select(Alert).where(Alert.bank_id == bank_id)).all()
    items: list[dict] = []
    item_allowlist = load_allowlist().get("alert_feed_item", [])

    for row in rows:
        created_at = _alert_created_at(row)
        if cutoff and created_at <= cutoff:
            continue

        meta = row.alert_metadata if isinstance(row.alert_metadata, dict) else {}
        source_event_id = str(meta.get("event_id") or f"{row.alert_id}:{_as_utc_z(created_at)}")

        item = {
            "alert_id": row.alert_id,
            "alert_type": row.alert_type,
            "rule_triggered": row.rule_triggered,
            "customer_id": row.customer_id,
            "transaction_id": row.transaction_id,
            "created_at": _as_utc_z(created_at),
            "source_event_id": source_event_id,
        }
        items.append(filter_with_allowlist(item, item_allowlist))

    items.sort(key=lambda x: (x.get("created_at", ""), x.get("alert_id", "")))
    payload = {"items": items[:limit], "count": len(items[:limit])}
    validate_against_schema("connector_alert_feed.schema.json", payload)

    log_fetch(
        db,
        request_id_ctx.get(),
        str(request.url.path),
        {"bank_id": bank_id, "created_after": created_after, "limit": limit},
    )
    return payload


@router.get("/alerts/{alert_id}")
def get_alert(
    alert_id: str,
    request: Request,
    bank_id: str = Header(default="demo", alias="X-Bank-ID"),
    _: None = Depends(verify_connector_auth),
    db: Session = Depends(get_db),
):
    alert = db.scalars(select(Alert).where(Alert.alert_id == alert_id, Alert.bank_id == bank_id)).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    payload = {
        "alert_id": alert.alert_id,
        "alert_type": alert.alert_type,
        "alert_metadata": alert.alert_metadata,
        "rule_triggered": alert.rule_triggered,
        "rule_description": alert.rule_description,
        "rule_thresholds": alert.rule_thresholds,
        "rule_evaluation": alert.rule_evaluation,
        "transaction_id": alert.transaction_id,
        "customer_id": alert.customer_id,
        "sanctions_hit_preview": alert.sanctions_hit_preview,
    }

    allowlist = load_allowlist().get("alerts", [])
    payload = filter_with_allowlist(payload, allowlist)
    validate_against_schema("connector_alert.schema.json", payload)

    log_fetch(
        db,
        request_id_ctx.get(),
        str(request.url.path),
        {"bank_id": bank_id, "alert_id": alert_id},
    )
    return payload


@router.get("/transactions")
def list_transactions(
    request: Request,
    bank_id: str = Header(default="demo", alias="X-Bank-ID"),
    customer_id: str | None = Query(default=None),
    created_after: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    _: None = Depends(verify_connector_auth),
    db: Session = Depends(get_db),
):
    cutoff = _parse_iso8601(created_after)
    if created_after and cutoff is None:
        raise HTTPException(status_code=400, detail="created_after must be ISO datetime")

    rows = db.scalars(select(Transaction).where(Transaction.bank_id == bank_id)).all()
    rows.sort(key=_tx_created_at, reverse=True)

    tx_allowlist = load_allowlist().get("transactions", [])
    items: list[dict] = []
    for row in rows:
        payload = {"transaction_id": row.transaction_id, "snapshot": row.snapshot}
        payload = filter_with_allowlist(payload, tx_allowlist)
        snap = payload.get("snapshot", {}) if isinstance(payload, dict) else {}

        if customer_id and str(snap.get("customer_id")) != customer_id:
            continue
        if cutoff:
            occurred_at = _tx_created_at(row)
            if occurred_at <= cutoff:
                continue
        items.append(payload)
        if len(items) >= limit:
            break

    log_fetch(
        db,
        request_id_ctx.get(),
        str(request.url.path),
        {"bank_id": bank_id, "customer_id": customer_id, "created_after": created_after, "limit": limit},
    )
    return {"items": items, "count": len(items)}


@router.get("/transactions/{transaction_id}")
def get_transaction(
    transaction_id: str,
    request: Request,
    bank_id: str = Header(default="demo", alias="X-Bank-ID"),
    _: None = Depends(verify_connector_auth),
    db: Session = Depends(get_db),
):
    tx = db.scalars(select(Transaction).where(Transaction.transaction_id == transaction_id, Transaction.bank_id == bank_id)).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    payload = {"transaction_id": tx.transaction_id, "snapshot": tx.snapshot}
    allowlist = load_allowlist().get("transactions", [])
    payload = filter_with_allowlist(payload, allowlist)
    validate_against_schema("connector_transaction.schema.json", payload)

    log_fetch(
        db,
        request_id_ctx.get(),
        str(request.url.path),
        {"bank_id": bank_id, "transaction_id": transaction_id},
    )
    return payload


@router.get("/customers")
def list_customers(
    request: Request,
    bank_id: str = Header(default="demo", alias="X-Bank-ID"),
    segment: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    _: None = Depends(verify_connector_auth),
    db: Session = Depends(get_db),
):
    rows = db.scalars(select(Customer).where(Customer.bank_id == bank_id)).all()
    rows.sort(key=lambda c: c.customer_id)
    customer_allowlist = load_allowlist().get("customers", [])

    items: list[dict] = []
    for row in rows:
        payload = {"customer_id": row.customer_id, "snapshot": row.snapshot}
        payload = filter_with_allowlist(payload, customer_allowlist)
        if segment and str(payload.get("snapshot", {}).get("segment")) != segment:
            continue
        items.append(payload)
        if len(items) >= limit:
            break

    log_fetch(
        db,
        request_id_ctx.get(),
        str(request.url.path),
        {"bank_id": bank_id, "segment": segment, "limit": limit},
    )
    return {"items": items, "count": len(items)}


@router.get("/customers/{customer_id}")
def get_customer(
    customer_id: str,
    request: Request,
    bank_id: str = Header(default="demo", alias="X-Bank-ID"),
    _: None = Depends(verify_connector_auth),
    db: Session = Depends(get_db),
):
    customer = db.scalars(select(Customer).where(Customer.customer_id == customer_id, Customer.bank_id == bank_id)).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    payload = {"customer_id": customer.customer_id, "snapshot": customer.snapshot}
    allowlist = load_allowlist().get("customers", [])
    payload = filter_with_allowlist(payload, allowlist)
    validate_against_schema("connector_customer.schema.json", payload)

    log_fetch(
        db,
        request_id_ctx.get(),
        str(request.url.path),
        {"bank_id": bank_id, "customer_id": customer_id},
    )
    return payload


@router.get("/aggregates")
def get_aggregates(
    request: Request,
    bank_id: str = Header(default="demo", alias="X-Bank-ID"),
    customer_id: str = Query(...),
    rule_triggered: str = Query(...),
    window_days: int | None = Query(default=None),
    _: None = Depends(verify_connector_auth),
    db: Session = Depends(get_db),
):
    query = select(Aggregate).where(
        Aggregate.bank_id == bank_id,
        Aggregate.customer_id == customer_id,
        Aggregate.rule_triggered == rule_triggered,
    )
    if window_days is not None:
        query = query.where(Aggregate.window_days == window_days)

    row = db.scalars(query).first()
    if not row:
        raise HTTPException(status_code=404, detail="Aggregates not found")

    payload = {
        "customer_id": row.customer_id,
        "rule_triggered": row.rule_triggered,
        "window_days": row.window_days,
        "aggregates": row.aggregates,
        "linked_transactions": row.linked_transactions,
    }
    allowlist = load_allowlist().get("aggregates", [])
    payload = filter_with_allowlist(payload, allowlist)
    validate_against_schema("connector_aggregates.schema.json", payload)

    log_fetch(
        db,
        request_id_ctx.get(),
        str(request.url.path),
        {
            "bank_id": bank_id,
            "customer_id": customer_id,
            "rule_triggered": rule_triggered,
            "window_days": window_days,
        },
    )
    return payload


@router.get("/sanctions/hits/{alert_id}")
def get_sanctions_hits(
    alert_id: str,
    request: Request,
    bank_id: str = Header(default="demo", alias="X-Bank-ID"),
    _: None = Depends(verify_connector_auth),
    db: Session = Depends(get_db),
):
    rows = db.scalars(
        select(SanctionsHit).where(SanctionsHit.alert_id == alert_id, SanctionsHit.bank_id == bank_id)
    ).all()

    payload = {
        "alert_id": alert_id,
        "hits": [
            {
                "hit_id": row.hit_id,
                "list_source": row.list_source,
                "matched_fields": row.matched_fields,
                "score": row.score,
                "features": row.features,
                "prior_decision": row.prior_decision,
            }
            for row in rows
        ],
    }

    allowlist = load_allowlist().get("sanctions_hits", [])
    payload = filter_with_allowlist(payload, allowlist)
    validate_against_schema("connector_sanctions_hit.schema.json", payload)

    log_fetch(
        db,
        request_id_ctx.get(),
        str(request.url.path),
        {"bank_id": bank_id, "alert_id": alert_id},
    )
    return payload


@sim_router.get("/status")
def simulator_status(
    request: Request,
    bank_id: str = Header(default="demo", alias="X-Bank-ID"),
    _: None = Depends(verify_connector_auth),
    db: Session = Depends(get_db),
):
    log_fetch(db, request_id_ctx.get(), str(request.url.path), {"bank_id": bank_id})
    return simulator_engine.status(bank_id=bank_id)


@sim_router.post("/start")
def simulator_start(
    payload: SimulatorStartRequest,
    request: Request,
    _: None = Depends(verify_connector_auth),
    db: Session = Depends(get_db),
):
    log_fetch(db, request_id_ctx.get(), str(request.url.path), payload.model_dump())
    return simulator_engine.start(**payload.model_dump())


@sim_router.post("/stop")
def simulator_stop(
    request: Request,
    bank_id: str = Header(default="demo", alias="X-Bank-ID"),
    _: None = Depends(verify_connector_auth),
    db: Session = Depends(get_db),
):
    log_fetch(db, request_id_ctx.get(), str(request.url.path), {"bank_id": bank_id})
    return simulator_engine.stop(bank_id=bank_id)


@sim_router.post("/tick")
def simulator_tick(
    payload: SimulatorTickRequest,
    request: Request,
    bank_id: str = Header(default="demo", alias="X-Bank-ID"),
    _: None = Depends(verify_connector_auth),
    db: Session = Depends(get_db),
):
    log_fetch(db, request_id_ctx.get(), str(request.url.path), {"bank_id": bank_id, **payload.model_dump()})
    return simulator_engine.tick(bank_id=bank_id, count=payload.count)


@sim_router.post("/emit")
def simulator_emit_demo_alert(
    payload: DemoEmitRequest,
    request: Request,
    _: None = Depends(verify_connector_auth),
    db: Session = Depends(get_db),
):
    """
    Emit exactly one alert + supporting objects for a bank-scoped demo.

    This is used by core-api for 1-click demo case generation.
    """
    log_fetch(db, request_id_ctx.get(), str(request.url.path), payload.model_dump())

    now = datetime.utcnow().replace(microsecond=0)
    created_at = _as_utc_z(now)
    bank_id = payload.bank_id
    suffix = uuid.uuid4().hex[:10]

    if payload.kind == "AML":
        customer_id = f"CUST-DEMO-{suffix}"
        tx_ids: list[str] = []
        amounts = [9100.0, 9400.0, 9600.0]
        for idx, amt in enumerate(amounts, start=1):
            tx_id = f"TX-DEMO-{suffix}-{idx}"
            tx_ids.append(tx_id)
            db.add(
                Transaction(
                    transaction_id=tx_id,
                    bank_id=bank_id,
                    snapshot={
                        "transaction_id": tx_id,
                        "customer_id": customer_id,
                        "type": "cash_deposit",
                        "amount": amt,
                        "currency": "USD",
                        "channel": "branch",
                        "occurred_at": created_at,
                        "description": "Demo cash deposits near reporting threshold",
                    },
                )
            )

        db.add(
            Customer(
                customer_id=customer_id,
                bank_id=bank_id,
                snapshot={
                    "customer_id": customer_id,
                    "customer_type": "SMB",
                    "segment": "Hospitality",
                    "kyc_risk_rating": "High",
                    "edd": True,
                    "prior_alerts_12m": 1,
                    "prior_sar_12m": 0,
                    "legal_name": "Demo Hospitality Group LLC",
                    "country": "US",
                },
            )
        )

        rule = "STRUCTURING_RULE_03"
        window_days = 7
        db.add(
            Aggregate(
                bank_id=bank_id,
                customer_id=customer_id,
                rule_triggered=rule,
                window_days=window_days,
                aggregates={
                    "cash_deposit_count_7d": 3,
                    "cash_deposit_total_7d": round(sum(amounts), 2),
                    "max_single_cash_deposit_7d": max(amounts),
                },
                linked_transactions=[{"transaction_id": t, "description": "Cash deposit near threshold"} for t in tx_ids],
            )
        )

        alert_id = f"ALERT-DEMO-AML-{suffix}"
        source_event_id = f"{alert_id}:{created_at}"
        db.add(
            Alert(
                alert_id=alert_id,
                bank_id=bank_id,
                alert_type="AML",
                alert_metadata={"source_system": "demo-emit", "created_at": created_at, "event_id": source_event_id},
                rule_triggered=rule,
                rule_description="Multiple cash deposits near the reporting threshold within a short window.",
                rule_thresholds={"cash_deposit_count_7d": 3, "cash_deposit_total_7d": 20000},
                rule_evaluation={
                    "conditions_triggered": [
                        {
                            "field": "historical_aggregates.cash_deposit_count_7d",
                            "operator": ">=",
                            "threshold": 3,
                            "actual": 3,
                            "window_days": window_days,
                        },
                        {
                            "field": "historical_aggregates.cash_deposit_total_7d",
                            "operator": ">=",
                            "threshold": 20000,
                            "actual": round(sum(amounts), 2),
                            "window_days": window_days,
                        },
                    ]
                },
                transaction_id=tx_ids[-1],
                customer_id=customer_id,
                sanctions_hit_preview=None,
            )
        )
        db.commit()
        return {"alert_id": alert_id}

    customer_id = f"CUST-DEMO-{suffix}"
    db.add(
        Customer(
            customer_id=customer_id,
            bank_id=bank_id,
            snapshot={
                "customer_id": customer_id,
                "customer_type": "Individual",
                "segment": "Retail",
                "kyc_risk_rating": "Medium",
                "edd": False,
                "prior_alerts_12m": 0,
                "prior_sar_12m": 0,
                "legal_name": "Demo Sanctions Candidate",
                "country": "AE",
            },
        )
    )

    rule = "OFAC_NAME_SCREEN_MATCH"
    score = 0.93
    db.add(
        Aggregate(
            bank_id=bank_id,
            customer_id=customer_id,
            rule_triggered=rule,
            window_days=None,
            aggregates={"recent_screening_matches_30d": 1, "max_screening_score_30d": score},
            linked_transactions=[],
        )
    )

    alert_id = f"ALERT-DEMO-SANCTIONS-{suffix}"
    source_event_id = f"{alert_id}:{created_at}"
    hit_id = f"HIT-DEMO-{suffix}"
    db.add(
        Alert(
            alert_id=alert_id,
            bank_id=bank_id,
            alert_type="SANCTIONS",
            alert_metadata={"source_system": "demo-emit", "created_at": created_at, "event_id": source_event_id},
            rule_triggered=rule,
            rule_description="High-confidence sanctions screening name match.",
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
            customer_id=customer_id,
            sanctions_hit_preview={"hit_id": hit_id, "score": score},
        )
    )
    db.add(
        SanctionsHit(
            bank_id=bank_id,
            alert_id=alert_id,
            hit_id=hit_id,
            list_source="OFAC SDN",
            matched_fields=["full_name", "country"],
            score=score,
            features={"name_similarity": 0.96, "country_match": True},
            prior_decision="NOT PROVIDED",
        )
    )
    db.commit()
    return {"alert_id": alert_id}
