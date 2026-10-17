"""Aplicação ClipDev: junta store, monitor, popup, preferências, indicador e DBus."""

from __future__ import annotations

import sys
from typing import Dict, Optional

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gio", "2.0")
from gi.repository import Gio, GLib, Gtk  # noqa: E402

from . import (  # noqa: E402
    clipboard,
    config,
    dbus_service,
    indicator,
    popup,
    prefs,
    store as st,
)


class ClipDevApp(Gtk.Application):
    def __init__(self) -> None:
        super().__init__(application_id=config.APP_ID, flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.store = st.Store()
        self.monitor: Optional[clipboard.ClipboardMonitor] = None
        self.popup: Optional[popup.Popup] = None
        self.prefs: Optional[prefs.PreferencesWindow] = None
        self.indicator: Optional[indicator.Indicator] = None
        self.dbus: Optional[dbus_service.DbusService] = None
        self._bus_id: int = 0

    # -- ciclo de vida -------------------------------------------------------
    def do_activate(self) -> None:
        if self.popup is not None:
            return

        self.popup = popup.Popup(
            self.store,
            copy_cb=self._copy_item,
            on_clear=self._clear_unpinned,
            on_prefs=self._open_prefs,
            on_font_change=self._on_font_change,
        )

        self.monitor = clipboard.ClipboardMonitor(self.store)
        self.monitor.connect("captured", self._on_captured)
        self.monitor.start()

        self.indicator = None
        try:
            self.indicator = indicator.Indicator(
                on_open=self._open_popup,
                on_clear=self._clear_unpinned,
                on_prefs=self._open_prefs,
                on_quit=self._quit,
            )
        except indicator.IndicatorUnavailable as exc:
            # Sem o typelib GIR o ícone não sobe, mas o resto do app funciona.
            print(f"[ClipDev] aviso: {exc}", file=sys.stderr)

        # DBus: assume o nome e registra o objeto
        self.dbus = dbus_service.DbusService(
            on_toggle=self._toggle_popup,
            on_open=self._open_popup,
            on_clear=self._clear_unpinned,
            on_quit=self._quit,
        )
        self._bus_id = Gio.bus_own_name(
            Gio.BusType.SESSION,
            config.DBUS_NAME,
            Gio.BusNameOwnerFlags.NONE,
            self._on_bus_acquired,
            None,
            None,
        )

        # mantém o processo vivo sem janela visível
        self.hold()

    def _on_bus_acquired(self, connection: Gio.DBusConnection, _name: str) -> None:  # noqa: ANN001
        assert self.dbus is not None
        self.dbus.register(connection)

    # -- handlers ------------------------------------------------------------
    def _on_captured(self, _monitor, _item: Dict) -> None:
        if self.popup is not None and self.popup.get_visible():
            self.popup.refresh()

    def _copy_item(self, item: Dict) -> None:
        assert self.monitor is not None
        if item["kind"] == st.IMAGE:
            self.monitor.set_image(item["content"])
        else:
            self.monitor.set_text(item["content"])
        # copiar promove o item ao topo do histórico
        self.store.add(item["kind"], item["content"], item.get("preview", ""), item["hash"])

    def _toggle_popup(self) -> None:
        if self.popup is None:
            self.activate()
            return
        self.popup.toggle()

    def _open_popup(self) -> None:
        if self.popup is None:
            self.activate()
            return
        self.popup.show_popup()

    def _clear_unpinned(self) -> None:
        self.store.clear_unpinned()
        if self.popup is not None and self.popup.get_visible():
            self.popup.refresh()

    def _open_prefs(self) -> None:
        if self.popup is None:
            return
        if self.prefs is None:
            self.prefs = prefs.PreferencesWindow(
                self.popup.get_font_size(), on_font_change=self._on_font_change
            )
        else:
            self.prefs.value.set_text(str(self.popup.get_font_size()))
        self.prefs.open()

    def _on_font_change(self, size: int) -> None:
        if self.popup is not None:
            self.popup._apply_font_size(size, save=True)
        if self.prefs is not None:
            self.prefs.value.set_text(str(config.clamp_font(size)))

    def _quit(self) -> None:
        if self._bus_id:
            Gio.bus_unown_name(self._bus_id)
        if self.monitor is not None:
            self.monitor = None
        self.store.close()
        self.quit()


def run() -> int:
    import signal

    app = ClipDevApp()
    # Encerramento gracioso em Ctrl+C / SIGTERM
    for sig in (signal.SIGINT, signal.SIGTERM):
        GLib.unix_signal_add(GLib.PRIORITY_HIGH, sig, lambda *_: (app._quit(), True)[1])
    return app.run([])