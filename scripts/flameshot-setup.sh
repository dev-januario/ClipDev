#!/usr/bin/env bash
# =============================================================================
# flameshot-setup.sh — instala o Flameshot nativo (v11) em ~/.local (sem sudo)
# e aponta o atalho Print para ele.
#
# Por quê: na sessão X11, o Flameshot v11 nativo abre a PRÓPRIA interface de
# captura (janela fullscreen "flameshot"). A versão flatpak (v14) delega a
# captura ao portal do GNOME e abre a UI nativa "Captura de tela" (o "normal
# do gnome"), mesmo no X11 — por isso este script NÃO usa o flatpak.
#
# O que ele faz:
#   1) Baixa o pacote "flameshot" do apt (sem instalar no sistema).
#   2) Extrai o binário para ~/.local/opt/flameshot/.
#   3) Cria o launcher ~/.local/bin/flameshot (PATH do usuário).
#   4) Aponta o keybinding do Print para "flameshot gui".
#   5) Cria desktop file + serviço D-Bus do usuário para o flameshot nativo
#      ter precedência sobre qualquer outra instalação (ex.: flatpak).
#   6) Recarrega o serviço de atalhos do GNOME (gsd-media-keys).
#
# USO (não precisa de sudo):
#   ./scripts/flameshot-setup.sh
#
# Para desfazer:
#   rm -f ~/.local/bin/flameshot ~/.local/opt/flameshot/flameshot
#   rm -f ~/.local/share/applications/org.flameshot.Flameshot.desktop
#   rm -f ~/.local/share/dbus-1/services/org.flameshot.Flameshot.service
#   gsettings reset org.gnome.settings-daemon.plugins.media-keys custom-keybindings
# =============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BIN_DIR="$HOME/.local/bin"
OPT_DIR="$HOME/.local/opt/flameshot"
TMP_DIR="$(mktemp -d)"
BINDING_PATH="/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/flameshot/"
BINDING_SCHEMA="org.gnome.settings-daemon.plugins.media-keys.custom-keybinding"

echo "== Flameshot :: setup (X11) =="

# Garante que estamos em X11 (o flameshot v11 depende da captura X11)
if [ "${XDG_SESSION_TYPE:-}" = "wayland" ]; then
  echo "!! Você está em uma sessão Wayland. O Flameshot nativo v11 NÃO"
  echo "   captura em Wayland (abre o portal do GNOME)."
  echo "   Saia e entre em 'Ubuntu on Xorg' na tela de login e rode de novo."
  exit 1
fi

# 1) Baixa e extrai o pacote (sem instalar no sistema)
echo
echo "[1/6] Baixando o pacote flameshot (apt download)..."
(cd "$TMP_DIR" && apt download flameshot >/dev/null 2>&1)
DEB=$(ls "$TMP_DIR"/flameshot_*.deb 2>/dev/null | head -1)
if [ -z "$DEB" ]; then
  echo "!! Não consegui baixar o pacote flameshot. Verifique sua rede/apt."
  exit 1
fi
echo "      pacote: $(basename "$DEB")"

echo "[2/6] Extraindo para $OPT_DIR ..."
mkdir -p "$OPT_DIR"
dpkg-deb -x "$DEB" "$TMP_DIR/extracted"
cp -f "$TMP_DIR/extracted/usr/bin/flameshot" "$OPT_DIR/flameshot"
chmod +x "$OPT_DIR/flameshot"
mkdir -p "$OPT_DIR/share"
if [ -d "$TMP_DIR/extracted/usr/share/flameshot/translations" ]; then
  cp -rf "$TMP_DIR/extracted/usr/share/flameshot/translations" "$OPT_DIR/share/"
fi

# 2) Launcher no PATH do usuário
echo "[3/6] Criando launcher $BIN_DIR/flameshot ..."
mkdir -p "$BIN_DIR"
cat > "$BIN_DIR/flameshot" << EOS
#!/usr/bin/env bash
# Launcher do Flameshot (extraído em ~/.local/opt/flameshot).
exec "$OPT_DIR/flameshot" "\$@"
EOS
chmod +x "$BIN_DIR/flameshot"

# 3) Keybinding do Print
# Reaproveita um binding que já exista com a tecla Print (ex.: custom0);
# só cria o caminho novo se não houver nenhum. Evita dois bindings no Print.
echo "[4/6] Apontando a tecla Print para 'flameshot gui' ..."
MEDIA_SCHEMA="org.gnome.settings-daemon.plugins.media-keys"
EXISTING_PATH=""
RAW=$(gsettings get "$MEDIA_SCHEMA" custom-keybindings 2>/dev/null)
RAW=${RAW//[\[\]]/}
IFS=',' read -r -a PATHS <<< "$RAW"
for entry in "${PATHS[@]}"; do
  p=$(echo "$entry" | xargs | tr -d "'")
  [ -z "$p" ] && continue
  b=$(gsettings get "$BINDING_SCHEMA:$p" binding 2>/dev/null | tr -d "'")
  if [ "$b" = "Print" ]; then
    EXISTING_PATH="$p"
    break
  fi
done

if [ -n "$EXISTING_PATH" ]; then
  echo "      usando binding existente: $EXISTING_PATH"
  gsettings set "$BINDING_SCHEMA:$EXISTING_PATH" name "'Print Flameshot nativo'" 2>/dev/null || true
  gsettings set "$BINDING_SCHEMA:$EXISTING_PATH" command "'flameshot gui'"
else
  echo "      criando binding novo: $BINDING_PATH"
  paths=$(gsettings get "$MEDIA_SCHEMA" custom-keybindings 2>/dev/null)
  paths=$(echo "$paths" | tr -d "[]")
  if [ -z "$paths" ] || [ "$paths" = "" ]; then
    gsettings set "$MEDIA_SCHEMA" custom-keybindings "['$BINDING_PATH']"
  else
    gsettings set "$MEDIA_SCHEMA" custom-keybindings "[$paths, '$BINDING_PATH']"
  fi
  gsettings set "$BINDING_SCHEMA:$BINDING_PATH" name "'Print Flameshot nativo'"
  gsettings set "$BINDING_SCHEMA:$BINDING_PATH" command "'flameshot gui'"
  gsettings set "$BINDING_SCHEMA:$BINDING_PATH" binding "'Print'"
fi

# 4) Precedência do nativo sobre outras instalações (desktop + D-Bus)
echo "[5/6] Garantindo precedência do flameshot nativo ..."
mkdir -p "$HOME/.local/share/applications" "$HOME/.local/share/dbus-1/services"
cat > "$HOME/.local/share/applications/org.flameshot.Flameshot.desktop" << 'EOD'
[Desktop Entry]
Name=Flameshot
GenericName=Screenshot tool
Comment=Powerful yet simple to use screenshot software.
Exec=flameshot
Icon=org.flameshot.Flameshot
Terminal=false
Type=Application
Categories=Graphics;
StartupNotify=false
StartupWMClass=flameshot
X-DBUS-StartupType=Unique
X-DBUS-ServiceName=org.flameshot.Flameshot

[Desktop Action Capture]
Name=Capturar tela
Exec=flameshot gui --delay 500

[Desktop Action Launcher]
Name=Abrir launcher
Exec=flameshot launcher
EOD
printf '[D-BUS Service]\nName=org.flameshot.Flameshot\nExec=%s\n' "$BIN_DIR/flameshot" > "$HOME/.local/share/dbus-1/services/org.flameshot.Flameshot.service"

# 5) Recarrega o serviço de atalhos
echo "[6/6] Recarregando serviço de atalhos (gsd-media-keys) ..."
if pgrep -x gsd-media-keys >/dev/null 2>&1; then
  killall gsd-media-keys 2>/dev/null || true
  sleep 1
fi

rm -rf "$TMP_DIR"

echo
echo "Pronto!"
echo "  flameshot  -> $(command -v flameshot 2>/dev/null || echo "$BIN_DIR/flameshot")"
FINAL_PATH="${EXISTING_PATH:-$BINDING_PATH}"
echo "  Print      -> $(gsettings get "$BINDING_SCHEMA:$FINAL_PATH" command 2>/dev/null)"
echo
echo "Aperte Print para testar — deve abrir a UI própria do Flameshot."