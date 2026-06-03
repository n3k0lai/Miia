"""Extract searchable text and metadata from Mazda ESI service manual HTML."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from html import unescape
from pathlib import Path

from bs4 import BeautifulSoup, NavigableString, Tag

DTC_CODE_RE = re.compile(r"[UBPC][0-9A-F]{4}:[0-9A-F]{2}", re.IGNORECASE)
DTC_SLASH_RE = re.compile(r"[UBPC][0-9A-F]{4}(?::[0-9A-F]{2})?(?:/[UBPC][0-9A-F]{4}(?::[0-9A-F]{2})?)+", re.IGNORECASE)


def extract_dtc_codes(text: str) -> list[str]:
    found: set[str] = set()
    for m in DTC_SLASH_RE.finditer(text):
        for part in m.group(0).split("/"):
            if ":" in part:
                found.add(part.upper())
    for m in DTC_CODE_RE.finditer(text):
        found.add(m.group(0).upper())
    return sorted(found)
PAGE_ID_RE = re.compile(r"^id[0-9a-z]+$", re.IGNORECASE)


@dataclass
class ManualPage:
    path: str
    page_id: str
    title: str
    section: str
    subsystem: str
    content: str
    dtc_codes: list[str] = field(default_factory=list)
    links: list[tuple[str, str]] = field(default_factory=list)


def _section_from_path(rel_path: str) -> tuple[str, str]:
    parts = Path(rel_path).parts
    if "esicont" in parts:
        idx = parts.index("esicont")
        if idx + 1 < len(parts):
            section = parts[idx + 1]
            subsystem = parts[idx + 2] if idx + 2 < len(parts) else ""
            return section, subsystem
    if "srt_root" in parts:
        return "srt", "repair_times"
    return "other", ""


def _block_label(tag: Tag) -> str | None:
    classes = tag.get("class") or []
    for cls in classes:
        if cls.startswith("attention"):
            return cls.replace("-label", "").replace("attention", "").strip() or "attention"
        if cls in ("servinfo-title", "servinfosub-title"):
            return None
    parent = tag.find_parent(class_=re.compile(r"attention\d"))
    if parent:
        label = parent.find(class_=re.compile(r"attention\d-label"))
        if label:
            return label.get_text(" ", strip=True)
    return None


def _text_from_node(node: Tag | NavigableString, depth: int = 0) -> str:
    if isinstance(node, NavigableString):
        return unescape(str(node))
    if not isinstance(node, Tag):
        return ""
    if node.name in ("script", "style", "meta", "link"):
        return ""
    if node.name == "img":
        cap = node.find_parent("table")
        if cap:
            caption = cap.find(class_="figure-caption")
            if caption:
                return f"[figure: {caption.get_text(strip=True)}]"
        return ""

    label = _block_label(node)
    parts: list[str] = []
    for child in node.children:
        parts.append(_text_from_node(child, depth + 1))
    text = "".join(parts)
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return ""
    if label:
        return f"\n[{label.upper()}] {text}\n"
    if node.name in ("p", "div", "dd", "li", "tr", "h1", "h2", "h3", "h4"):
        return f"\n{text}\n"
    return text


def parse_html_file(path: Path, manual_root: Path) -> ManualPage | None:
    raw = path.read_text(encoding="utf-8", errors="replace")
    soup = BeautifulSoup(raw, "lxml")
    body = soup.body or soup

    title_el = body.find(class_="servinfo-title")
    title = title_el.get_text(" ", strip=True) if title_el else ""
    if not title:
        title_tag = soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else path.stem

    page_id = ""
    id_el = body.find(class_="servinfo-title-id")
    if id_el:
        page_id = id_el.get_text(strip=True)
    anchor = body.find("a", attrs={"name": PAGE_ID_RE})
    if anchor and anchor.get("name"):
        page_id = page_id or anchor["name"]

    if not page_id:
        stem = path.stem
        page_id = stem if PAGE_ID_RE.match(stem) else stem

    rel = str(path.relative_to(manual_root))
    section, subsystem = _section_from_path(rel)

    links: list[tuple[str, str]] = []
    for a in body.find_all("a", href=True):
        href = a["href"]
        if href.startswith("#") or href.startswith("javascript"):
            continue
        label = a.get_text(" ", strip=True)
        if label:
            links.append((label, href))

    content = _text_from_node(body)
    content = re.sub(r"\n{3,}", "\n\n", content).strip()
    dtc_codes = extract_dtc_codes(content + " " + title)

    return ManualPage(
        path=rel,
        page_id=page_id,
        title=title,
        section=section,
        subsystem=subsystem,
        content=content,
        dtc_codes=dtc_codes,
        links=links[:50],
    )