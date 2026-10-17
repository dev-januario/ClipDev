"""Configuração central do ClipDev: caminhos, constantes e paleta de cores."""

from __future__ import annotations

import json
import os
from pathlib import Path

APP_ID = "io.github.clipdev.ClipDev"
APP_NAME = "ClipDev"
APP_VERSION = "1.1.0"

DBUS_NAME = "io.github.clipdev.ClipDev.Control"
DBUS_PATH = "/io/github/clipdev/ClipDev"

# --- Retenção ---------------------------------------------------------------
# Máximo de itens NÃO fixados mantidos. Itens fixados nunca são removidos.
MAX_UNPINNED = 50

# --- Popup ------------------------------------------------------------------
VISIBLE_ROWS = 15          # quantas linhas ficam visíveis sem rolar
ROW_HEIGHT = 40            # altura de cada linha, em pixels
ROW_BORDER = 0             # separador inferior (sem borda; espaçamento via CSS)
POPUP_WIDTH = 440
POPUP_MARGIN = 6           # margem em relação à borda superior direita
CORNER_RADIUS = 10         # border-radius do popup
SEARCH_HEIGHT = 54         # altura estimada da barra de busca + toolbar
POPUP_HEIGHT = VISIBLE_ROWS * (ROW_HEIGHT + ROW_BORDER) + SEARCH_HEIGHT

# --- Fonte ------------------------------------------------------------------
FONT_MIN = 8
FONT_MAX = 20
FONT_DEFAULT = 14          # tamanho de fonte padrão (px)

# --- Imagens ----------------------------------------------------------------
THUMB_SIZE = 128                      # thumbnail armazenada em disco (px)
ROW_ICON_SIZE = 30                    # ícone de texto na linha (px)
ROW_THUMB_SIZE = 30                   # prévia quadrada da imagem na linha (px)
MAX_IMAGE_BYTES = 10 * 1024 * 1024    # 10 MB por imagem

# --- Paleta -----------------------------------------------------------------
COLOR_BLUE = "#0086FF"
COLOR_YELLOW = "#FFC700"
COLOR_RED = "#FF3B30"
COLOR_BLACK = "#1D212A"


# --- Diretórios -------------------------------------------------------------
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


def config_path() -> Path:
    return data_dir() / "settings.json"


def style_path() -> Path:
    return Path(__file__).parent / "style.css"


def icon_path() -> Path:
    return Path(__file__).parent / "icons" / "clipdev.svg"


def autostart_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return Path(base) / "autostart" / "clipdev.desktop"


# --- Preferências -----------------------------------------------------------
def load_settings() -> dict:
    """Lê settings.json; devolve defaults se ausente/ inválido."""
    defaults = {"font_size": FONT_DEFAULT}
    path = config_path()
    if not path.exists():
        return defaults
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return defaults
    if not isinstance(data, dict):
        return defaults
    fs = data.get("font_size", FONT_DEFAULT)
    try:
        fs = int(fs)
    except (TypeError, ValueError):
        fs = FONT_DEFAULT
    defaults["font_size"] = clamp_font(fs)
    return defaults


def save_settings(settings: dict) -> None:
    path = config_path()
    try:
        path.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    except OSError:
        pass


def clamp_font(size: int) -> int:
    return max(FONT_MIN, min(FONT_MAX, int(size)))