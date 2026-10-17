"""Configuração central do ClipDev: caminhos, constantes e paleta de cores."""

from __future__ import annotations

import os
from pathlib import Path

APP_ID = "io.github.clipdev.ClipDev"
APP_NAME = "ClipDev"
APP_VERSION = "1.0.0"

DBUS_NAME = "io.github.clipdev.ClipDev"
DBUS_PATH = "/io/github/clipdev/ClipDev"

# --- Retenção ---------------------------------------------------------------
# Máximo de itens NÃO fixados mantidos. Itens fixados nunca são removidos.
MAX_UNPINNED = 50

# --- Popup ------------------------------------------------------------------
VISIBLE_ROWS = 15      # quantas linhas ficam visíveis sem rolar
ROW_HEIGHT = 15        # altura de cada linha, em pixels (compacto)
POPUP_WIDTH = 380
POPUP_MARGIN = 6       # margem em relação à borda superior direita

# --- Imagens ----------------------------------------------------------------
THUMB_SIZE = 64                       # thumbnail armazenada em disco (px)
ROW_THUMB_SIZE = 12                   # thumbnail desenhada na linha (px)
MAX_IMAGE_BYTES = 10 * 1024 * 1024    # 10 MB por imagem

# --- Paleta -----------------------------------------------------------------
COLOR_BLUE = "#0086FF"
COLOR_YELLOW = "#FFC700"
COLOR_BLACK = "#1D212A"


def data_dir() -> Path:
    """Diretório de dados. Sobrescrevível por CLIPDEV_DATA_DIR (usado em testes)."""
    override = os.environ.get("CLIPDEV_DATA_DIR")
    if override:
        d = Path(override)
    else:
        base = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
        d = Path(base) / "clipdev"
    d.mkdir(parents=True, exist_ok=True)
    return d


def db_path() -> Path:
    return data_dir() / "clipdev.db"


def images_dir() -> Path:
    d = data_dir() / "images"
    d.mkdir(parents=True, exist_ok=True)
    return d


def style_path() -> Path:
    return Path(__file__).parent / "style.css"


def icon_path() -> Path:
    return Path(__file__).parent / "icons" / "clipdev.svg"


def autostart_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return Path(base) / "autostart" / "clipdev.desktop"