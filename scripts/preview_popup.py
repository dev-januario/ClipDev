"""Renderiza o popup com dados de exemplo e salva um PNG (inspeção visual).

Não faz parte do app; usa Gtk.OffscreenWindow para não depender de captura de tela.
"""

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ["CLIPDEV_DATA_DIR"] = tempfile.mkdtemp(prefix="clipdev-preview-")

import gi  # noqa: E402

gi.require_version("Gtk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import GdkPixbuf, GLib, Gtk  # noqa: E402

from clipdev import config, images, popup, store as st  # noqa: E402

OUT = sys.argv[1] if len(sys.argv) > 1 else "/tmp/clipdev-popup.png"

PINNED = [
    "Endereço: Rua das Palmeiras, 342, apto 71",
    "Pix: alys@exemplo.com",
]
UNPINNED = [
    "https://github.com/aly/ClipDev",
    "def calcular_retorno(investimento, taxa):",
    "Nota fiscal 2026-10 — R$ 1.284,90",
    "#!/usr/bin/env python3",
    "Reunião de arquitetura às 14h30 (horário de Brasília)",
    "ssh-rsa AAAAB3NzaC1yc2EAAAADAQAB...",
    "SELECT * FROM items WHERE pinned=1;",
    "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
    "https://news.ycombinator.com/item?id=987654",
    "sudo apt install gir1.2-ayatanaappindicator3-0.1",
    "Chave de API: sk-teste-nao-real",
    "42.001-230 — Rio de Janeiro/RJ",
    "O último item visível sem rolar",
]


def seed(store):
    for text in PINNED:
        h = st.Store.hash_content(text.encode())
        item_id, _ = store.add(st.TEXT, text, text, h)
        store.set_pinned(item_id, True)

    for text in UNPINNED:
        h = st.Store.hash_content(text.encode())
        store.add(st.TEXT, text, text, h)

    pb = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, True, 8, 240, 160)
    pb.fill(0x0086FFFF)
    ok, buf = pb.save_to_bufferv("png", [], [])
    if ok:
        info = images.save_image_bytes(bytes(buf), fmt="png")
        store.add(st.IMAGE, info["path"], info["thumb"], info["hash"])


def main():
    store = st.Store()
    seed(store)

    win = popup.Popup(store, copy_cb=lambda item: None)
    win.refresh()

    root = win.get_child()
    win.remove(root)

    off = Gtk.OffscreenWindow()
    off.set_size_request(config.POPUP_WIDTH, config.POPUP_HEIGHT)
    off.get_style_context().add_class("clipdev-window")
    off.add(root)
    off.show_all()

    def capture():
        pb = off.get_pixbuf()
        if pb is None:
            print("pixbuf nulo")
        else:
            pb.savev(OUT, "png", [], [])
            print(f"salvo: {OUT} ({pb.get_width()}x{pb.get_height()})")
        Gtk.main_quit()
        return False

    GLib.timeout_add(700, capture)
    Gtk.main()


if __name__ == "__main__":
    main()