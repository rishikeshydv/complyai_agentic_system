from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from core.db.models import AuditEvent, LLMInvocation
from core.utils.hashing import sha256_json, sha256_text


def append_audit_event(
    db: Session,
    case_id: str | None,
    workflow_run_id: str | None,
    actor_type: str,
    actor_id: str,
    action: str,
    notes: str,
    metadata: dict[str, Any] | None = None,
) -> AuditEvent:
    event = AuditEvent(
        event_id=str(uuid.uuid4()),
        case_id=case_id,
        workflow_run_id=workflow_run_id,
        actor_type=actor_type,
        actor_id=actor_id,
        action=action,
        notes=notes,
        metadata_jsonb=metadata or {},
        created_at=datetime.utcnow(),
    )
    db.add(event)
    db.commit()
    return event


def record_llm_invocation(
    db: Session,
    workflow_run_id: str | None,
    case_id: str | None,
    prompt_id: str,
    version: str,
    rendered_prompt: str,
    model_provider: str,
    model_name: str,
    request_payload: dict[str, Any],
    response_payload: dict[str, Any],
) -> LLMInvocation:
    invocation = LLMInvocation(
        workflow_run_id=workflow_run_id,
        case_id=case_id,
        prompt_id=prompt_id,
        version=version,
        rendered_prompt_hash=sha256_text(rendered_prompt),
        model_provider=model_provider,
        model_name=model_name,
        response_hash=sha256_json(response_payload),
        request_payload=request_payload,
        response_payload=response_payload,
    )
    db.add(invocation)
    db.commit()
    return invocation
