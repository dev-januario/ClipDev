#!/usr/bin/env bash
# Instala o ClipDev: verifica dependências, cria o comando ~/.local/bin/clipdev,
# registra o atalho Super+V e habilita o autostart.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY=/usr/bin/python3.10
BIN_DIR="$HOME/.local/bin"

echo "== ClipDev :: install =="

# 1) Dependência de sistema (typelib do AppIndicator)
if ! "$PY" -c "import gi; gi.require_version('AyatanaAppIndicator3','0.1')" 2>/dev/null; then
  echo "!! Falta o pacote: gir1.2-ayatanaappindicator3-0.1"
  echo "   Rode:  sudo apt install gir1.2-ayatanaappindicator3-0.1"
  echo "   (o ícone na barra não sobe sem ele)"
fi

# 2) Sanidade do GTK/PyGObject
if ! "$PY" -c "import gi; gi.require_version('Gtk','3.0')" 2>/dev/null; then
  echo "!! PyGObject/GTK3 não encontrado em $PY. Instale python3-gi gir1.2-gtk-3.0."
  exit 1
fi

# 3) Comando no PATH
mkdir -p "$BIN_DIR"
ln -sf "$ROOT/scripts/clipdev" "$BIN_DIR/clipdev"
chmod +x "$ROOT/scripts/clipdev"
echo "comando criado: $BIN_DIR/clipdev"

# 4) Atalho Super+V e autostart
"$PY" -m clipdev install-shortcut || true
"$PY" -m clipdev autostart-install || true

# 5) Recarrega o serviço de atalhos do GNOME para o Super+V valer já
#    (o gsd-media-keys volta sozinho; sem isso o atalho só pega no próximo login)
if pgrep -x gsd-media-keys >/dev/null 2>&1; then
  killall gsd-media-keys 2>/dev/null || true
  echo "serviço de atalhos recarregado (gsd-media-keys)"
fi

echo
echo "Pronto. Para iniciar agora:"
echo "  clipdev run &        (ou apenas aperte Super+V)"
echo
echo "Se $BIN_DIR não estiver no PATH, adicione ao ~/.bashrc:"
echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""