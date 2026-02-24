from __future__ import annotations

from sqlalchemy.orm import Session

from connector.db.models import ConnectorFetchAudit


def log_fetch(db: Session, request_id: str, endpoint: str, parameters: dict) -> None:
    row = ConnectorFetchAudit(request_id=request_id, endpoint=endpoint, parameters=parameters)
    db.add(row)
    db.commit()
