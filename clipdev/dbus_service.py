"""Serviço DBus do ClipDev.

Expõe ``io.github.clipdev.ClipDev`` em ``/io/github/clipdev/ClipDev`` com o
método ``Toggle()``. É o alvo do atalho global Super+V (o atalho roda
``clipdev toggle``, que chama este método).
"""

from __future__ import annotations

from typing import Callable

import gi

gi.require_version("Gio", "2.0")
from gi.repository import Gio, GLib  # noqa: E402

from . import config  # noqa: E402

_INTROSPECTION = """
<node>
  <interface name='io.github.clipdev.ClipDev'>
    <method name='Toggle'/>
    <method name='Open'/>
    <method name='Clear'/>
    <method name='Quit'/>
  </interface>
</node>
"""


class DbusService:
    def __init__(
        self,
        on_toggle: Callable[[], None],
        on_open: Callable[[], None],
        on_clear: Callable[[], None],
        on_quit: Callable[[], None],
    ):
        self.on_toggle = on_toggle
        self.on_open = on_open
        self.on_clear = on_clear
        self.on_quit = on_quit
        self._reg_id: int = 0
        self._node_info = Gio.DBusNodeInfo.new_for_xml(_INTROSPECTION)

    def register(self, connection: Gio.DBusConnection) -> None:
        interface = self._node_info.interfaces[0]
        self._reg_id = connection.register_object(
            config.DBUS_PATH,
            interface,
            self._on_method_call,
            None,
            None,
        )

    def _on_method_call(self, _conn, _sender, _path, _iface, method, _params, invocation):  # noqa: ANN001
        if method == "Toggle":
            GLib.idle_add(lambda: self.on_toggle() or False)
            invocation.return_value(None)
        elif method == "Open":
            GLib.idle_add(lambda: self.on_open() or False)
            invocation.return_value(None)
        elif method == "Clear":
            GLib.idle_add(lambda: self.on_clear() or False)
            invocation.return_value(None)
        elif method == "Quit":
            GLib.idle_add(lambda: self.on_quit() or False)
            invocation.return_value(None)
        else:
            invocation.return_error_literal(
                Gio.dbus_error_quark(), Gio.DBusError.UNKNOWN_METHOD, "método desconhecido"
            )