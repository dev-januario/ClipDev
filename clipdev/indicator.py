"""Indicador na barra superior (AyatanaAppIndicator3).

Fornece o ícone perto do Wi-Fi, com menu (Abrir histórico, Limpar não-fixados,
Sair). Requer o typelib GIR ``gir1.2-ayatanaappindicator3-0.1``.
"""

from __future__ import annotations

from typing import Callable, Optional

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa: E402

from . import config  # noqa: E402

MISSING_DEP_HINT = (
    "O ícone da barra requer o pacote gir1.2-ayatanaappindicator3-0.1.\n"
    "Instale com:  sudo apt install gir1.2-ayatanaappindicator3-0.1"
)


class IndicatorUnavailable(RuntimeError):
    """O binding do AppIndicator não está disponível no sistema."""


def _load_appindicator():
    """Importa o namespace do AppIndicator sob demanda (lazy).

    Assim, o restante do app (clipboard, popup, DBus/atalho) funciona mesmo
    sem o typelib GIR instalado.
    """
    try:
        gi.require_version("AyatanaAppIndicator3", "0.1")
        from gi.repository import AyatanaAppIndicator3 as AppIndicator

        return AppIndicator
    except (ValueError, ImportError):
        pass
    try:
        gi.require_version("AppIndicator3", "0.1")
        from gi.repository import AppIndicator3 as AppIndicator

        return AppIndicator
    except (ValueError, ImportError) as exc:
        raise IndicatorUnavailable(MISSING_DEP_HINT) from exc


class Indicator:
    def __init__(
        self,
        on_open: Callable[[], None],
        on_clear: Callable[[], None],
        on_quit: Callable[[], None],
    ) -> None:
        AppIndicator = _load_appindicator()
        self.on_open = on_open
        self.on_clear = on_clear
        self.on_quit = on_quit

        icon = str(config.icon_path()) if config.icon_path().exists() else "edit-copy"
        self.indicator = AppIndicator.Indicator.new(
            config.APP_ID,
            icon,
            AppIndicator.IndicatorCategory.APPLICATION_STATUS,
        )
        self.indicator.set_title(config.APP_NAME)
        if config.icon_path().exists():
            self.indicator.set_icon_full(icon, config.APP_NAME)
        self.indicator.set_status(AppIndicator.IndicatorStatus.ACTIVE)

        self.menu = self._build_menu()
        self.indicator.set_menu(self.menu)
        # clique do meio abre o popup (quando suportado)
        try:
            self.indicator.set_secondary_activate_target(self._open_item)
        except Exception:
            pass

    def _build_menu(self) -> Gtk.Menu:
        menu = Gtk.Menu()

        self._open_item = Gtk.MenuItem(label="Abrir histórico")
        self._open_item.connect("activate", lambda *_: self.on_open())
        menu.append(self._open_item)

        clear_item = Gtk.MenuItem(label="Limpar não-fixados")
        clear_item.connect("activate", lambda *_: self.on_clear())
        menu.append(clear_item)

        menu.append(Gtk.SeparatorMenuItem())

        quit_item = Gtk.MenuItem(label="Sair")
        quit_item.connect("activate", lambda *_: self.on_quit())
        menu.append(quit_item)

        menu.show_all()
        return menu

    def set_tooltip(self, text: str) -> None:
        try:
            self.indicator.set_title(text or config.APP_NAME)
        except Exception:
            pass