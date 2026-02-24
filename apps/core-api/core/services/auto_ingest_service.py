from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.config import settings
from core.db.models import AlertIngestEvent, ConnectorPollState
from core.services.connector_client import ConnectorClient
from core.services.governance_service import append_audit_event
from core.services.orchestrator import OrchestratorService
from core.utils.schema_loader import validate_json


class AutoIngestService:
    def __init__(
        self,
        connector_client: ConnectorClient | None = None,
        orchestrator_factory: Callable[[], OrchestratorService] | None = None,
    ) -> None:
        self.connector = connector_client or ConnectorClient()
        self.orchestrator_factory = orchestrator_factory or OrchestratorService

    @staticmethod
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

    @staticmethod
    def _as_utc_z(value: datetime) -> str:
        return value.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")

    @staticmethod
    def _connector_call(method, bank_id: str, **kwargs: Any) -> dict[str, Any]:
        try:
            return method(bank_id=bank_id, **kwargs)
        except TypeError:
            return method(**kwargs)

    @staticmethod
    def _resolved_bank_ids() -> list[str]:
        configured = sorted(settings.connector_bank_url_map.keys())
        if configured:
            return configured
        return ["demo"]

    def _get_or_create_state(self, db: Session, bank_id: str) -> ConnectorPollState:
        state = db.get(ConnectorPollState, bank_id)
        if state:
            return state
        state = ConnectorPollState(bank_id=bank_id, last_seen_created_at=None)
        db.add(state)
        db.commit()
        db.refresh(state)
        return state

    def dispatch_alert_event(
        self,
        db: Session,
        bank_id: str,
        alert_id: str,
        source_event_id: str,
        event_created_at: datetime | str | None,
        actor_id: str,
    ) -> tuple[bool, str | None]:
        if isinstance(event_created_at, str):
            event_created_at = self._parse_iso8601(event_created_at)

        ingest = AlertIngestEvent(
            bank_id=bank_id,
            alert_id=alert_id,
            source_event_id=source_event_id,
            event_created_at=event_created_at or datetime.utcnow(),
            status="QUEUED",
        )
        db.add(ingest)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            return False, None

        db.refresh(ingest)

        orchestrator = self.orchestrator_factory()
        workflow = orchestrator.create_workflow_run(
            db,
            alert_id=alert_id,
            bank_id=bank_id,
            request_id=f"auto-ingest:{source_event_id}",
        )

        ingest.workflow_run_id = workflow.workflow_run_id
        db.add(ingest)
        db.commit()

        append_audit_event(
            db,
            case_id=None,
            workflow_run_id=workflow.workflow_run_id,
            actor_type="SYSTEM",
            actor_id=actor_id,
            action="AUTO_INGEST_QUEUED",
            notes=f"Queued background case generation for alert {alert_id}",
            metadata={"bank_id": bank_id, "source_event_id": source_event_id},
        )

        if settings.celery_task_always_eager:
            try:
                case_row = orchestrator.pull_and_generate_case(
                    db=db,
                    alert_id=alert_id,
                    bank_id=bank_id,
                    workflow_run_id=workflow.workflow_run_id,
                    actor_id=actor_id,
                )
                mark_ingest_event_by_workflow(
                    db,
                    workflow_run_id=workflow.workflow_run_id,
                    status="COMPLETED",
                    case_id=case_row.case_id,
                )
            except Exception as exc:  # pragma: no cover - guarded by tests for happy path
                mark_ingest_event_by_workflow(
                    db,
                    workflow_run_id=workflow.workflow_run_id,
                    status="FAILED",
                    error_message=str(exc),
                )
                append_audit_event(
                    db,
                    case_id=None,
                    workflow_run_id=workflow.workflow_run_id,
                    actor_type="SYSTEM",
                    actor_id=actor_id,
                    action="AUTO_INGEST_FAILED",
                    notes=str(exc),
                    metadata={"bank_id": bank_id, "alert_id": alert_id},
                )
                return True, str(exc)
        else:
            from core.celery_app import celery_app

            try:
                celery_app.send_task(
                    "pull_and_generate_case",
                    kwargs={
                        "alert_id": alert_id,
                        "bank_id": bank_id,
                        "workflow_run_id": workflow.workflow_run_id,
                    },
                )
            except Exception as exc:
                mark_ingest_event_by_workflow(
                    db,
                    workflow_run_id=workflow.workflow_run_id,
                    status="FAILED",
                    error_message=str(exc),
                )
                append_audit_event(
                    db,
                    case_id=None,
                    workflow_run_id=workflow.workflow_run_id,
                    actor_type="SYSTEM",
                    actor_id=actor_id,
                    action="AUTO_INGEST_FAILED",
                    notes=str(exc),
                    metadata={"bank_id": bank_id, "alert_id": alert_id},
                )
                return True, str(exc)

        return True, None

    def poll_and_dispatch(self, db: Session, actor_id: str = "auto-ingest") -> dict[str, Any]:
        if not settings.auto_ingest_enabled:
            return {
                "enabled": False,
                "queued": 0,
                "deduped": 0,
                "errors": 0,
                "discovered": 0,
                "banks": [],
            }

        queued = 0
        deduped = 0
        errors = 0
        discovered = 0
        details: list[dict[str, Any]] = []

        for bank_id in self._resolved_bank_ids():
            state = self._get_or_create_state(db, bank_id)
            created_after = None
            if state.last_seen_created_at:
                overlap = max(settings.auto_ingest_overlap_seconds, 0)
                watermark = state.last_seen_created_at - timedelta(seconds=overlap)
                created_after = self._as_utc_z(watermark)

            try:
                payload = self._connector_call(
                    self.connector.fetch_alert_feed,
                    bank_id=bank_id,
                    created_after=created_after,
                    limit=settings.auto_ingest_batch_size,
                )
                validate_json("connector_alert_feed.schema.json", payload)
            except Exception as exc:
                errors += 1
                details.append(
                    {
                        "bank_id": bank_id,
                        "queued": 0,
                        "deduped": 0,
                        "errors": 1,
                        "discovered": 0,
                        "error": str(exc),
                    }
                )
                continue

            items = list(payload.get("items", []))
            items.sort(key=lambda x: (x.get("created_at", ""), x.get("alert_id", "")))

            bank_queued = 0
            bank_deduped = 0
            bank_errors = 0
            bank_discovered = len(items)
            discovered += bank_discovered

            max_seen = state.last_seen_created_at

            for item in items:
                alert_id = str(item.get("alert_id") or "")
                if not alert_id:
                    bank_errors += 1
                    errors += 1
                    continue

                created_at_str = item.get("created_at")
                event_created_at = self._parse_iso8601(created_at_str) or datetime.utcnow()
                source_event_id = str(item.get("source_event_id") or f"{alert_id}:{created_at_str or 'NOT PROVIDED'}")

                ok, dispatch_error = self.dispatch_alert_event(
                    db=db,
                    bank_id=bank_id,
                    alert_id=alert_id,
                    source_event_id=source_event_id,
                    event_created_at=event_created_at,
                    actor_id=actor_id,
                )
                if not ok:
                    bank_deduped += 1
                    deduped += 1
                else:
                    bank_queued += 1
                    queued += 1
                    if dispatch_error:
                        bank_errors += 1
                        errors += 1

                if max_seen is None or event_created_at > max_seen:
                    max_seen = event_created_at

            if max_seen is not None:
                state.last_seen_created_at = max_seen
                db.add(state)
                db.commit()

            details.append(
                {
                    "bank_id": bank_id,
                    "queued": bank_queued,
                    "deduped": bank_deduped,
                    "errors": bank_errors,
                    "discovered": bank_discovered,
                    "last_seen_created_at": self._as_utc_z(max_seen) if max_seen else None,
                }
            )

        return {
            "enabled": True,
            "queued": queued,
            "deduped": deduped,
            "errors": errors,
            "discovered": discovered,
            "banks": details,
        }


def mark_ingest_event_by_workflow(
    db: Session,
    workflow_run_id: str,
    status: str,
    case_id: str | None = None,
    error_message: str | None = None,
) -> None:
    row = db.scalar(
        select(AlertIngestEvent)
        .where(AlertIngestEvent.workflow_run_id == workflow_run_id)
        .order_by(AlertIngestEvent.id.desc())
    )
    if not row:
        return

    row.status = status
    if case_id is not None:
        row.case_id = case_id
    row.error_message = error_message
    db.add(row)
    db.commit()
