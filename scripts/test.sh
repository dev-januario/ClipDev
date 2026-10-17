#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
PY="${VENV:-.venv}/bin/python"
if [ ! -x "$PY" ]; then
  PY=/usr/bin/python3.10
fi
exec "$PY" -m pytest -q "$@"