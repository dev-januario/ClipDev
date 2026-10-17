"""Popup principal do ClipDev.

Janela GTK sem decoração, ancorada no canto superior direito, com campo de
busca, lista rolável (15 linhas visíveis, 15px cada) e ações por hover
(copiar, fixar, excluir). Tema aplicado via style.css.
"""

from __future__ import annotations

from typing import Callable, Dict, Optional

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gdk, GdkPixbuf, GLib, Gtk  # noqa: E402

from . import config, images, store as st  # noqa: E402

CopyCallback = Callable[[Dict], None]


class Popup(Gtk.Window):
    def __init__(self, store: "st.Store", copy_cb: CopyCallback, on_quit: Optional[Callable[[], None]] = None):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.store = store
        self.copy_cb = copy_cb
        self.on_quit = on_quit
        self._rows: Dict[int, Gtk.ListBoxRow] = {}

        self.set_decorated(False)
        self.set_resizable(False)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_keep_above(True)
        self.set_type_hint(Gdk.WindowTypeHint.POPUP_MENU)
        self.set_accept_focus(True)
        self.set_default_size(config.POPUP_WIDTH, config.POPUP_HEIGHT)

        self.get_style_context().add_class("clipdev-window")
        self._load_css()

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        root.set_size_request(config.POPUP_WIDTH, -1)
        self.root = root
        self.add(root)

        self.search = Gtk.SearchEntry()
        self.search.get_style_context().add_class("search-entry")
        self.search.set_placeholder_text("Buscar no histórico…")
        self.search.connect("search-changed", lambda *_: self.refresh())
        root.pack_start(self.search, False, False, 0)

        self.scrolled = Gtk.ScrolledWindow()
        self.scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        # altura fixa: exibe exatamente VISIBLE_ROWS linhas completas
        self.scrolled.set_min_content_height(config.LIST_HEIGHT)
        self.scrolled.set_max_content_height(config.LIST_HEIGHT)
        self.scrolled.set_propagate_natural_height(False)

        self.listbox = Gtk.ListBox()
        self.listbox.get_style_context().add_class("clipdev-list")
        self.listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.listbox.set_activate_on_single_click(True)
        self.listbox.connect("row-activated", self._on_row_activated)
        self.scrolled.add(self.listbox)
        root.pack_start(self.scrolled, True, True, 0)

        self.connect("key-press-event", self._on_key_press)
        self.connect("delete-event", self._on_delete_event)
        self.connect("focus-out-event", self._on_focus_out)

    # -- CSS -----------------------------------------------------------------
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

    # -- visibilidade --------------------------------------------------------
    def toggle(self) -> None:
        if self.get_visible():
            self.hide()
        else:
            self.show_popup()

    def show_popup(self) -> None:
        self.refresh()
        self._position()
        self.show_all()
        self.search.set_text("")
        self._select_first()
        self.present()
        GLib.idle_add(lambda: self.search.grab_focus() or False)

    def _position(self) -> None:
        display = Gdk.Display.get_default()
        if display is None:
            return
        monitor = display.get_primary_monitor()
        geo = monitor.get_workarea()
        win_w, win_h = self.get_size()
        if win_w <= 1:
            win_w = config.POPUP_WIDTH
            win_h = config.POPUP_HEIGHT
        x = geo.x + geo.width - win_w - config.POPUP_MARGIN
        y = geo.y + config.POPUP_MARGIN
        self.move(max(geo.x, x), max(geo.y, y))

    def _select_first(self) -> None:
        rows = self.listbox.get_children()
        if rows:
            self.listbox.select_row(rows[0])

    # -- construção da lista -------------------------------------------------
    def refresh(self) -> None:
        for child in self.listbox.get_children():
            self.listbox.remove(child)
        self._rows.clear()

        query = self.search.get_text().strip() or None
        for item in self.store.list_items(query=query):
            row = self._build_row(item)
            self._rows[int(item["id"])] = row
            self.listbox.add(row)
        self.listbox.show_all()
        self._select_first()

    def _build_row(self, item: Dict) -> Gtk.ListBoxRow:
        row = Gtk.ListBoxRow()
        row.clipdev_id = int(item["id"])  # type: ignore[attr-defined]
        if item["pinned"]:
            row.get_style_context().add_class("pinned")

        eventbox = Gtk.EventBox()
        eventbox.set_visible_window(False)

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        hbox.set_margin_start(4)
        hbox.set_margin_end(4)
        eventbox.add(hbox)

        hbox.pack_start(self._build_leading_icon(item), False, False, 0)

        label = Gtk.Label(label=self._row_text(item))
        label.get_style_context().add_class("row-label")
        label.set_xalign(0.0)
        label.set_ellipsize(3)  # Pango.EllipsizeMode.END
        label.set_single_line_mode(True)
        label.set_hexpand(True)
        hbox.pack_start(label, True, True, 0)

        actions = self._build_actions(item)
        hbox.pack_end(actions, False, False, 0)

        # ações aparecem só no hover
        actions.set_no_show_all(True)
        actions.hide()
        eventbox.connect("enter-notify-event", lambda *_: actions.show())
        eventbox.connect("leave-notify-event", lambda *_: actions.hide())

        row.add(eventbox)
        row.set_tooltip_text(item["content"] if item["kind"] == st.TEXT else "Imagem")
        return row

    def _build_leading_icon(self, item: Dict) -> Gtk.Widget:
        if item["kind"] == st.IMAGE:
            try:
                img = Gtk.Image.new_from_file(item["preview"])
                img.set_pixel_size(config.ROW_THUMB_SIZE)
                return img
            except Exception:
                pass
        icon = Gtk.Image.new_from_icon_name("text-x-generic-symbolic", Gtk.IconSize.MENU)
        icon.get_style_context().add_class("row-icon")
        icon.set_pixel_size(config.ROW_THUMB_SIZE)
        return icon

    @staticmethod
    def _row_text(item: Dict) -> str:
        if item["kind"] == st.IMAGE:
            return "Imagem"
        text = (item["preview"] or item["content"] or "").replace("\n", " ").strip()
        return text[:120]

    def _build_actions(self, item: Dict) -> Gtk.Box:
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        box.get_style_context().add_class("row-actions")
        item_id = int(item["id"])

        copy_btn = Gtk.Button.new_from_icon_name("edit-copy-symbolic", Gtk.IconSize.MENU)
        copy_btn.set_relief(Gtk.ReliefStyle.NONE)
        copy_btn.set_tooltip_text("Copiar")
        copy_btn.connect("clicked", lambda *_: self._copy(item_id))
        box.pack_start(copy_btn, False, False, 0)

        pin_btn = Gtk.Button.new_from_icon_name(
            "starred-symbolic" if item["pinned"] else "non-starred-symbolic",
            Gtk.IconSize.MENU,
        )
        pin_btn.set_relief(Gtk.ReliefStyle.NONE)
        pin_btn.set_tooltip_text("Desafixar" if item["pinned"] else "Fixar")
        if item["pinned"]:
            pin_btn.get_style_context().add_class("pin-active")
        pin_btn.connect("clicked", lambda *_: self._toggle_pin(item_id))
        box.pack_start(pin_btn, False, False, 0)

        del_btn = Gtk.Button.new_from_icon_name("user-trash-symbolic", Gtk.IconSize.MENU)
        del_btn.set_relief(Gtk.ReliefStyle.NONE)
        del_btn.set_tooltip_text("Excluir")
        del_btn.connect("clicked", lambda *_: self._delete(item_id))
        box.pack_start(del_btn, False, False, 0)
        return box

    # -- ações ---------------------------------------------------------------
    def _copy(self, item_id: int) -> None:
        item = self.store.get(item_id)
        if not item:
            return
        self.copy_cb(item)
        self.hide()

    def _toggle_pin(self, item_id: int) -> None:
        self.store.toggle_pinned(item_id)
        self.refresh()

    def _delete(self, item_id: int) -> None:
        self.store.delete(item_id)
        self.refresh()

    # -- eventos -------------------------------------------------------------
    def _on_row_activated(self, _listbox, row) -> None:  # noqa: ANN001
        item_id = getattr(row, "clipdev_id", None)
        if item_id is not None:
            self._copy(int(item_id))

    def _on_key_press(self, _widget, event) -> bool:  # noqa: ANN001
        key = event.keyval
        if key == Gdk.KEY_Escape:
            self.hide()
            return True
        if key == Gdk.KEY_Return or key == Gdk.KEY_KP_Enter:
            row = self.listbox.get_selected_row()
            if row is not None:
                self._on_row_activated(self.listbox, row)
            return True
        if key == Gdk.KEY_Delete:
            row = self.listbox.get_selected_row()
            if row is not None:
                self._delete(int(getattr(row, "clipdev_id")))
            return True
        if key in (Gdk.KEY_Down, Gdk.KEY_Up):
            self._move_selection(1 if key == Gdk.KEY_Down else -1)
            return True
        return False

    def _move_selection(self, delta: int) -> None:
        rows = self.listbox.get_children()
        if not rows:
            return
        current = self.listbox.get_selected_row()
        idx = rows.index(current) if current in rows else -1
        new_idx = min(max(idx + delta, 0), len(rows) - 1)
        self.listbox.select_row(rows[new_idx])
        rows[new_idx].grab_focus()

    def _on_delete_event(self, *_args) -> bool:
        self.hide()
        return True  # não destrói; apenas esconde

    def _on_focus_out(self, _widget, _event) -> bool:
        # fecha ao clicar fora (mas não durante o clique num botão interno)
        GLib.timeout_add(120, self._hide_if_unfocused)
        return False

    def _hide_if_unfocused(self) -> bool:
        if self.get_visible() and not self.is_active():
            self.hide()
        return False