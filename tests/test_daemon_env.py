"""Testes do lançamento do daemon com backend X11 forçado.

No Wayland nativo o GTK3 ignora ``Gtk.Window.move()`` (o compositor decide a
posição), então o popup abria em lugar aleatório. Além disso, o monitor de
clipboard do GTK3/Wayland não recebe eventos ``owner-change`` de apps Wayland
com janela — a captura só funciona de forma confiável no backend X11
(XWayland, ponte de clipboard do GNOME).

A solução: o launcher do daemon (``clipdev run`` / ``_spawn_daemon()``) deve
sempre forçar ``GDK_BACKEND=x11``.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from clipdev import __main__ as cli  # noqa: E402


def test_force_x11_preserves_existing_gdk_backend(monkeypatch, tmp_path):
    """Se o usuário já definiu GDK_BACKEND=x11, nada muda (não sobrescreve)."""
    monkeypatch.setenv("GDK_BACKEND", "x11")
    monkeypatch.setenv("PYTHONPATH", "/existe")

    env = cli._daemon_env()

    assert env["GDK_BACKEND"] == "x11"


def test_force_x11_overrides_wayland_backend(monkeypatch):
    """Num ambiente Wayland, o daemon deve rodar como x11 (não nativo)."""
    monkeypatch.setenv("XDG_SESSION_TYPE", "wayland")
    if "GDK_BACKEND" in os.environ:
        monkeypatch.delenv("GDK_BACKEND")
    monkeypatch.setenv("PYTHONPATH", "/existe")

    env = cli._daemon_env()

    assert env["GDK_BACKEND"] == "x11"


def test_force_x11_sets_when_absent(monkeypatch):
    """Sem GDK_BACKEND definido, força x11 e mantém o PYTHONPATH do projeto."""
    if "GDK_BACKEND" in os.environ:
        monkeypatch.delenv("GDK_BACKEND")
    monkeypatch.setenv("PYTHONPATH", "/existe")
    monkeypatch.setattr(cli, "PROJECT_ROOT", "/projeto")

    env = cli._daemon_env()

    assert env["GDK_BACKEND"] == "x11"
    assert "/projeto" in env["PYTHONPATH"].split(os.pathsep)


def test_spawn_daemon_uses_daemon_env(monkeypatch):
    """_spawn_daemon() repassa o mesmo env (com GDK_BACKEND=x11) ao processo."""
    captured = {}

    class FakePopen:
        def __init__(self, args, cwd, env, start_new_session, stdout, stderr):
            captured["args"] = args
            captured["env"] = env

    monkeypatch.setattr(cli.subprocess, "Popen", FakePopen)
    monkeypatch.setenv("PYTHONPATH", "/existe")

    cli._spawn_daemon()

    assert captured["env"]["GDK_BACKEND"] == "x11"
    assert captured["args"] == [sys.executable, "-m", "clipdev", "run"]


def test_cmd_run_forces_x11(monkeypatch):
    """`clipdev run` (autostart/terminal) deve definir GDK_BACKEND=x11 antes do GTK carregar."""
    monkeypatch.delenv("GDK_BACKEND", raising=False)
    called = {"run_called": False}

    class FakeApp:
        @staticmethod
        def run():
            called["run_called"] = True
            return 0

    monkeypatch.setattr(cli, "os", __import__("os"))
    monkeypatch.setitem(cli.os.environ, "GDK_BACKEND", "x11")  # garantia pós-execução
    monkeypatch.setattr(cli, "sys", __import__("sys"))

    # importa o app de teste depois que cmd_run define o env
    import importlib

    import types

    fake_app = types.ModuleType("clipdev.app")
    fake_app.run = FakeApp.run
    monkeypatch.setitem(cli.sys.modules, "clipdev.app", fake_app)

    result = cli.cmd_run(None)

    assert result == 0
    assert cli.os.environ["GDK_BACKEND"] == "x11"
    assert called["run_called"] is True