from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Engine


def ensure_bank_id_columns(engine: Engine) -> None:
    """
    Minimal, idempotent runtime migration for demos.

    We don't use Alembic yet. In Postgres, CREATE TABLE is handled by SQLAlchemy,
    but ALTER TABLE is needed when existing deployments add new columns.
    """
    if engine.dialect.name != "postgresql":
        # SQLite in tests and other dialects are handled via clean create_all.
        return

    statements = [
        "ALTER TABLE alerts ADD COLUMN IF NOT EXISTS bank_id VARCHAR NOT NULL DEFAULT 'demo'",
        "ALTER TABLE transactions ADD COLUMN IF NOT EXISTS bank_id VARCHAR NOT NULL DEFAULT 'demo'",
        "ALTER TABLE customers ADD COLUMN IF NOT EXISTS bank_id VARCHAR NOT NULL DEFAULT 'demo'",
        "ALTER TABLE aggregates ADD COLUMN IF NOT EXISTS bank_id VARCHAR NOT NULL DEFAULT 'demo'",
        "ALTER TABLE sanctions_hits ADD COLUMN IF NOT EXISTS bank_id VARCHAR NOT NULL DEFAULT 'demo'",
    ]

    with engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))

