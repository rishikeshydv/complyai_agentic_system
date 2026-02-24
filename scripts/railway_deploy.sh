#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if ! command -v railway >/dev/null 2>&1; then
  echo "railway CLI not found in PATH"
  exit 1
fi

if [[ -z "${RAILWAY_API_TOKEN:-}" ]]; then
  echo "RAILWAY_API_TOKEN is not set in this shell."
  echo "Export it first, or run from a shell where you are logged in."
  exit 2
fi

services=("$@")
if [[ "${#services[@]}" -eq 0 ]]; then
  services=(core-api connector web core-worker core-beat)
fi

echo "Deploying to Railway (services: ${services[*]})"

for s in "${services[@]}"; do
  echo
  echo "==> railway up --service ${s} --detach"
  railway up --service "${s}" --detach
done

echo
echo "Done."

