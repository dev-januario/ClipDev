"""Atalho global Super+V via GSettings (GNOME media-keys custom keybindings).

Registra um keybinding custom apontando para ``<clipdev> toggle``. O GNOME
executa o comando quando o atalho é pressionado, e o comando fala com o daemon
via DBus.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import List

SCHEMA = "org.gnome.settings-daemon.plugins.media-keys"
KEY = "custom-keybindings"
BINDING_PATH = "/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/clipdev/"
BINDING_SCHEMA = "org.gnome.settings-daemon.plugins.media-keys.custom-keybinding"
SHORTCUT = "<Super>v"


def _gsettings(*args: str) -> str:
    return subprocess.run(
        ["gsettings", *args], capture_output=True, text=True, check=False
    ).stdout.strip()


def _gsettings_set(schema: str, key: str, value: str, path: str | None = None) -> None:
    # sintaxe correta: gsettings set SCHEMA[:PATH] KEY VALUE
    target = f"{schema}:{path}" if path else schema
    cmd = ["gsettings", "set", target, key, value]
    subprocess.run(cmd, check=False, capture_output=True, text=True)


def _read_custom_list() -> List[str]:
    out = _gsettings("get", SCHEMA, KEY)
    # formato: ['/path/1/', '/path/2/']
    out = out.strip().strip("[]")
    if not out:
        return []
    return [p.strip().strip("'\"") for p in out.split(",") if p.strip()]


def _clipdev_command() -> str:
    exe = shutil.which("clipdev")
    if exe:
        return f"{exe} toggle"
    # fallback: usa o launcher do próprio projeto (não depende do PATH)
    launcher = Path(__file__).resolve().parent.parent / "scripts" / "clipdev"
    if launcher.exists():
        return f"{launcher} toggle"
    return "/usr/bin/python3.10 -m clipdev toggle"


def install() -> bool:
    paths = _read_custom_list()
    if BINDING_PATH not in paths:
        paths.append(BINDING_PATH)
        _gsettings_set(SCHEMA, KEY, "[" + ", ".join(f"'{p}'" for p in paths) + "]")

    _gsettings_set(BINDING_SCHEMA, "name", "'ClipDev: abrir histórico'", path=BINDING_PATH)
    _gsettings_set(BINDING_SCHEMA, "command", f"'{_clipdev_command()}'", path=BINDING_PATH)
    _gsettings_set(BINDING_SCHEMA, "binding", f"'{SHORTCUT}'", path=BINDING_PATH)
    return True


def uninstall() -> bool:
    paths = _read_custom_list()
    if BINDING_PATH in paths:
        paths.remove(BINDING_PATH)
        if paths:
            value = "[" + ", ".join(f"'{p}'" for p in paths) + "]"
        else:
            value = "@as []"
        _gsettings_set(SCHEMA, KEY, value)
    return True


def is_installed() -> bool:
    return BINDING_PATH in _read_custom_list()