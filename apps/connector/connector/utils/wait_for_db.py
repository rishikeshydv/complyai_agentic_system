from __future__ import annotations

import os
import time

from sqlalchemy import create_engine, text

from connector.config import settings


def wait_for_db(timeout_seconds: int = 90, interval_seconds: float = 1.0) -> None:
    timeout = int(os.getenv("DB_WAIT_TIMEOUT_SECONDS", str(timeout_seconds)))
    interval = float(os.getenv("DB_WAIT_INTERVAL_SECONDS", str(interval_seconds)))
    deadline = time.monotonic() + timeout
    engine = create_engine(settings.connector_db_url, future=True, pool_pre_ping=True)

    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            engine.dispose()
            return
        except Exception as exc:  # pragma: no cover - startup guard
            last_error = exc
            time.sleep(interval)

    engine.dispose()
    raise RuntimeError(f"Timed out waiting for connector DB after {timeout}s: {last_error}")


def main() -> None:
    wait_for_db()


if __name__ == "__main__":
    main()
