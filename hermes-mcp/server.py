#!/usr/bin/env python3
"""
Hermes MCP server — Mazda MX-5 service manual + vehicle context for in-car local models.

Designed for Raspberry Pi: stdio transport, SQLite FTS5 (no embedding API).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Resource, TextContent, Tool

from manual_db import ManualDatabase
from vehicle_state import read_vehicle_state

DEFAULT_DB = Path(__file__).resolve().parent / "data" / "manual.db"
DEFAULT_MANUAL = Path(__file__).resolve().parent.parent / "manual"

server = Server("hermes")
_db: ManualDatabase | None = None


def db() -> ManualDatabase:
    global _db
    if _db is None:
        path = Path(os.environ.get("HERMES_MANUAL_DB", DEFAULT_DB))
        if not path.is_file():
            raise FileNotFoundError(
                f"Manual index not found at {path}. Run: python index_manual.py --rebuild"
            )
        _db = ManualDatabase(path)
        _db.initialize()
    return _db


HERMES_CONTEXT = """\
Hermes runs on a Mazda MX-5 ND with a Raspberry Pi shimmed into the CMU (Connectivity Master Unit) harness.
Use the service manual tools to ground answers in OEM procedures, DTC diagnostics, and wiring references.
Prefer lookup_dtc when the user or vehicle telemetry reports a fault code.
For live sensor/state questions, combine manual guidance with current vehicle readings when available.
"""


@server.list_resources()
async def list_resources() -> list[Resource]:
    database = db()
    stats = database.stats()
    return [
        Resource(
            uri="hermes://context",
            name="Hermes vehicle context",
            description="How Hermes relates to the CMU harness and this manual",
            mimeType="text/plain",
        ),
        Resource(
            uri="hermes://manual/stats",
            name="Manual index statistics",
            description="Page counts and manual metadata",
            mimeType="application/json",
        ),
    ]


@server.read_resource()
async def read_resource(uri: str) -> str:
    if uri == "hermes://context":
        return HERMES_CONTEXT
    if uri == "hermes://manual/stats":
        return json.dumps(db().stats(), indent=2)
    raise ValueError(f"Unknown resource: {uri}")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="search_manual",
            description=(
                "Full-text search the Mazda MX-5 ND service manual. "
                "Use for procedures, specs, wiring, components, symptoms. "
                "Returns titles, paths, and snippets."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search terms (e.g. 'CMU DTC CAN')"},
                    "limit": {"type": "integer", "default": 8, "minimum": 1, "maximum": 20},
                    "section": {
                        "type": "string",
                        "description": "Optional filter: srvc, engine, mission, srt",
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="get_manual_page",
            description=(
                "Load full text of a manual page by page_id (e.g. id0902n7345400) or relative path "
                "(e.g. esicont/srvc/html/id0902n7345400.html)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "page_id": {"type": "string"},
                    "path": {"type": "string"},
                },
            },
        ),
        Tool(
            name="lookup_dtc",
            description=(
                "Find manual pages for a diagnostic trouble code (e.g. U0100:00, B1234:2A). "
                "Use when vehicle telemetry or CMU reports a DTC."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "DTC code with optional suffix"},
                    "limit": {"type": "integer", "default": 10},
                },
                "required": ["code"],
            },
        ),
        Tool(
            name="list_manual_sections",
            description="List top-level manual sections (srvc, engine, mission, etc.) with page counts.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="get_vehicle_state",
            description=(
                "Read live vehicle telemetry from the Pi CMU harness (JSON file). "
                "Set HERMES_VEHICLE_STATE to the state file path. Returns null if unavailable."
            ),
            inputSchema={"type": "object", "properties": {}},
        ),
    ]


def _truncate(text: str, max_len: int = 12000) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 40] + "\n\n[… truncated for context window …]"


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    database = db()

    if name == "search_manual":
        hits = database.search(
            arguments["query"],
            limit=arguments.get("limit", 8),
            section=arguments.get("section"),
        )
        if not hits:
            return [TextContent(type="text", text="No matches. Try broader terms or a DTC lookup.")]
        lines = []
        for h in hits:
            lines.append(
                f"### {h['title']}\n"
                f"- page_id: `{h['page_id']}`\n"
                f"- path: `{h['path']}`\n"
                f"- section: {h['section']}/{h['subsystem']}\n"
                f"- snippet: {h['snippet']}\n"
            )
        return [TextContent(type="text", text="\n".join(lines))]

    if name == "get_manual_page":
        page = database.get_page(
            page_id=arguments.get("page_id"),
            path=arguments.get("path"),
        )
        if not page:
            return [TextContent(type="text", text="Page not found.")]
        links = "\n".join(f"- [{t}]({h})" for t, h in page["links"][:20])
        body = (
            f"# {page['title']}\n\n"
            f"page_id: `{page['page_id']}`  \n"
            f"path: `{page['path']}`  \n"
            f"section: {page['section']}/{page['subsystem']}\n\n"
            f"{_truncate(page['content'])}\n\n"
        )
        if links:
            body += f"## Related links\n{links}\n"
        if page["dtc_codes"]:
            body += f"\n## DTC codes on this page\n{', '.join(page['dtc_codes'])}\n"
        manual_root = Path(os.environ.get("HERMES_MANUAL_ROOT", DEFAULT_MANUAL))
        body += f"\n_(HTML source: {manual_root / page['path']})_\n"
        return [TextContent(type="text", text=body)]

    if name == "lookup_dtc":
        hits = database.lookup_dtc(arguments["code"], limit=arguments.get("limit", 10))
        if not hits:
            return [
                TextContent(
                    type="text",
                    text=f"No manual pages indexed for DTC {arguments['code']}. Try search_manual.",
                )
            ]
        lines = [f"## DTC {arguments['code'].upper()}\n"]
        for h in hits:
            lines.append(
                f"### {h['title']}\n"
                f"- page_id: `{h['page_id']}`\n"
                f"- path: `{h['path']}`\n"
                f"- excerpt: {h['excerpt']}…\n"
            )
        return [TextContent(type="text", text="\n".join(lines))]

    if name == "list_manual_sections":
        sections = database.list_sections()
        text = "\n".join(f"- **{s['section']}**: {s['pages']} pages" for s in sections)
        return [TextContent(type="text", text=f"## Manual sections\n{text}\n")]

    if name == "get_vehicle_state":
        state = read_vehicle_state()
        if state is None:
            return [
                TextContent(
                    type="text",
                    text="No vehicle state (set HERMES_VEHICLE_STATE to a JSON file from the harness).",
                )
            ]
        dtcs = state.get("dtcs") or []
        hint = ""
        if dtcs:
            hint = f"\n\nActive DTCs: {', '.join(dtcs)} — use lookup_dtc for each."
        return [TextContent(type="text", text=json.dumps(state, indent=2) + hint)]

    raise ValueError(f"Unknown tool: {name}")


async def main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())