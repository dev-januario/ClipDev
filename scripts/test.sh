#!/usr/bin/env bash
# Roda a suíte de testes do ClipDev.
# Usa o python3.10 do sistema (onde o PyGObject/GTK3 vive).
set -euo pipefail
cd "$(dirname "$0")/.."
exec /usr/bin/python3.10 -m pytest tests/ -v "$@"