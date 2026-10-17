"""Script temporário: renderiza o popup com dados de exemplo e salva um PNG.

Usado para inspeção visual durante o desenvolvimento. Não faz parte do app.
"""

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# store temporário e isolado
os.environ["CLIPDEV_DATA_DIR"] = tempfile.mkdtemp(prefix="clipdev-preview-")

import gi  # noqa: E402

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk  # noqa: E402

from clipdev import config, popup, store as st  # noqa: E402

OUT = sys.argv[1] if len(sys.argv) > 1 else "/tmp/clipdev-popup.png"

SAMPLES = [
    ("https://github.com/aly/ClipDev", False),
    ("def calcular_retorno(investimento, taxa):", False),
    ("Nota fiscal 2026-10 — R$ 1.284,90", False),
    ("Endereço: Rua das Palmeiras, 342, apto 71", True),   # fixado (amarelo)
    ("#!/usr/bin/env python3", False),
    ("Reunião de arquitetura às 14h30 (horário de Brasília)", False),
    ("ssh-rsa AAAAB3NzaC1yc2EAAAADAQAB...", False),
    ("SELECT * FROM items WHERE pinned=1;", False),
    ("Pix: alys@exemplo.com", False),
    ("Lorem ipsum dolor sit amet, consectetur adipiscing elit.", False),
    ("https://news.ycombinator.com/item?id=987654", False),
    ("sudo apt install gir1.2-ayatanaappindicator3-0.1", False),
    ("Chave de API: sk-teste-nao-real", False),
    ("42.001-230 — Rio de Janeiro/RJ", False),
    ("O último item visível sem rolar", False),
    ("Item 16 (só aparece ao rolar)", False),
    ("Item 17 (só aparece ao rolar)", False),
]


def seed(store):
    for text, pinned in SAMPLES:
        h = st.Store.hash_content(text.encode())
        item_id, _ = store.add(st.TEXT, text, text, h)
        if pinned:
            store.set_pinned(item_id, True)


def main():
    store = st.Store()
    seed(store)

    win = popup.Popup(store, copy_cb=lambda item: None)
    win.refresh()

    # move o conteúdo para uma janela offscreen e renderiza num pixbuf
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