"""Monitor da área de transferência via GTK3/Gdk.

Escuta o sinal ``owner-change`` da seleção CLIPBOARD e lê o conteúdo de forma
assíncrona (nunca bloqueia a UI). Suporta texto, imagens (raw ou via URI de
arquivo) e respeita uma flag de supressão para não recapturar cópias feitas
pelo próprio ClipDev.
"""

from __future__ import annotations

from typing import Callable, List, Optional

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gdk, GdkPixbuf, GLib, GObject, Gtk  # noqa: E402

from . import images, store as st  # noqa: E402

_TEXT_TARGETS = {
    "UTF8_STRING",
    "text/plain",
    "text/plain;charset=utf-8",
    "STRING",
    "TEXT",
}
_IMAGE_EXT = {"png", "jpg", "jpeg", "gif", "bmp", "tiff", "webp", "ico"}


class ClipboardMonitor(GObject.GObject):
    """Observa o clipboard e emite ``captured`` com o item persistido."""

    __gsignals__ = {
        # payload: dict com a linha recém-adicionada
        "captured": (GObject.SignalFlags.RUN_FIRST, None, (object,)),
    }

    def __init__(self, store: "st.Store") -> None:
        super().__init__()
        self.store = store
        self.clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        self._suppress = False
        self._last_hash: Optional[str] = None
        self._clipboard_handler = self.clipboard.connect(
            "owner-change", self._on_owner_change
        )

    # -- API pública ---------------------------------------------------------
    def start(self) -> None:
        """Captura o conteúdo atual do clipboard ao iniciar."""
        GLib.idle_add(lambda: self.clipboard.request_targets(self._on_targets) or False)

    def set_text(self, text: str) -> None:
        self._suppress = True
        self._last_hash = st.Store.hash_content(text.encode())
        self.clipboard.set_text(text, -1)
        self.clipboard.store()
        GLib.timeout_add(400, self._release_suppress)

    def set_image(self, path: str) -> None:
        self._suppress = True
        try:
            pb = GdkPixbuf.Pixbuf.new_from_file(path)
            self.clipboard.set_image(pb)
            self.clipboard.store()
        except Exception:
            pass
        GLib.timeout_add(400, self._release_suppress)

    # -- interno -------------------------------------------------------------
    def _release_suppress(self) -> bool:
        self._suppress = False
        return False  # não repete

    def _on_owner_change(self, clipboard, event) -> None:  # noqa: ANN001
        if self._suppress:
            return
        clipboard.request_targets(self._on_targets)

    def _on_targets(self, clipboard, targets, _data=None) -> None:  # noqa: ANN001
        names = {t.name() for t in (targets or [])}
        if any(n.startswith("image/") for n in names):
            clipboard.request_image(self._on_image)
        elif "text/uri-list" in names:
            clipboard.request_uris(self._on_uris)
        elif names & _TEXT_TARGETS:
            clipboard.request_text(self._on_text)

    def _on_text(self, clipboard, text, _data=None) -> None:  # noqa: ANN001
        if not text:
            return
        h = st.Store.hash_content(text.encode())
        if h == self._last_hash:
            return
        preview = " ".join(text.split())[:200]
        self._persist(st.TEXT, text, preview, h)

    def _on_image(self, clipboard, pixbuf, _data=None) -> None:  # noqa: ANN001
        if pixbuf is None:
            return
        ok, buf = pixbuf.save_to_bufferv("png", [], [])
        if not ok:
            return
        self._persist_image_bytes(bytes(buf), fmt="png")

    def _on_uris(self, clipboard, uris, _data=None) -> None:  # noqa: ANN001
        for uri in uris or []:
            path = self._uri_to_path(uri)
            if not path:
                continue
            ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""
            if ext in _IMAGE_EXT:
                try:
                    with open(path, "rb") as fh:
                        data = fh.read()
                    self._persist_image_bytes(data, fmt=ext)
                except (OSError, images.NotAnImageError, images.ImageTooLargeError):
                    continue

    def _persist_image_bytes(self, data: bytes, fmt: Optional[str]) -> None:
        try:
            info = images.save_image_bytes(data, fmt=fmt)
        except (images.NotAnImageError, images.ImageTooLargeError):
            return
        if info["hash"] == self._last_hash:
            return
        self._persist(st.IMAGE, info["path"], info["thumb"], info["hash"])

    def _persist(self, kind: str, content: str, preview: str, hash_: str) -> None:
        item_id, created = self.store.add(kind, content, preview, hash_)
        if not created:
            # dedup: ainda assim avisa a UI para reordenar
            item = self.store.get(item_id)
        else:
            item = self.store.get(item_id)
        if item:
            self.emit("captured", item)

    @staticmethod
    def _uri_to_path(uri: str) -> Optional[str]:
        if not uri.startswith("file://"):
            return None
        from urllib.parse import unquote, urlparse

        parsed = urlparse(uri)
        return unquote(parsed.path)