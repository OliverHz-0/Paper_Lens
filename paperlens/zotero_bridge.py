"""Zotero Bridge: connects to Local Zotero SQLite/Storage, Zotero 7 Local API, and Zotero MCP Server."""

from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import sqlite3
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import httpx

from .config import load_config


def _get_zotero_dir() -> Path:
    cfg = load_config()
    raw = (cfg.get("zotero_data_dir") or "").strip()
    return Path(raw).expanduser() if raw else (Path.home() / "Zotero")


def _detect_mcp_command() -> str:
    """Check user config, PATH, or Claude/Antigravity MCP configs for an installed zotero-mcp server."""
    cfg = load_config()
    if (cfg.get("zotero_mcp_command") or "").strip():
        return cfg["zotero_mcp_command"].strip()

    if shutil.which("zotero-mcp"):
        return "zotero-mcp"

    # Check common MCP JSON config locations for a zotero server entry (read-only)
    candidates = [
        Path.home() / ".gemini" / "antigravity" / "mcp_config.json",
        Path.home() / ".claude" / "settings.json",
        Path.home() / ".claude.json",
    ]
    for p in candidates:
        if not p.exists():
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            servers = data.get("mcpServers") or {}
            for name, scfg in servers.items():
                if "zotero" in name.lower() and isinstance(scfg, dict) and scfg.get("command"):
                    cmd = scfg["command"]
                    args = scfg.get("args") or []
                    return " ".join([cmd] + [str(a) for a in args])
        except Exception:
            continue
    return ""


def probe_zotero_local_api() -> bool:
    cfg = load_config()
    base = (cfg.get("zotero_local_api_url") or "http://127.0.0.1:23119/api/users/0").rstrip("/")
    try:
        with httpx.Client(timeout=1.5) as client:
            r = client.get(f"{base}/collections", params={"limit": 1})
            return r.status_code == 200
    except Exception:
        return False


def probe_zotero_mcp(command_str: str | None = None) -> dict[str, Any]:
    """Perform a standard MCP JSON-RPC 2.0 stdio handshake (`initialize` + `tools/list`) with Zotero MCP."""
    cmd_str = (command_str or _detect_mcp_command()).strip()
    if not cmd_str:
        return {
            "connected": False,
            "command": "",
            "tools": [],
            "message": "未检测到外部 zotero-mcp 进程（已自动启用本机 Zotero SQLite 直连；如需连接 Zotero MCP，可在下方填入启动命令如 `uvx zotero-mcp` 或 `zotero-mcp`）。",
        }
    try:
        argv = shlex.split(cmd_str)
        init_req = json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "PaperLens", "version": "0.1.0"},
                },
            }
        )
        list_req = json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        stdin_payload = f"{init_req}\n{list_req}\n"
        proc = subprocess.run(
            argv,
            input=stdin_payload,
            capture_output=True,
            text=True,
            timeout=6,
            env={**os.environ, "ZOTERO_LOCAL": "true"},
        )
        tools: list[str] = []
        server_info = None
        for line in proc.stdout.splitlines():
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                msg = json.loads(line)
                if msg.get("id") == 1 and "result" in msg:
                    server_info = msg["result"].get("serverInfo")
                if msg.get("id") == 2 and "result" in msg:
                    tools = [t.get("name") for t in msg["result"].get("tools", []) if t.get("name")]
            except Exception:
                continue
        if server_info or tools:
            return {
                "connected": True,
                "command": cmd_str,
                "server_info": server_info,
                "tools": tools,
                "message": f"已通过 MCP 协议连接 Zotero MCP（发现 {len(tools)} 个工具）",
            }
        return {
            "connected": False,
            "command": cmd_str,
            "tools": [],
            "message": f"MCP 启动未返回有效握手：{proc.stderr[:180] or '无响应'}",
        }
    except Exception as exc:
        return {
            "connected": False,
            "command": cmd_str,
            "tools": [],
            "message": f"Zotero MCP 连接失败：{exc}",
        }


def get_zotero_status() -> dict[str, Any]:
    zdir = _get_zotero_dir()
    db_path = zdir / "zotero.sqlite"
    storage_dir = zdir / "storage"
    mcp_cmd = _detect_mcp_command()
    local_api = probe_zotero_local_api()

    return {
        "local_sqlite_available": db_path.exists(),
        "zotero_data_dir": str(zdir),
        "storage_available": storage_dir.exists(),
        "local_api_available": local_api,
        "mcp_configured": bool(mcp_cmd),
        "mcp_command": mcp_cmd,
    }


def _resolve_attachment_path(zdir: Path, item_key: str, raw_path: str | None) -> Path | None:
    if not raw_path:
        return None
    if raw_path.startswith("storage:"):
        fname = raw_path.split("storage:", 1)[1]
        p = zdir / "storage" / item_key / fname
        if p.exists():
            return p
        # Fallback: pick first PDF inside that storage key dir
        folder = zdir / "storage" / item_key
        if folder.exists():
            pdfs = sorted(folder.glob("*.pdf"))
            if pdfs:
                return pdfs[0]
        return None
    # Linked absolute file path
    p = Path(raw_path).expanduser()
    return p if p.exists() else None


def read_zotero_library() -> dict[str, Any]:
    """Safely read Zotero collections and all items with local PDF attachments via a temp snapshot."""
    zdir = _get_zotero_dir()
    db_path = zdir / "zotero.sqlite"
    if not db_path.exists():
        return {
            "available": False,
            "error": f"未在 {zdir} 找到 zotero.sqlite，请在设置中确认 Zotero 数据目录。",
            "collections": [],
            "items": [],
        }

    with tempfile.TemporaryDirectory(prefix="paperlens_zotero_") as td:
        td_path = Path(td)
        for fn in ("zotero.sqlite", "zotero.sqlite-wal", "zotero.sqlite-shm"):
            src = zdir / fn
            if src.exists():
                shutil.copy2(src, td_path / fn)

        con = sqlite3.connect(str(td_path / "zotero.sqlite"))
        con.row_factory = sqlite3.Row
        cur = con.cursor()

        # 1. Collections
        raw_cols = cur.execute(
            "SELECT collectionID, collectionName, parentCollectionID FROM collections ORDER BY collectionName"
        ).fetchall()
        collections_map: dict[int, dict[str, Any]] = {}
        for row in raw_cols:
            cid = int(row["collectionID"])
            collections_map[cid] = {
                "id": cid,
                "name": row["collectionName"],
                "parent_id": row["parentCollectionID"],
                "pdf_count": 0,
            }

        # 2. Item -> Collection mapping
        item_cols: dict[int, list[int]] = {}
        for row in cur.execute("SELECT collectionID, itemID FROM collectionItems"):
            item_cols.setdefault(int(row["itemID"]), []).append(int(row["collectionID"]))

        # 3. Deleted items to ignore
        deleted_ids = {int(r["itemID"]) for r in cur.execute("SELECT itemID FROM deletedItems")}

        # 4. Metadata fields (title, date, DOI, publicationTitle)
        field_rows = cur.execute(
            """
            SELECT id.itemID, f.fieldName, iv.value
            FROM itemData id
            JOIN fields f ON id.fieldID = f.fieldID
            JOIN itemDataValues iv ON id.valueID = iv.valueID
            WHERE f.fieldName IN ('title', 'date', 'DOI', 'publicationTitle')
            """
        ).fetchall()
        item_meta: dict[int, dict[str, str]] = {}
        for r in field_rows:
            item_meta.setdefault(int(r["itemID"]), {})[r["fieldName"]] = r["value"]

        # 5. Creators (authors)
        creator_rows = cur.execute(
            """
            SELECT ic.itemID, c.firstName, c.lastName
            FROM itemCreators ic
            JOIN creators c ON ic.creatorID = c.creatorID
            ORDER BY ic.itemID, ic.orderIndex
            """
        ).fetchall()
        item_authors: dict[int, list[str]] = {}
        for r in creator_rows:
            name = " ".join(x for x in (r["firstName"], r["lastName"]) if x).strip()
            if name:
                item_authors.setdefault(int(r["itemID"]), []).append(name)

        # 6. All PDF attachments
        att_rows = cur.execute(
            """
            SELECT ia.itemID AS att_id, ia.parentItemID AS parent_id, ia.path AS raw_path,
                   i.key AS att_key, i.dateAdded AS date_added
            FROM itemAttachments ia
            JOIN items i ON ia.itemID = i.itemID
            WHERE ia.contentType = 'application/pdf'
            ORDER BY i.dateAdded DESC
            """
        ).fetchall()
        con.close()

    items_out: list[dict[str, Any]] = []
    seen_paths: set[str] = set()

    for r in att_rows:
        att_id = int(r["att_id"])
        parent_id = int(r["parent_id"]) if r["parent_id"] is not None else att_id
        if att_id in deleted_ids or parent_id in deleted_ids:
            continue

        pdf_path = _resolve_attachment_path(zdir, r["att_key"], r["raw_path"])
        if not pdf_path or not pdf_path.exists():
            continue
        resolved_str = str(pdf_path.resolve())
        if resolved_str in seen_paths:
            continue
        seen_paths.add(resolved_str)

        meta = item_meta.get(parent_id) or item_meta.get(att_id) or {}
        authors = item_authors.get(parent_id, [])
        date_str = meta.get("date", "")
        year_m = re.search(r"\b(19\d{2}|20\d{2})\b", date_str)
        year = int(year_m.group(1)) if year_m else None

        fname = pdf_path.name
        is_translated = any(tok in fname for tok in ("译文", "双语", "doc2x", "_zh_"))
        col_ids = sorted(set(item_cols.get(parent_id, []) + item_cols.get(att_id, [])))
        for cid in col_ids:
            if cid in collections_map:
                collections_map[cid]["pdf_count"] += 1

        items_out.append(
            {
                "attachment_key": r["att_key"],
                "attachment_id": att_id,
                "parent_id": parent_id,
                "title": meta.get("title") or pdf_path.stem,
                "filename": fname,
                "pdf_path": resolved_str,
                "size_mb": round(pdf_path.stat().st_size / (1024 * 1024), 2),
                "authors": ", ".join(authors[:4]) + (" et al." if len(authors) > 4 else ""),
                "year": year,
                "journal": meta.get("publicationTitle", ""),
                "doi": meta.get("DOI", ""),
                "collection_ids": col_ids,
                "collection_names": [
                    collections_map[cid]["name"] for cid in col_ids if cid in collections_map
                ],
                "is_translated_copy": is_translated,
                "date_added": r["date_added"],
            }
        )

    return {
        "available": True,
        "zotero_data_dir": str(zdir),
        "collections": list(collections_map.values()),
        "items": items_out,
        "total_pdfs": len(items_out),
    }


def lookup_zotero_pdf(attachment_key: str) -> dict[str, Any] | None:
    lib = read_zotero_library()
    for it in lib.get("items", []):
        if it["attachment_key"] == attachment_key:
            return it
    return None
