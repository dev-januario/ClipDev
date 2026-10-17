"""Testes de retenção envolvendo arquivos de imagem em disco."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gi  # noqa: E402

gi.require_version("GdkPixbuf", "2.0")
from gi.repository import GdkPixbuf  # noqa: E402

from clipdev import images, store as st  # noqa: E402


def _png_bytes(color):
    pb = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, True, 8, 40, 40)
    pb.fill((color[0] << 24) | (color[1] << 16) | (color[2] << 8) | 0xFF)
    ok, buf = pb.save_to_bufferv("png", [], [])
    assert ok
    return bytes(buf)


def test_evicted_image_removes_files(tmp_path, monkeypatch):
    monkeypatch.setenv("CLIPDEV_DATA_DIR", str(tmp_path / "data"))
    s = st.Store(path=str(tmp_path / "r.db"), max_unpinned=3)

    first = None
    for i in range(5):
        data = _png_bytes((i * 10 % 256, 100, 200))
        info = images.save_image_bytes(data, fmt="png")
        if first is None:
            first = info
        s.add(st.IMAGE, info["path"], info["thumb"], info["hash"])

    # o primeiro item foi evictado e seus arquivos apagados
    assert s.count_unpinned() == 3
    assert not os.path.exists(first["path"])
    assert not os.path.exists(first["thumb"])


def test_pinned_image_files_survive(tmp_path, monkeypatch):
    monkeypatch.setenv("CLIPDEV_DATA_DIR", str(tmp_path / "data"))
    s = st.Store(path=str(tmp_path / "r.db"), max_unpinned=2)

    info = images.save_image_bytes(_png_bytes((1, 2, 3)), fmt="png")
    item_id, _ = s.add(st.IMAGE, info["path"], info["thumb"], info["hash"])
    s.set_pinned(item_id, True)

    for i in range(6):
        data = _png_bytes((i + 50, 10, 10))
        inf = images.save_image_bytes(data, fmt="png")
        s.add(st.IMAGE, inf["path"], inf["thumb"], inf["hash"])

    assert os.path.exists(info["path"])
    assert s.get(item_id)["pinned"] == 1
    assert s.count_unpinned() == 2