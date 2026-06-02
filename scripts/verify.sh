#!/usr/bin/env bash
# Run all local checks (compile, imports, optional route smoke test).
set -euo pipefail
cd "$(dirname "$0")/.."

PYTHON="${PYTHON:-python3}"
if [[ -x .venv/bin/python ]]; then
  PYTHON=".venv/bin/python"
fi

echo "==> Python compile"
$PYTHON -m compileall -q src scripts streamlit_app.py

echo "==> Import check"
$PYTHON -c "
from src.api.main import app
from src.app import main
from src.services.route_service import compare_routes_for_trip
print('imports OK')
"

if [[ "${RUN_ROUTE_SMOKE:-0}" == "1" ]]; then
  echo "==> Route smoke (needs network)"
  $PYTHON scripts/compare_routes.py \
    --origin-lat 41.8781 --origin-lon -87.6298 \
    --dest-lat 41.9484 --dest-lon -87.6553
fi

echo "All checks passed."
