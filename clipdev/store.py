"""Camada de persistência do ClipDev (SQLite). Sem dependência de GTK."""

from __future__ import annotations

import hashlib
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from . import config

TEXT = "text"
IMAGE = "image"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    kind       TEXT    NOT NULL,
    content    TEXT    NOT NULL,
    preview    TEXT,
    hash       TEXT    NOT NULL UNIQUE,
    pinned     INTEGER NOT NULL DEFAULT 0,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_items_updated ON items(updated_at DESC);
"""


class Store:
    """Armazena itens de clipboard com dedup, pin e retenção."""

    def __init__(self, path: Optional[str] = None, max_unpinned: Optional[int] = None):
        self.path = str(path) if path else str(config.db_path())
        self.max_unpinned = config.MAX_UNPINNED if max_unpinned is None else max_unpinned
        self._conn = sqlite3.connect(self.path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    # -- utilidades ----------------------------------------------------------
    @staticmethod
    def hash_content(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    @staticmethod
    def _now() -> int:
        """Timestamp em milissegundos (resolução suficiente p/ ordenação estável)."""
        return int(time.time() * 1000)

    # -- escrita -------------------------------------------------------------
    def add(self, kind: str, content: str, preview: str, hash_: str) -> Tuple[int, bool]:
        """Adiciona item. Se já existir (mesmo hash), sobe ao topo.

        Retorna (id, criado) onde ``criado`` é False quando era duplicado.
        """
        now = self._now()
        row = self._conn.execute("SELECT id FROM items WHERE hash=?", (hash_,)).fetchone()
        if row is not None:
            self._conn.execute(
                "UPDATE items SET updated_at=? WHERE id=?", (now, row["id"])
            )
            self._conn.commit()
            self._enforce_limit()
            return int(row["id"]), False

        cur = self._conn.execute(
            "INSERT INTO items(kind, content, preview, hash, pinned, created_at, updated_at)"
            " VALUES(?,?,?,?,0,?,?)",
            (kind, content, preview, hash_, now, now),
        )
        self._conn.commit()
        new_id = int(cur.lastrowid)
        self._enforce_limit()
        return new_id, True

    def set_pinned(self, item_id: int, pinned: bool) -> None:
        self._conn.execute(
            "UPDATE items SET pinned=? WHERE id=?", (1 if pinned else 0, item_id)
        )
        self._conn.commit()
        self._enforce_limit()

    def toggle_pinned(self, item_id: int) -> bool:
        row = self._conn.execute(
            "SELECT pinned FROM items WHERE id=?", (item_id,)
        ).fetchone()
        if row is None:
            return False
        new = not bool(row["pinned"])
        self.set_pinned(item_id, new)
        return new

    def delete(self, item_id: int, delete_files: bool = True) -> None:
        row = self._conn.execute(
            "SELECT kind, content FROM items WHERE id=?", (item_id,)
        ).fetchone()
        if row is None:
            return
        if delete_files and row["kind"] == IMAGE:
            self._remove_image_files(row["content"])
        self._conn.execute("DELETE FROM items WHERE id=?", (item_id,))
        self._conn.commit()

    def clear_unpinned(self, delete_files: bool = True) -> int:
        rows = self._conn.execute(
            "SELECT id FROM items WHERE pinned=0"
        ).fetchall()
        for r in rows:
            self.delete(int(r["id"]), delete_files=delete_files)
        return len(rows)

    # -- leitura -------------------------------------------------------------
    def list_items(self, query: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        sql = "SELECT * FROM items"
        params: List[Any] = []
        if query:
            sql += " WHERE content LIKE ? OR preview LIKE ?"
            like = f"%{query}%"
            params += [like, like]
        sql += " ORDER BY pinned DESC, updated_at DESC, id DESC"
        if limit:
            sql += " LIMIT ?"
            params.append(limit)
        return [dict(r) for r in self._conn.execute(sql, params).fetchall()]

    def get(self, item_id: int) -> Optional[Dict[str, Any]]:
        row = self._conn.execute("SELECT * FROM items WHERE id=?", (item_id,)).fetchone()
        return dict(row) if row else None

    def count(self) -> int:
        return int(self._conn.execute("SELECT COUNT(*) AS c FROM items").fetchone()["c"])

    def count_unpinned(self) -> int:
        return int(
            self._conn.execute(
                "SELECT COUNT(*) AS c FROM items WHERE pinned=0"
            ).fetchone()["c"]
        )

    # -- interno -------------------------------------------------------------
    def _enforce_limit(self) -> None:
        rows = self._conn.execute(
            "SELECT id FROM items WHERE pinned=0 ORDER BY updated_at DESC, id DESC"
        ).fetchall()
        excess = rows[self.max_unpinned:]
        for r in excess:
            self.delete(int(r["id"]), delete_files=True)

    @staticmethod
    def _remove_image_files(content: str) -> None:
        try:
            p = Path(content)
            if p.exists():
                p.unlink()
            thumb = p.with_name(f"{p.stem}_thumb{p.suffix}")
            if thumb.exists():
                thumb.unlink()
        except OSError:
            pass

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:
            pass