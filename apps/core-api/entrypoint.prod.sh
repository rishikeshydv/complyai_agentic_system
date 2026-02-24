#!/usr/bin/env sh
set -eu

# Production entrypoint:
# - Wait for DB
# - Ensure schema exists (create_all)
# - Optionally seed demo data (disabled by default)

python -m core.utils.wait_for_db
python -m core.db.bootstrap

if [ "${CORE_RUN_SEED:-false}" = "true" ]; then
  python -m core.db.seed
fi

exec uvicorn core.main:app --host 0.0.0.0 --port "${PORT:-8000}" --workers "${UVICORN_WORKERS:-2}"

