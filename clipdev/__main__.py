"""Interface de linha de comando do ClipDev.

Uso:
    clipdev run                  # inicia o daemon (ícone na barra)
    clipdev toggle               # abre/fecha o popup (alvo do Super+V)
    clipdev open | quit
    clipdev install-shortcut     # registra Super+V
    clipdev uninstall-shortcut
    clipdev autostart-install    # inicia no login
    clipdev autostart-remove
    clipdev status
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from clipdev import config  # noqa: E402


def _proxy():
    import gi

    gi.require_version("Gio", "2.0")
    from gi.repository import Gio

    return Gio.DBusProxy.new_for_bus_sync(
        Gio.BusType.SESSION,
        Gio.DBusProxyFlags.NONE,
        None,
        config.DBUS_NAME,
        config.DBUS_PATH,
        "io.github.clipdev.ClipDev",
        None,
    )


def _call(method: str) -> bool:
    try:
        proxy = _proxy()
        proxy.call_sync(method, None, 0, -1, None)
        return True
    except Exception:
        return False


def _spawn_daemon() -> None:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(PROJECT_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    subprocess.Popen(
        [sys.executable, "-m", "clipdev", "run"],
        cwd=str(PROJECT_ROOT),
        env=env,
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _daemon_running() -> bool:
    """True se o nome DBus do daemon estiver sendo servido na sessão."""
    try:
        import gi

        gi.require_version("Gio", "2.0")
        from gi.repository import Gio, GLib

        conn = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        reply = conn.call_sync(
            "org.freedesktop.DBus",
            "/org/freedesktop/DBus",
            "org.freedesktop.DBus",
            "NameHasOwner",
            GLib.Variant("(s)", (config.DBUS_NAME,)),
            None,
            0,
            -1,
            None,
        )
        return bool(reply.unpack()[0])
    except Exception:
        return False


def cmd_run(_args) -> int:
    from clipdev.app import run

    return run()


def _call_or_spawn(method: str) -> int:
    """Chama o método no daemon; se ele não estiver rodando, sobe e tenta de novo."""
    if _call(method):
        return 0
    _spawn_daemon()
    for _ in range(25):
        time.sleep(0.15)
        if _call(method):
            return 0
    return 0


def cmd_toggle(_args) -> int:
    return _call_or_spawn("Toggle")


def cmd_open(_args) -> int:
    return _call_or_spawn("Open")


def cmd_quit(_args) -> int:
    _call("Quit")
    return 0


def cmd_install_shortcut(_args) -> int:
    from clipdev import shortcut

    shortcut.install()
    print(f"Atalho {shortcut.SHORTCUT} registrado (ClipDev: abrir histórico).")
    return 0


def cmd_uninstall_shortcut(_args) -> int:
    from clipdev import shortcut

    shortcut.uninstall()
    print("Atalho removido.")
    return 0


def cmd_autostart_install(_args) -> int:
    from clipdev import autostart

    autostart.install()
    print(f"Autostart criado em {config.autostart_path()}")
    return 0


def cmd_autostart_remove(_args) -> int:
    from clipdev import autostart

    autostart.remove()
    print("Autostart removido.")
    return 0


def cmd_status(_args) -> int:
    from clipdev import shortcut

    running = _daemon_running()
    print(f"Daemon rodando: {'sim' if running else 'não'}")
    print(f"Atalho instalado: {'sim' if shortcut.is_installed() else 'não'}")
    print(f"Autostart: {'sim' if config.autostart_path().exists() else 'não'}")

    try:
        from clipdev.indicator import _load_appindicator

        _load_appindicator()
        print("Ícone (AppIndicator): disponível")
    except Exception:
        print("Ícone (AppIndicator): INDISPONÍVEL — falta gir1.2-ayatanaappindicator3-0.1")
    return 0


def cmd_clear(_args) -> int:
    from clipdev import store as st

    s = st.Store()
    n = s.clear_unpinned()
    s.close()
    print(f"{n} itens não-fixados removidos.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="clipdev", description="Gerenciador de clipboard do ClipDev")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("run", help="inicia o daemon").set_defaults(func=cmd_run)
    sub.add_parser("toggle", help="abre/fecha o popup").set_defaults(func=cmd_toggle)
    sub.add_parser("open", help="abre o popup").set_defaults(func=cmd_open)
    sub.add_parser("quit", help="encerra o daemon").set_defaults(func=cmd_quit)
    sub.add_parser("install-shortcut", help="registra Super+V").set_defaults(func=cmd_install_shortcut)
    sub.add_parser("uninstall-shortcut", help="remove Super+V").set_defaults(func=cmd_uninstall_shortcut)
    sub.add_parser("autostart-install", help="inicia no login").set_defaults(func=cmd_autostart_install)
    sub.add_parser("autostart-remove", help="não inicia no login").set_defaults(func=cmd_autostart_remove)
    sub.add_parser("status", help="mostra o estado").set_defaults(func=cmd_status)
    sub.add_parser("clear", help="limpa itens não-fixados").set_defaults(func=cmd_clear)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help()
        return 1
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())