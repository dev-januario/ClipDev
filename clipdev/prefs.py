"""Janela de preferências do ClipDev (por enquanto: tamanho da fonte)."""

from __future__ import annotations

from typing import Callable, Optional

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, Gtk  # noqa: E402

from . import config  # noqa: E402


class PreferencesWindow(Gtk.Window):
    def __init__(self, font_size: int, on_font_change: Callable[[int], None]):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.on_font_change = on_font_change
        self._font_size = config.clamp_font(font_size)

        self.set_title(f"{config.APP_NAME} — Preferências")
        self.set_resizable(False)
        self.set_skip_taskbar_hint(True)
        self.set_keep_above(True)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_default_size(340, 140)
        self.get_style_context().add_class("prefs-window")
        self._load_css()

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_margin_top(14)
        box.set_margin_bottom(14)
        box.set_margin_start(16)
        box.set_margin_end(16)
        self.add(box)

        title = Gtk.Label(label="Preferências", xalign=0.0)
        title.get_style_context().add_class("prefs-title")
        box.pack_start(title, False, False, 0)

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        label = Gtk.Label(label="Tamanho da fonte", xalign=0.0)
        label.get_style_context().add_class("prefs-label")
        label.set_hexpand(True)
        row.pack_start(label, True, True, 0)

        minus = Gtk.Button(label="−")
        minus.get_style_context().add_class("footer-button")
        minus.connect("clicked", lambda *_: self._change(-1))
        row.pack_start(minus, False, False, 0)

        self.value = Gtk.Label(label=str(self._font_size))
        self.value.get_style_context().add_class("prefs-value")
        row.pack_start(self.value, False, False, 0)

        plus = Gtk.Button(label="+")
        plus.get_style_context().add_class("footer-button")
        plus.connect("clicked", lambda *_: self._change(+1))
        row.pack_start(plus, False, False, 0)
        box.pack_start(row, False, False, 0)

        hint = Gtk.Label(
            label=f"Ajuste de {config.FONT_MIN} a {config.FONT_MAX}px. "
            "A lista do histórico se ajusta automaticamente.",
            xalign=0.0,
        )
        hint.get_style_context().add_class("prefs-label")
        hint.set_line_wrap(True)
        box.pack_start(hint, False, False, 0)

        close = Gtk.Button(label="Fechar")
        close.get_style_context().add_class("footer-button")
        close.connect("clicked", lambda *_: self.hide())
        box.pack_end(close, False, False, 0)

        self.connect("delete-event", self._on_delete_event)

    def _load_css(self) -> None:
        try:
            provider = Gtk.CssProvider()
            provider.load_from_path(str(config.style_path()))
            Gtk.StyleContext.add_provider_for_screen(
                Gdk.Screen.get_default(),
                provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
            )
        except Exception:
            pass

    def _change(self, delta: int) -> None:
        self._font_size = config.clamp_font(self._font_size + delta)
        self.value.set_text(str(self._font_size))
        self.on_font_change(self._font_size)

    def open(self) -> None:
        self.show_all()
        self.present()

    def _on_delete_event(self, *_args) -> bool:
        self.hide()
        return True