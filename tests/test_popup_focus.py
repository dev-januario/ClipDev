"""Testes do pedido de foco do popup (popup.present_focused).

O bug original: com type hint POPUP_MENU, o Mutter nunca dá foco de teclado, e
o present() do GTK usava um timestamp antigo -> o popup era marcado com
DEMANDS_ATTENTION e as setas/Enter iam para outra janela. A correção pede a
ativação com um timestamp fresco do servidor X.

Estes testes exercitam a lógica de decisão sem precisar de um display real,
usando janelas fake (duck typing).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from clipdev import popup  # noqa: E402


class FakeWindow:
    """Janela fake que registra qual caminho de apresentação foi usado."""

    def __init__(self, gdk_window=object()):
        self._gdk_window = gdk_window
        self.present_called = False
        self.present_with_time_called = None

    def get_window(self):
        return self._gdk_window

    def present(self):
        self.present_called = True

    def present_with_time(self, timestamp):
        self.present_with_time_called = timestamp


class FakeGdkX11:
    def __init__(self, value=1234, raise_exc=False):
        self._value = value
        self._raise = raise_exc
        self.calls = 0

    def x11_get_server_time(self, _gdk_window):
        self.calls += 1
        if self._raise:
            raise RuntimeError("sem X11")
        return self._value


def test_uses_fresh_server_time(monkeypatch):
    """Caminho normal: usa present_with_time com o timestamp do servidor."""
    fake = FakeGdkX11(value=999)
    monkeypatch.setattr(popup, "GdkX11", fake)
    win = FakeWindow()

    used = popup.present_focused(win)

    assert used is True
    assert win.present_with_time_called == 999
    assert win.present_called is False
    assert fake.calls == 1


def test_falls_back_when_no_gdkx11(monkeypatch):
    """Sem GdkX11 (ex.: Wayland), cai no present() normal."""
    monkeypatch.setattr(popup, "GdkX11", None)
    win = FakeWindow()

    used = popup.present_focused(win)

    assert used is False
    assert win.present_called is True
    assert win.present_with_time_called is None


def test_falls_back_when_no_gdk_window(monkeypatch):
    """Janela ainda não realizada (get_window() -> None): present() normal."""
    monkeypatch.setattr(popup, "GdkX11", FakeGdkX11())
    win = FakeWindow(gdk_window=None)

    used = popup.present_focused(win)

    assert used is False
    assert win.present_called is True
    assert win.present_with_time_called is None


def test_falls_back_on_exception(monkeypatch):
    """Erro ao consultar o servidor X não deve quebrar: present() normal."""
    monkeypatch.setattr(popup, "GdkX11", FakeGdkX11(raise_exc=True))
    win = FakeWindow()

    used = popup.present_focused(win)

    assert used is False
    assert win.present_called is True
    assert win.present_with_time_called is None


def test_falls_back_on_zero_timestamp(monkeypatch):
    """Timestamp 0 não é útil; usa present() normal."""
    monkeypatch.setattr(popup, "GdkX11", FakeGdkX11(value=0))
    win = FakeWindow()

    used = popup.present_focused(win)

    assert used is False
    assert win.present_called is True
    assert win.present_with_time_called is None