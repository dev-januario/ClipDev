"""Testes do posicionamento do popup (popup.resolve_workarea).

O bug original: no Wayland nativo, ``Gdk.Display.get_primary_monitor()``
retorna ``None`` (o conceito de "monitor primário" é do X11). O ``_position()``
chamava ``monitor.get_workarea()`` direto e quebrava com
``AttributeError: 'NoneType' object has no attribute 'get_workarea'`` antes do
``show_all()`` — o popup nunca aparecia ao apertar Super+V.

A correção: nunca confiar em ``get_primary_monitor()``; usar
``get_monitor(0)`` como fallback e retornar ``None`` se não houver monitor.

Estes testes exercitam a lógica de decisão sem precisar de um display real,
usando displays e monitores fake (duck typing).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from clipdev import popup  # noqa: E402


class FakeMonitor:
    def __init__(self, x=0, y=0, w=1920, h=1080):
        self._geo = (x, y, w, h)

    def get_workarea(self):
        x, y, w, h = self._geo
        class _Workarea:
            def __init__(self):
                self.x = x
                self.y = y
                self.width = w
                self.height = h
        return _Workarea()


class FakeDisplay:
    """Display fake que simula o comportamento do Gdk no X11 e no Wayland."""

    def __init__(self, primary=None, monitors=()):
        self._primary = primary
        self._monitors = list(monitors)

    def get_primary_monitor(self):
        return self._primary

    def get_monitor(self, index):
        try:
            return self._monitors[index]
        except IndexError:
            return None

    def get_n_monitors(self):
        return len(self._monitors)


def test_uses_primary_monitor_when_available():
    """X11: com monitor primário disponível, usa a workarea dele."""
    monitor = FakeMonitor(x=100, y=50, w=1280, h=800)
    display = FakeDisplay(primary=monitor, monitors=[monitor])

    geo = popup.resolve_workarea(display)

    assert geo is not None
    assert geo.x == 100
    assert geo.y == 50
    assert geo.width == 1280
    assert geo.height == 800


def test_falls_back_to_monitor_zero_when_no_primary():
    """Wayland: sem monitor primário, usa get_monitor(0)."""
    monitor0 = FakeMonitor(x=0, y=0, w=2560, h=1440)
    display = FakeDisplay(primary=None, monitors=[monitor0])

    geo = popup.resolve_workarea(display)

    assert geo is not None
    assert geo.width == 2560
    assert geo.height == 1440


def test_returns_none_when_no_monitor_at_all():
    """Sem nenhum monitor (ex.: display não realizado), não quebra."""
    display = FakeDisplay(primary=None, monitors=[])

    geo = popup.resolve_workarea(display)

    assert geo is None


def test_returns_none_when_display_is_none():
    """Sem display default (ex.: teste headless), não quebra."""
    geo = popup.resolve_workarea(None)

    assert geo is None