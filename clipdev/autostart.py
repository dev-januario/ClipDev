"""Autostart do ClipDev via arquivo .desktop em ~/.config/autostart."""

from __future__ import annotations

import shutil
from pathlib import Path

from . import config

_DESKTOP = """[Desktop Entry]
Type=Application
Name=ClipDev
Comment=Gerenciador de clipboard
Exec={exec_cmd}
Icon={icon}
Terminal=false
X-GNOME-Autostart-enabled=true
StartupNotify=false
"""


def _exec_command() -> str:
    """Comando do Exec=. Caminhos com espaços precisam de aspas; nada de `#`."""
    exe = shutil.which("clipdev")
    if exe:
        return f'"{exe}" run'
    # usa o launcher do próprio projeto (funciona de qualquer cwd)
    launcher = Path(__file__).resolve().parent.parent / "scripts" / "clipdev"
    if launcher.exists():
        return f'"{launcher}" run'
    return "/usr/bin/python3.10 -m clipdev run"


def install() -> Path:
    path = config.autostart_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    icon = str(config.icon_path()) if config.icon_path().exists() else "edit-copy"
    path.write_text(_DESKTOP.format(exec_cmd=_exec_command(), icon=icon), encoding="utf-8")
    return path


def remove() -> None:
    path = config.autostart_path()
    try:
        if path.exists():
            path.unlink()
    except OSError:
        pass


def is_installed() -> bool:
    return config.autostart_path().exists()