#!/usr/bin/env bash
# Desinstala o ClipDev: remove atalho, autostart e o comando do PATH.
# (Não apaga seus dados; para isso remova ~/.local/share/clipdev manualmente.)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY=/usr/bin/python3.10
BIN_DIR="$HOME/.local/bin"

echo "== ClipDev :: uninstall =="

"$PY" -m clipdev quit 2>/dev/null || true
"$PY" -m clipdev uninstall-shortcut || true
"$PY" -m clipdev autostart-remove || true

if [ -L "$BIN_DIR/clipdev" ]; then
  rm -f "$BIN_DIR/clipdev"
  echo "comando removido: $BIN_DIR/clipdev"
fi

echo "Pronto. Dados em ~/.local/share/clipdev foram mantidos."