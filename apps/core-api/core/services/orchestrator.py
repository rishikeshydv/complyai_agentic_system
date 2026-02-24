from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from difflib import unified_diff
from typing import Any

from sqlalchemy.orm import Session

from core.agents.casefile_builder import CaseFileBuilderAgent
from core.agents.rule_interpreter import RuleInterpreterAgent
from core.agents.sar_copilot import SARCopilotAgent
from core.db.models import Case, EvidenceSnapshot, WorkflowRun
from core.services.evidence_service import EvidenceService
from core.services.governance_service import append_audit_event
from core.utils.hashing import sha256_json
from core.utils.template_loader import render_markdown

WORKFLOW_STATES = [
    "RECEIVED_ALERT_EVENT",
    "FETCHING_EVIDENCE",
    "EVIDENCE_READY",
    "EXPLAINING_TRIGGER",
    "BUILDING_CASEFILE",
    "SAR_DRAFTING",
    "READY_FOR_REVIEW",
    "ERROR",
]


class OrchestratorService:
    def __init__(self) -> None:
        self.evidence_service = EvidenceService()
        self.rule_interpreter = RuleInterpreterAgent()
        self.casefile_builder = CaseFileBuilderAgent()
        self.sar_copilot = SARCopilotAgent()

    def create_workflow_run(self, db: Session, alert_id: str, bank_id: str, request_id: str | None) -> WorkflowRun:
        row = WorkflowRun(
            workflow_run_id=str(uuid.uuid4()),
            alert_id=alert_id,
            bank_id=bank_id,
            status="RECEIVED_ALERT_EVENT",
            steps=[
                {
                    "status": "RECEIVED_ALERT_EVENT",
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "note": "Workflow accepted alert event",
                }
            ],
            errors=[],
            request_id=request_id,
        )
        db.add(row)
        db.commit()
        return row

    def _set_status(self, db: Session, workflow: WorkflowRun, status: str, note: str) -> None:
        workflow.status = status
        steps = list(workflow.steps or [])
        steps.append({"status": status, "ts": datetime.now(timezone.utc).isoformat(), "note": note})
        workflow.steps = steps
        db.add(workflow)
        db.commit()

    def _mark_error(self, db: Session, workflow: WorkflowRun, message: str) -> None:
        workflow.status = "ERROR"
        errors = list(workflow.errors or [])
        errors.append({"ts": datetime.now(timezone.utc).isoformat(), "message": message})
        workflow.errors = errors
        steps = list(workflow.steps or [])
        steps.append({"status": "ERROR", "ts": datetime.now(timezone.utc).isoformat(), "note": message})
        workflow.steps = steps
        workflow.finished_at = datetime.utcnow()
        db.add(workflow)
        db.commit()

    def pull_and_generate_case(
        self,
        db: Session,
        alert_id: str,
        bank_id: str,
        workflow_run_id: str,
        actor_id: str = "system-orchestrator",
    ) -> Case:
        workflow = db.get(WorkflowRun, workflow_run_id)
        if not workflow:
            raise ValueError("Workflow run not found")

        append_audit_event(
            db,
            case_id=None,
            workflow_run_id=workflow_run_id,
            actor_type="SYSTEM",
            actor_id=actor_id,
            action="WORKFLOW_STARTED",
            notes=f"Started pull-mode orchestration for alert {alert_id}",
            metadata={"bank_id": bank_id},
        )

        try:
            self._set_status(db, workflow, "FETCHING_EVIDENCE", "Fetching evidence from connector")
            evidence_graph = self.evidence_service.build_evidence_graph(db, alert_id=alert_id, bank_id=bank_id)

            snapshot = EvidenceSnapshot(
                alert_id=alert_id,
                bank_id=bank_id,
                graph_json=evidence_graph,
                evidence_hash=evidence_graph["evidence_hash"],
            )
            db.add(snapshot)
            db.commit()
            db.refresh(snapshot)

            self._set_status(db, workflow, "EVIDENCE_READY", "Evidence graph built and validated")

            self._set_status(db, workflow, "EXPLAINING_TRIGGER", "Generating trigger explanation")
            trigger_explanation = self.rule_interpreter.run(db, evidence_graph, workflow_run_id)

            self._set_status(db, workflow, "BUILDING_CASEFILE", "Building deterministic casefile")
            casefile = self.casefile_builder.run(db, evidence_graph, trigger_explanation, workflow_run_id)

            recommendation = casefile["executive_summary"].get("recommended_disposition", "REVIEW")
            if recommendation in {"SAR_RECOMMENDED", "ESCALATE"}:
                self._set_status(db, workflow, "SAR_DRAFTING", "Generating SAR draft")
                casefile["sar_draft"] = self.sar_copilot.run(db, evidence_graph, casefile, workflow_run_id)

            workflow.finished_at = datetime.utcnow()
            self._set_status(db, workflow, "READY_FOR_REVIEW", "Case generation complete")

            timeline_events = [
                {
                    "action": step["status"],
                    "actor_type": "SYSTEM",
                    "actor_id": actor_id,
                    "timestamp": step["ts"],
                    "notes": step["note"],
                    "metadata": {"workflow_run_id": workflow_run_id},
                }
                for step in workflow.steps
            ]
            casefile["timeline_and_audit"] = {"events": timeline_events}

            case_id = str(uuid.uuid4())
            export_id = f"exp_{uuid.uuid4().hex}"
            casefile["export_bundle"]["export_id"] = export_id
            casefile["export_bundle"]["source_payload_hash"] = evidence_graph.get("source_payload_hash", "NOT PROVIDED")
            casefile["export_bundle"]["evidence_hash"] = evidence_graph["evidence_hash"]

            casefile_hash = sha256_json({**casefile, "export_bundle": {**casefile["export_bundle"], "casefile_hash": "PENDING"}})
            casefile["export_bundle"]["casefile_hash"] = casefile_hash

            markdown = render_markdown("casefile.md.j2", {"casefile": casefile})

            case_row = Case(
                case_id=case_id,
                alert_id=alert_id,
                bank_id=bank_id,
                alert_type=casefile["header"].get("alert_type", "NOT PROVIDED"),
                status="READY_FOR_REVIEW",
                casefile_json=casefile,
                casefile_markdown=markdown,
                evidence_snapshot_id=snapshot.id,
                evidence_hash=evidence_graph["evidence_hash"],
                casefile_hash=casefile_hash,
            )
            db.add(case_row)
            db.commit()

            snapshot.case_id = case_id
            db.add(snapshot)
            db.commit()

            workflow.case_id = case_id
            db.add(workflow)
            db.commit()

            append_audit_event(
                db,
                case_id=case_id,
                workflow_run_id=workflow_run_id,
                actor_type="AI",
                actor_id="casefile-builder",
                action="CASEFILE_GENERATED",
                notes="Generated evidence-first casefile",
                metadata={"casefile_hash": casefile_hash, "evidence_hash": evidence_graph["evidence_hash"]},
            )

            db.refresh(case_row)
            return case_row

        except Exception as exc:
            self._mark_error(db, workflow, str(exc))
            append_audit_event(
                db,
                case_id=None,
                workflow_run_id=workflow_run_id,
                actor_type="SYSTEM",
                actor_id=actor_id,
                action="WORKFLOW_FAILED",
                notes=str(exc),
                metadata={"alert_id": alert_id},
            )
            raise

    def replay_casefile(self, db: Session, case_row: Case, apply_changes: bool = False) -> dict[str, Any]:
        snapshot = db.get(EvidenceSnapshot, case_row.evidence_snapshot_id)
        if not snapshot:
            raise ValueError("Evidence snapshot missing")

        workflow = self.create_workflow_run(db, alert_id=case_row.alert_id, bank_id=case_row.bank_id, request_id="replay")
        trigger = self.rule_interpreter.run(db, snapshot.graph_json, workflow.workflow_run_id)
        rebuilt = self.casefile_builder.run(db, snapshot.graph_json, trigger, workflow.workflow_run_id)

        rebuilt["timeline_and_audit"] = case_row.casefile_json.get("timeline_and_audit", {"events": []})
        rebuilt["export_bundle"]["export_id"] = case_row.casefile_json.get("export_bundle", {}).get("export_id", "NOT PROVIDED")
        rebuilt["export_bundle"]["source_payload_hash"] = snapshot.graph_json.get("source_payload_hash", "NOT PROVIDED")
        rebuilt["export_bundle"]["evidence_hash"] = snapshot.evidence_hash

        new_hash = sha256_json({**rebuilt, "export_bundle": {**rebuilt["export_bundle"], "casefile_hash": "PENDING"}})
        rebuilt["export_bundle"]["casefile_hash"] = new_hash

        old_dump = json.dumps(case_row.casefile_json, indent=2, sort_keys=True).splitlines(keepends=True)
        new_dump = json.dumps(rebuilt, indent=2, sort_keys=True).splitlines(keepends=True)
        diff = "".join(unified_diff(old_dump, new_dump, fromfile="old", tofile="new"))

        if apply_changes:
            case_row.casefile_json = rebuilt
            case_row.casefile_hash = new_hash
            case_row.casefile_markdown = render_markdown("casefile.md.j2", {"casefile": rebuilt})
            db.add(case_row)
            db.commit()

        append_audit_event(
            db=db,
            case_id=case_row.case_id,
            workflow_run_id=workflow.workflow_run_id,
            actor_type="SYSTEM",
            actor_id="replay-engine",
            action="CASEFILE_REPLAYED",
            notes="Replayed casefile from immutable evidence snapshot",
            metadata={"applied": apply_changes, "new_casefile_hash": new_hash},
        )

        return {
            "case_id": case_row.case_id,
            "old_casefile_hash": case_row.casefile_hash,
            "new_casefile_hash": new_hash,
            "diff": diff,
            "applied": apply_changes,
        }
