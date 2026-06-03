#!/usr/bin/env python3
"""Build the Hermes manual search index from manual/ HTML."""

from __future__ import annotations

import argparse
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

from manual_db import ManualDatabase
from manual_parse import parse_html_file

MANUAL_TITLE_RE = re.compile(r"<title>([^<]+)</title>", re.IGNORECASE)


class TocParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.stack: list[tuple[str, int | None]] = []
        self.entries: list[tuple[str, str | None, int, int | None]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = dict(attrs)
        if tag == "ul":
            self.stack.append(("ul", None))
        elif tag == "li":
            parent = self.stack[-1][1] if self.stack else None
            self.stack.append(("li", parent))
        elif tag == "a" and self.stack and self.stack[-1][0] == "li":
            href = attr.get("href")
            self.stack[-1] = ("li", href)

    def handle_endtag(self, tag: str) -> None:
        if tag in ("ul", "li") and self.stack:
            self.stack.pop()

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if not text or not self.stack or self.stack[-1][0] != "li":
            return
        href = self.stack[-1][1]
        depth = sum(1 for kind, _ in self.stack if kind == "ul") - 1
        parent = None
        for i in range(len(self.entries) - 1, -1, -1):
            if self.entries[i][2] < depth:
                parent = i
                break
        self.entries.append((text, href, depth, parent))


def index_toc(db: ManualDatabase, index_html: Path, manual_root: Path) -> None:
    html = index_html.read_text(encoding="utf-8", errors="replace")
    match = MANUAL_TITLE_RE.search(html)
    if match:
        db.set_meta("manual_title", match.group(1).strip())

    parser = TocParser()
    parser.feed(html)
    rowid_map: dict[int, int] = {}
    for idx, (title, href, depth, parent_idx) in enumerate(parser.entries):
        path = None
        if href and not href.startswith("http"):
            path = str(Path(href).as_posix())
        parent_rowid = rowid_map.get(parent_idx) if parent_idx is not None else None
        rowid = db.insert_toc(title, path, parent_rowid, depth)
        rowid_map[idx] = rowid


def main() -> int:
    ap = argparse.ArgumentParser(description="Index Mazda MX-5 service manual for Hermes MCP")
    ap.add_argument(
        "--manual-root",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "manual",
    )
    ap.add_argument(
        "--db",
        type=Path,
        default=Path(__file__).resolve().parent / "data" / "manual.db",
    )
    ap.add_argument("--rebuild", action="store_true")
    args = ap.parse_args()

    manual_root = args.manual_root.resolve()
    if not manual_root.is_dir():
        print(f"manual root not found: {manual_root}", file=sys.stderr)
        return 1

    args.db.parent.mkdir(parents=True, exist_ok=True)
    db = ManualDatabase(args.db)
    db.initialize()
    if args.rebuild:
        db.clear()

    index_html = manual_root / "index.html"
    if index_html.is_file():
        index_toc(db, index_html, manual_root)

    html_files = sorted(manual_root.rglob("*.html")) + sorted(manual_root.rglob("*.htm"))
    seen_paths: set[str] = set()
    count = 0
    for path in html_files:
        if path.name.startswith("."):
            continue
        rel = str(path.relative_to(manual_root))
        if rel in seen_paths:
            continue
        seen_paths.add(rel)
        try:
            page = parse_html_file(path, manual_root)
        except Exception as exc:
            print(f"skip {rel}: {exc}", file=sys.stderr)
            continue
        if not page or not page.content:
            continue
        db.insert_page(page)
        count += 1
        if count % 500 == 0:
            print(f"indexed {count} pages…", file=sys.stderr)
            db.commit()

    db.set_meta("manual_root", str(manual_root))
    db.set_meta("vehicle", "Mazda MX-5 ND (03/2018+)")
    db.commit()
    stats = db.stats()
    print(f"Done: {stats['pages']} pages, {stats['distinct_dtcs']} DTC codes → {args.db}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())