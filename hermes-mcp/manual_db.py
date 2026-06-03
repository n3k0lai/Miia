"""SQLite FTS5 storage for the Mazda service manual."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from manual_parse import ManualPage

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;

CREATE TABLE IF NOT EXISTS meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS pages (
  rowid INTEGER PRIMARY KEY,
  page_id TEXT NOT NULL,
  path TEXT NOT NULL UNIQUE,
  title TEXT NOT NULL,
  section TEXT NOT NULL,
  subsystem TEXT NOT NULL,
  content TEXT NOT NULL,
  dtc_codes TEXT NOT NULL DEFAULT '[]',
  links TEXT NOT NULL DEFAULT '[]'
);

CREATE INDEX IF NOT EXISTS idx_pages_page_id ON pages(page_id);
CREATE INDEX IF NOT EXISTS idx_pages_section ON pages(section);

CREATE VIRTUAL TABLE IF NOT EXISTS pages_fts USING fts5(
  title,
  content,
  section,
  subsystem,
  page_id UNINDEXED,
  path UNINDEXED,
  tokenize='porter unicode61'
);

CREATE TABLE IF NOT EXISTS toc (
  rowid INTEGER PRIMARY KEY,
  title TEXT NOT NULL,
  path TEXT,
  parent_rowid INTEGER,
  depth INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS dtc_index (
  dtc TEXT NOT NULL,
  page_rowid INTEGER NOT NULL,
  PRIMARY KEY (dtc, page_rowid),
  FOREIGN KEY (page_rowid) REFERENCES pages(rowid)
);
CREATE INDEX IF NOT EXISTS idx_dtc ON dtc_index(dtc);
"""


class ManualDatabase:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._conn: sqlite3.Connection | None = None

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def initialize(self) -> None:
        self.conn.executescript(SCHEMA)

    def clear(self) -> None:
        self.conn.executescript(
            "DELETE FROM dtc_index; DELETE FROM pages_fts; DELETE FROM pages; DELETE FROM toc;"
        )
        self.conn.commit()

    def set_meta(self, key: str, value: str) -> None:
        self.conn.execute(
            "INSERT INTO meta(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )

    def insert_page(self, page: ManualPage) -> int:
        cur = self.conn.execute(
            """
            INSERT INTO pages(page_id, path, title, section, subsystem, content, dtc_codes, links)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                page.page_id,
                page.path,
                page.title,
                page.section,
                page.subsystem,
                page.content,
                json.dumps(page.dtc_codes),
                json.dumps(page.links),
            ),
        )
        rowid = cur.lastrowid
        assert rowid is not None
        self.conn.execute(
            """
            INSERT INTO pages_fts(rowid, title, content, section, subsystem, page_id, path)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (rowid, page.title, page.content, page.section, page.subsystem, page.page_id, page.path),
        )
        for code in page.dtc_codes:
            self.conn.execute(
                "INSERT OR IGNORE INTO dtc_index(dtc, page_rowid) VALUES (?, ?)",
                (code, rowid),
            )
        return rowid

    def insert_toc(self, title: str, path: str | None, parent_rowid: int | None, depth: int) -> int:
        cur = self.conn.execute(
            "INSERT INTO toc(title, path, parent_rowid, depth) VALUES (?, ?, ?, ?)",
            (title, path, parent_rowid, depth),
        )
        assert cur.lastrowid is not None
        return cur.lastrowid

    def commit(self) -> None:
        self.conn.commit()

    def search(
        self,
        query: str,
        *,
        limit: int = 8,
        section: str | None = None,
    ) -> list[dict]:
        terms = _fts_query(query)
        if not terms:
            return []
        sql = """
            SELECT
              p.page_id,
              p.path,
              p.title,
              p.section,
              p.subsystem,
              snippet(pages_fts, 1, '[[', ']]', ' … ', 24) AS snippet,
              bm25(pages_fts) AS rank
            FROM pages_fts
            JOIN pages p ON p.rowid = pages_fts.rowid
            WHERE pages_fts MATCH ?
        """
        params: list[object] = [terms]
        if section:
            sql += " AND p.section = ?"
            params.append(section)
        sql += " ORDER BY rank LIMIT ?"
        params.append(limit)
        rows = self.conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def lookup_dtc(self, code: str, *, limit: int = 12) -> list[dict]:
        normalized = code.strip().upper().replace("DTC", "").strip()
        if ":" not in normalized and len(normalized) == 5:
            prefix = normalized[0]
            rest = normalized[1:]
            normalized = f"{prefix}{rest[:4]}:{rest[4:]}" if len(rest) >= 4 else normalized
        rows = self.conn.execute(
            """
            SELECT p.page_id, p.path, p.title, p.section, p.subsystem,
                   substr(p.content, 1, 400) AS excerpt,
                   CASE
                     WHEN p.title LIKE ? THEN 0
                     WHEN p.title LIKE ? THEN 1
                     ELSE 2
                   END AS sort_key
            FROM dtc_index d
            JOIN pages p ON p.rowid = d.page_rowid
            WHERE d.dtc = ?
            ORDER BY sort_key, length(p.content), p.title
            LIMIT ?
            """,
            (
                f"DTC {normalized}%",
                f"%{normalized}%",
                normalized,
                limit,
            ),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_page(self, *, page_id: str | None = None, path: str | None = None) -> dict | None:
        if path:
            row = self.conn.execute("SELECT * FROM pages WHERE path = ?", (path,)).fetchone()
        elif page_id:
            row = self.conn.execute(
                "SELECT * FROM pages WHERE page_id = ? ORDER BY length(content) DESC LIMIT 1",
                (page_id,),
            ).fetchone()
        else:
            return None
        if not row:
            return None
        data = dict(row)
        data["dtc_codes"] = json.loads(data["dtc_codes"])
        data["links"] = json.loads(data["links"])
        return data

    def list_sections(self) -> list[dict]:
        rows = self.conn.execute(
            """
            SELECT section, COUNT(*) AS pages
            FROM pages
            GROUP BY section
            ORDER BY pages DESC
            """
        ).fetchall()
        return [dict(r) for r in rows]

    def toc_tree(self, *, max_depth: int = 2) -> list[dict]:
        rows = self.conn.execute(
            "SELECT rowid, title, path, parent_rowid, depth FROM toc WHERE depth <= ? ORDER BY rowid",
            (max_depth,),
        ).fetchall()
        return [dict(r) for r in rows]

    def stats(self) -> dict:
        pages = self.conn.execute("SELECT COUNT(*) FROM pages").fetchone()[0]
        dtcs = self.conn.execute("SELECT COUNT(DISTINCT dtc) FROM dtc_index").fetchone()[0]
        meta = {r["key"]: r["value"] for r in self.conn.execute("SELECT key, value FROM meta")}
        return {"pages": pages, "distinct_dtcs": dtcs, **meta}


def _fts_query(query: str) -> str:
    """Turn a natural-language query into a safe FTS5 AND query."""
    tokens = []
    for raw in query.split():
        word = "".join(c for c in raw if c.isalnum() or c in (":", "-", "_"))
        if len(word) < 2:
            continue
        tokens.append(f'"{word}"' if ":" in word else word)
    return " ".join(tokens)