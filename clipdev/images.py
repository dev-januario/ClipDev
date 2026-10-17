"""Manipulação de imagens: salvar original, gerar thumbnail, dedup por hash.

Usa GdkPixbuf (funciona headless, sem display). Sem dependência de janela GTK.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Dict, Optional

import gi

gi.require_version("GdkPixbuf", "2.0")
from gi.repository import GdkPixbuf  # noqa: E402

from . import config  # noqa: E402

_FORMAT_EXT = {
    "png": "png",
    "jpeg": "jpg",
    "jpg": "jpg",
    "gif": "gif",
    "bmp": "bmp",
    "tiff": "tiff",
    "webp": "webp",
    "ico": "ico",
}


class NotAnImageError(ValueError):
    """Os bytes fornecidos não são uma imagem reconhecida."""


class ImageTooLargeError(ValueError):
    """A imagem excede o limite configurado."""


def _ext_for(fmt: Optional[str]) -> str:
    if not fmt:
        return "png"
    return _FORMAT_EXT.get(fmt.lower(), "png")


def load_pixbuf_from_bytes(data: bytes) -> GdkPixbuf.Pixbuf:
    loader = GdkPixbuf.PixbufLoader()
    try:
        loader.write(data)
        loader.close()
    except Exception as exc:  # GLib.Error
        raise NotAnImageError(str(exc)) from exc
    pb = loader.get_pixbuf()
    if pb is None:
        raise NotAnImageError("pixbuf vazio")
    return pb


def load_pixbuf(path: str) -> GdkPixbuf.Pixbuf:
    return GdkPixbuf.Pixbuf.new_from_file(path)


def make_thumbnail(pb: GdkPixbuf.Pixbuf, size: int = config.THUMB_SIZE) -> GdkPixbuf.Pixbuf:
    w, h = pb.get_width(), pb.get_height()
    scale = min(size / w, size / h, 1.0)
    tw, th = max(1, int(w * scale)), max(1, int(h * scale))
    return pb.scale_simple(tw, th, GdkPixbuf.InterpType.BILINEAR)


def preview_pixbuf(source, size: int = config.ROW_THUMB_SIZE) -> Optional[GdkPixbuf.Pixbuf]:
    """Carrega ``source`` (caminho de imagem/thumbnail) num pixbuf QUADRADO
    de ``size``×``size`` (com barras transparentes), para usar como prévia
    compacta na linha. Nunca amplia além de ``size``.
    """
    try:
        pb = GdkPixbuf.Pixbuf.new_from_file(str(source))
    except Exception:
        return None
    w, h = pb.get_width(), pb.get_height()
    if w <= 0 or h <= 0:
        return None
    scale = min(size / w, size / h, 1.0)
    tw, th = max(1, int(round(w * scale))), max(1, int(round(h * scale)))
    scaled = pb.scale_simple(tw, th, GdkPixbuf.InterpType.BILINEAR)
    canvas = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, True, 8, size, size)
    canvas.fill(0x00000000)
    scaled.composite(
        canvas, 0, 0, size, size, 0, 0, 1.0, 1.0,
        GdkPixbuf.InterpType.BILINEAR, 255,
    )
    return canvas


def save_image_bytes(
    data: bytes,
    fmt: Optional[str] = None,
    max_bytes: Optional[int] = None,
) -> Dict[str, str]:
    """Salva a imagem e sua thumbnail. Retorna dict com hash/path/thumb/ext.

    O original é gravado sem recompressão (bytes originais). A thumbnail é
    salva em PNG ao lado do original, com sufixo ``_thumb``.
    """
    limit = config.MAX_IMAGE_BYTES if max_bytes is None else max_bytes
    if len(data) > limit:
        raise ImageTooLargeError(f"{len(data)} bytes > limite {limit}")

    pb = load_pixbuf_from_bytes(data)
    h = hashlib.sha256(data).hexdigest()
    ext = _ext_for(fmt)
    img_dir = config.images_dir()

    path = img_dir / f"{h}.{ext}"
    thumb = img_dir / f"{h}_thumb.png"

    if not path.exists():
        path.write_bytes(data)
    if not thumb.exists():
        make_thumbnail(pb).savev(str(thumb), "png", [], [])

    return {
        "hash": h,
        "path": str(path),
        "thumb": str(thumb),
        "ext": ext,
        "width": str(pb.get_width()),
        "height": str(pb.get_height()),
    }


def thumb_path_for(content_path: str) -> Path:
    """Caminho esperado da thumbnail para um original (mesmo se ausente)."""
    p = Path(content_path)
    return p.with_name(f"{p.stem}_thumb.png")