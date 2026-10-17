"""Testes de images.py (headless, sem display)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gi  # noqa: E402

gi.require_version("GdkPixbuf", "2.0")
from gi.repository import GdkPixbuf  # noqa: E402

from clipdev import config, images  # noqa: E402


def _png_bytes(width=120, height=80, color=(0, 134, 255)):
    pb = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, True, 8, width, height)
    pb.fill((color[0] << 24) | (color[1] << 16) | (color[2] << 8) | 0xFF)
    ok, buf = pb.save_to_bufferv("png", [], [])
    assert ok
    return bytes(buf)


def test_save_creates_original_and_thumb(tmp_path, monkeypatch):
    monkeypatch.setenv("CLIPDEV_DATA_DIR", str(tmp_path))
    data = _png_bytes()
    info = images.save_image_bytes(data, fmt="png")

    assert os.path.exists(info["path"])
    assert os.path.exists(info["thumb"])
    assert info["hash"] == images.hashlib.sha256(data).hexdigest()


def test_thumbnail_is_scaled_down(tmp_path, monkeypatch):
    monkeypatch.setenv("CLIPDEV_DATA_DIR", str(tmp_path))
    info = images.save_image_bytes(_png_bytes(400, 300), fmt="png")
    tb = GdkPixbuf.Pixbuf.new_from_file(info["thumb"])
    assert max(tb.get_width(), tb.get_height()) <= config.THUMB_SIZE


def test_small_image_not_upscaled(tmp_path, monkeypatch):
    monkeypatch.setenv("CLIPDEV_DATA_DIR", str(tmp_path))
    info = images.save_image_bytes(_png_bytes(10, 10), fmt="png")
    tb = GdkPixbuf.Pixbuf.new_from_file(info["thumb"])
    assert tb.get_width() == 10 and tb.get_height() == 10


def test_dedup_same_bytes_same_path(tmp_path, monkeypatch):
    monkeypatch.setenv("CLIPDEV_DATA_DIR", str(tmp_path))
    data = _png_bytes()
    a = images.save_image_bytes(data, fmt="png")
    b = images.save_image_bytes(data, fmt="png")
    assert a["hash"] == b["hash"]
    assert a["path"] == b["path"]


def test_rejects_non_image(tmp_path, monkeypatch):
    monkeypatch.setenv("CLIPDEV_DATA_DIR", str(tmp_path))
    try:
        images.save_image_bytes(b"isto nao e imagem", fmt="png")
        assert False, "deveria lançar NotAnImageError"
    except images.NotAnImageError:
        pass


def test_rejects_oversize(tmp_path, monkeypatch):
    monkeypatch.setenv("CLIPDEV_DATA_DIR", str(tmp_path))
    data = _png_bytes()
    try:
        images.save_image_bytes(data, fmt="png", max_bytes=10)
        assert False, "deveria lançar ImageTooLargeError"
    except images.ImageTooLargeError:
        pass


def test_preview_is_square(tmp_path, monkeypatch):
    """A prévia da linha deve ser sempre quadrada (30x30), não a imagem inteira."""
    monkeypatch.setenv("CLIPDEV_DATA_DIR", str(tmp_path))
    for w, h in [(800, 600), (300, 900), (120, 80)]:
        info = images.save_image_bytes(_png_bytes(w, h), fmt="png")
        pv = images.preview_pixbuf(info["thumb"], config.ROW_THUMB_SIZE)
        assert pv is not None
        assert pv.get_width() == config.ROW_THUMB_SIZE
        assert pv.get_height() == config.ROW_THUMB_SIZE


def test_preview_has_alpha(tmp_path, monkeypatch):
    """Imagem larga deve caber com barras transparentes (canal alpha)."""
    monkeypatch.setenv("CLIPDEV_DATA_DIR", str(tmp_path))
    info = images.save_image_bytes(_png_bytes(400, 100), fmt="png")
    pv = images.preview_pixbuf(info["thumb"], 30)
    assert pv.get_has_alpha() is True


def test_preview_invalid_returns_none(tmp_path):
    assert images.preview_pixbuf(str(tmp_path / "naoexiste.png"), 30) is None


def test_preview_size_matches_config():
    assert config.ROW_THUMB_SIZE == 30
    assert config.ROW_HEIGHT == 40
    assert config.FONT_DEFAULT == 14