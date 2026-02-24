#!/usr/bin/env sh
set -eu

# Production entrypoint:
# - Wait for DB (only needed if connector uses a DB; fine to keep enabled)
# - Ensure schema exists
# - Optionally seed demo mock bank data (disabled by default)

python -m connector.utils.wait_for_db

# Connector has no separate "bootstrap" module; seed() already create_all and is idempotent.
# For production demo deployments, allow controlled seeding via CONNECTOR_RUN_SEED=true.
if [ "${CONNECTOR_RUN_SEED:-false}" = "true" ]; then
  python -m connector.db.seed
else
  python -c "from connector.db.models import Base; from connector.db.session import engine; Base.metadata.create_all(bind=engine)"
fi

exec uvicorn connector.main:app --host 0.0.0.0 --port "${PORT:-8100}" --workers "${UVICORN_WORKERS:-2}"

