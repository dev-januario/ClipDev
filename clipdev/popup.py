"""Popup principal do ClipDev.

Layout:
    [ Campo de busca ]
    -------------------
    Fixados
    | | item fixado            ☆  ⚲  ⧉  🗑
    -------------------
    Não fixados
    | | item                   ☆  ⚲  ⧉  🗑
    -------------------
    Tamanho da fonte [- 13 +]   [⚙] [Limpar não fixados]

- A barra "| |" à esquerda é amarela nos fixados e transparente nos demais.
- A estrela é cinza quando solta e amarela quando fixada.
- O alfinete (map pin) é cinza quando solto e vermelho quando fixado.
"""

from __future__ import annotations

from typing import Callable, Dict, List, Optional

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gdk, GdkPixbuf, GLib, Gtk  # noqa: E402

from . import config, images, store as st  # noqa: E402

CopyCallback = Callable[[Dict], None]


class Popup(Gtk.Window):
    def __init__(
        self,
        store: "st.Store",
        copy_cb: CopyCallback,
        on_clear: Optional[Callable[[], None]] = None,
        on_prefs: Optional[Callable[[], None]] = None,
        on_font_change: Optional[Callable[[int], None]] = None,
    ):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.store = store
        self.copy_cb = copy_cb
        self.on_clear = on_clear
        self.on_prefs = on_prefs
        self.on_font_change = on_font_change
        self._item_rows: List[Gtk.ListBoxRow] = []
        self._settings = config.load_settings()
        self._font_size = config.clamp_font(self._settings.get("font_size", config.FONT_DEFAULT))

        self.set_decorated(False)
        self.set_resizable(False)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_keep_above(True)
        self.set_type_hint(Gdk.WindowTypeHint.POPUP_MENU)
        self.set_accept_focus(True)
        self.set_default_size(config.POPUP_WIDTH, config.POPUP_HEIGHT)

        self.get_style_context().add_class("clipdev-window")
        self._base_provider = self._load_css(config.style_path())
        self._font_provider = Gtk.CssProvider()
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            self._font_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 1,
        )
        self._apply_font_size(self._font_size, save=False)

        self._build_ui()
        self.connect("key-press-event", self._on_key_press)
        self.connect("delete-event", self._on_delete_event)
        self.connect("focus-out-event", self._on_focus_out)

    # -- CSS -----------------------------------------------------------------
    @staticmethod
    def _load_css(path) -> Optional[Gtk.CssProvider]:
        try:
            provider = Gtk.CssProvider()
            provider.load_from_path(str(path))
            Gtk.StyleContext.add_provider_for_screen(
                Gdk.Screen.get_default(),
                provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
            )
            return provider
        except Exception:
            return None

    def _apply_font_size(self, size: int, save: bool = True) -> None:
        self._font_size = config.clamp_font(size)
        # a altura da linha acompanha a fonte, com piso em ROW_HEIGHT (40px)
        row_h = max(config.ROW_HEIGHT, self._font_size + 26)
        css = (
            f".row-label {{ font-size: {self._font_size}px; }}\n"
            f".clipdev-list row {{ min-height: {row_h}px; }}\n"
            f".row-label.pinned {{ font-size: {self._font_size}px; }}\n"
        )
        try:
            self._font_provider.load_from_data(css.encode())
        except Exception:
            pass
        if getattr(self, "_font_value_label", None) is not None:
            self._font_value_label.set_text(str(self._font_size))
        if save:
            self._settings["font_size"] = self._font_size
            config.save_settings(self._settings)
            if self.on_font_change:
                self.on_font_change(self._font_size)

    # -- construção da UI ----------------------------------------------------
    def _build_ui(self) -> None:
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
        self.scrolled.set_min_content_height(config.VISIBLE_ROWS * config.ROW_HEIGHT)
        self.scrolled.set_max_content_height(config.VISIBLE_ROWS * config.ROW_HEIGHT)
        self.scrolled.set_propagate_natural_height(False)

        self.listbox = Gtk.ListBox()
        self.listbox.get_style_context().add_class("clipdev-list")
        self.listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.listbox.set_activate_on_single_click(True)
        self.listbox.connect("row-activated", self._on_row_activated)
        self.scrolled.add(self.listbox)
        root.pack_start(self.scrolled, True, True, 0)

        root.pack_start(self._build_footer(), False, False, 0)

    def _build_footer(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        box.get_style_context().add_class("clipdev-footer")

        label = Gtk.Label(label="Tamanho da fonte")
        label.get_style_context().add_class("footer-label")
        box.pack_start(label, False, False, 0)

        minus = Gtk.Button(label="−")
        minus.get_style_context().add_class("footer-button")
        minus.set_tooltip_text("Diminuir fonte")
        minus.connect("clicked", lambda *_: self._apply_font_size(self._font_size - 1))
        box.pack_start(minus, False, False, 0)

        self._font_value_label = Gtk.Label(label=str(self._font_size))
        self._font_value_label.get_style_context().add_class("prefs-value")
        box.pack_start(self._font_value_label, False, False, 0)

        plus = Gtk.Button(label="+")
        plus.get_style_context().add_class("footer-button")
        plus.set_tooltip_text("Aumentar fonte")
        plus.connect("clicked", lambda *_: self._apply_font_size(self._font_size + 1))
        box.pack_start(plus, False, False, 0)

        box.pack_start(Gtk.Box(), True, True, 0)  # espaçador

        prefs = Gtk.Button(label="⚙")
        prefs.get_style_context().add_class("footer-button")
        prefs.set_tooltip_text("Preferências")
        prefs.connect("clicked", lambda *_: self.on_prefs and self.on_prefs())
        box.pack_start(prefs, False, False, 0)

        clear = Gtk.Button(label="Limpar não fixados")
        clear.get_style_context().add_class("footer-button")
        clear.get_style_context().add_class("danger")
        clear.set_tooltip_text("Apaga todo o histórico não fixado")
        clear.connect("clicked", lambda *_: self._clear_unpinned())
        box.pack_start(clear, False, False, 0)
        return box

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
        if self._item_rows:
            self.listbox.select_row(self._item_rows[0])

    # -- lista ---------------------------------------------------------------
    def refresh(self) -> None:
        for child in self.listbox.get_children():
            self.listbox.remove(child)
        self._item_rows = []

        query = self.search.get_text().strip() or None
        items = self.store.list_items(query=query)
        pinned = [i for i in items if i["pinned"]]
        unpinned = [i for i in items if not i["pinned"]]

        if pinned:
            self.listbox.add(self._section_header("Fixados"))
            for item in pinned:
                self._add_item_row(item)

        if unpinned:
            self.listbox.add(self._section_header("Não fixados"))
            for item in unpinned:
                self._add_item_row(item)

        if not items:
            empty = Gtk.ListBoxRow()
            empty.set_selectable(False)
            empty.set_activatable(False)
            lbl = Gtk.Label(label="Nada por aqui ainda…")
            lbl.get_style_context().add_class("section-header")
            lbl.set_margin_top(8)
            lbl.set_margin_bottom(8)
            empty.add(lbl)
            self.listbox.add(empty)

        self.listbox.show_all()
        self._select_first()

    def _section_header(self, text: str) -> Gtk.ListBoxRow:
        row = Gtk.ListBoxRow()
        row.set_selectable(False)
        row.set_activatable(False)
        lbl = Gtk.Label(label=text, xalign=0.0)
        lbl.get_style_context().add_class("section-header")
        row.add(lbl)
        return row

    def _add_item_row(self, item: Dict) -> None:
        row = Gtk.ListBoxRow()
        row.clipdev_id = int(item["id"])  # type: ignore[attr-defined]

        eventbox = Gtk.EventBox()
        eventbox.set_visible_window(False)
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        hbox.set_margin_start(6)
        hbox.set_margin_end(6)
        eventbox.add(hbox)

        # barra "| |" à esquerda
        bar = Gtk.Box()
        bar.get_style_context().add_class("pin-bar")
        if item["pinned"]:
            bar.get_style_context().add_class("pinned")
        bar.set_size_request(3, -1)
        hbox.pack_start(bar, False, False, 0)

        # ícone/thumbnail
        hbox.pack_start(self._build_leading_icon(item), False, False, 0)

        # rótulo
        label = Gtk.Label(label=self._row_text(item))
        label.get_style_context().add_class("row-label")
        if item["pinned"]:
            label.get_style_context().add_class("pinned")
        label.set_xalign(0.0)
        label.set_ellipsize(3)
        label.set_single_line_mode(True)
        label.set_hexpand(True)
        hbox.pack_start(label, True, True, 0)

        # ações
        actions = self._build_actions(item)
        hbox.pack_end(actions, False, False, 0)

        row.add(eventbox)
        row.set_tooltip_text(item["content"] if item["kind"] == st.TEXT else "Imagem")
        self.listbox.add(row)
        self._item_rows.append(row)

    def _build_leading_icon(self, item: Dict) -> Gtk.Widget:
        if item["kind"] == st.IMAGE:
            # prévia quadrada fixa (30x30): a imagem inteira NÃO é exibida
            pb = images.preview_pixbuf(item["preview"], config.ROW_THUMB_SIZE)
            if pb is not None:
                return Gtk.Image.new_from_pixbuf(pb)
        icon = Gtk.Image.new_from_icon_name("text-x-generic-symbolic", Gtk.IconSize.MENU)
        icon.get_style_context().add_class("icon-action")
        icon.set_pixel_size(config.ROW_ICON_SIZE)
        return icon

    @staticmethod
    def _row_text(item: Dict) -> str:
        if item["kind"] == st.IMAGE:
            return "Imagem"
        text = (item["preview"] or item["content"] or "").replace("\n", " ").strip()
        return text[:160]

    def _build_actions(self, item: Dict) -> Gtk.Box:
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        box.get_style_context().add_class("row-actions")
        item_id = int(item["id"])
        pinned = bool(item["pinned"])

        # estrela (fixar): cinza -> amarela
        star = Gtk.Button.new_from_icon_name(
            "starred-symbolic" if pinned else "non-starred-symbolic", Gtk.IconSize.MENU
        )
        star.set_relief(Gtk.ReliefStyle.NONE)
        star.set_tooltip_text("Desafixar" if pinned else "Fixar")
        star.get_style_context().add_class("icon-star")
        if pinned:
            star.get_style_context().add_class("pinned")
        star.connect("clicked", lambda *_: self._toggle_pin(item_id))
        box.pack_start(star, False, False, 0)

        copy_btn = Gtk.Button.new_from_icon_name("edit-copy-symbolic", Gtk.IconSize.MENU)
        copy_btn.set_relief(Gtk.ReliefStyle.NONE)
        copy_btn.set_tooltip_text("Copiar")
        copy_btn.get_style_context().add_class("icon-action")
        copy_btn.connect("clicked", lambda *_: self._copy(item_id))
        box.pack_start(copy_btn, False, False, 0)

        del_btn = Gtk.Button.new_from_icon_name("user-trash-symbolic", Gtk.IconSize.MENU)
        del_btn.set_relief(Gtk.ReliefStyle.NONE)
        del_btn.set_tooltip_text("Excluir")
        del_btn.get_style_context().add_class("icon-action")
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

    def _clear_unpinned(self) -> None:
        if self.on_clear:
            self.on_clear()
        else:
            self.store.clear_unpinned()
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
        if key in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            row = self.listbox.get_selected_row()
            if row is not None and getattr(row, "clipdev_id", None) is not None:
                self._on_row_activated(self.listbox, row)
            return True
        if key == Gdk.KEY_Delete:
            row = self.listbox.get_selected_row()
            if row is not None and getattr(row, "clipdev_id", None) is not None:
                self._delete(int(getattr(row, "clipdev_id")))
            return True
        if key == Gdk.KEY_Down:
            self._move_selection(1)
            return True
        if key == Gdk.KEY_Up:
            self._move_selection(-1)
            return True
        return False

    def _move_selection(self, delta: int) -> None:
        if not self._item_rows:
            return
        current = self.listbox.get_selected_row()
        try:
            idx = self._item_rows.index(current)
        except ValueError:
            idx = -1
        new_idx = min(max(idx + delta, 0), len(self._item_rows) - 1)
        row = self._item_rows[new_idx]
        self.listbox.select_row(row)
        row.grab_focus()

    def _on_delete_event(self, *_args) -> bool:
        self.hide()
        return True

    def _on_focus_out(self, _widget, _event) -> bool:
        GLib.timeout_add(120, self._hide_if_unfocused)
        return False

    def _hide_if_unfocused(self) -> bool:
        if self.get_visible() and not self.is_active():
            self.hide()
        return False

    def get_font_size(self) -> int:
        return self._font_size