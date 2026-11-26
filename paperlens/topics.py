"""Research Topics (课题管理) persistence for organizing papers by project/collection."""

from __future__ import annotations

import json
import re
import time
import uuid
from pathlib import Path
from typing import Any

from .config import DATA_DIR, PROJECT_ROOT

TOPICS_FILE = PROJECT_ROOT / "data" / "topics.json"

TOPIC_COLORS = ["teal", "blue", "amber", "purple", "emerald", "rose"]


def _slug(name: str) -> str:
    clean = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff_-]+", "-", name).strip("-")
    return f"topic-{uuid.uuid4().hex[:6]}" if not clean else f"{clean[:24]}-{uuid.uuid4().hex[:4]}"


def _load_store() -> dict[str, Any]:
    if TOPICS_FILE.exists():
        try:
            data = json.loads(TOPICS_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict) and isinstance(data.get("topics"), list):
                return data
        except Exception:
            pass

    # Seed initial topic containing the preloaded limits-2025 paper if present
    seed_papers = ["limits-2025"] if (DATA_DIR / "limits-2025" / "manifest.json").exists() else []
    initial = {
        "topics": [
            {
                "id": "topic-amp",
                "name": "抗菌肽与 AI 药物设计",
                "description": "宿主防御肽（HDP）、抗结核多肽与小样本机器学习挖掘相关文献",
                "color": "teal",
                "paper_ids": seed_papers,
                "zotero_collection_id": None,
                "created_at": int(time.time()),
            }
        ]
    }
    _save_store(initial)
    return initial


def _save_store(data: dict[str, Any]) -> None:
    TOPICS_FILE.parent.mkdir(parents=True, exist_ok=True)
    TOPICS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def list_topics() -> list[dict[str, Any]]:
    return _load_store()["topics"]


def create_topic(
    name: str,
    description: str = "",
    color: str = "blue",
    zotero_collection_id: int | None = None,
) -> dict[str, Any]:
    name = name.strip()
    if not name:
        raise ValueError("课题名称不能为空")
    store = _load_store()
    # If syncing from Zotero collection and already exists, return existing
    if zotero_collection_id is not None:
        for t in store["topics"]:
            if t.get("zotero_collection_id") == zotero_collection_id:
                return t
    if color not in TOPIC_COLORS:
        color = TOPIC_COLORS[len(store["topics"]) % len(TOPIC_COLORS)]
    topic = {
        "id": _slug(name),
        "name": name,
        "description": description.strip(),
        "color": color,
        "paper_ids": [],
        "zotero_collection_id": zotero_collection_id,
        "created_at": int(time.time()),
    }
    store["topics"].append(topic)
    _save_store(store)
    return topic


def update_topic(topic_id: str, updates: dict[str, Any]) -> dict[str, Any]:
    store = _load_store()
    for t in store["topics"]:
        if t["id"] == topic_id:
            if "name" in updates and str(updates["name"]).strip():
                t["name"] = str(updates["name"]).strip()
            if "description" in updates:
                t["description"] = str(updates["description"]).strip()
            if "color" in updates and updates["color"] in TOPIC_COLORS:
                t["color"] = updates["color"]
            _save_store(store)
            return t
    raise KeyError(f"Topic not found: {topic_id}")


def delete_topic(topic_id: str) -> None:
    store = _load_store()
    store["topics"] = [t for t in store["topics"] if t["id"] != topic_id]
    _save_store(store)


def assign_paper(topic_id: str, paper_id: str) -> dict[str, Any]:
    store = _load_store()
    for t in store["topics"]:
        if t["id"] == topic_id:
            if paper_id not in t["paper_ids"]:
                t["paper_ids"].append(paper_id)
            _save_store(store)
            return t
    raise KeyError(f"Topic not found: {topic_id}")


def remove_paper(topic_id: str, paper_id: str) -> dict[str, Any]:
    store = _load_store()
    for t in store["topics"]:
        if t["id"] == topic_id:
            t["paper_ids"] = [pid for pid in t["paper_ids"] if pid != paper_id]
            _save_store(store)
            return t
    raise KeyError(f"Topic not found: {topic_id}")


def set_paper_topics(paper_id: str, topic_ids: list[str]) -> list[dict[str, Any]]:
    """Atomically set the exact list of topic IDs a paper belongs to."""
    paper_id = str(paper_id or "").strip()
    if not paper_id:
        raise ValueError("paper_id 不能为空")
    target_set = set(topic_ids or [])
    store = _load_store()
    for t in store["topics"]:
        pids = [pid for pid in t.get("paper_ids", []) if pid != paper_id]
        if t["id"] in target_set:
            pids.append(paper_id)
        t["paper_ids"] = pids
    _save_store(store)
    return store["topics"]


def move_paper_topic(
    paper_id: str,
    target_topic_id: str,
    source_topic_id: str | None = None,
    copy: bool = False,
) -> list[dict[str, Any]]:
    """Drag-and-drop move/assign helper.

    - target_topic_id == "uncategorized": removes the paper from all topics.
    - Otherwise adds paper to target_topic_id; if source_topic_id is a real topic
      different from target_topic_id and copy is False, also removes it from source.
    """
    paper_id = str(paper_id or "").strip()
    target_topic_id = str(target_topic_id or "").strip()
    if not paper_id:
        raise ValueError("paper_id 不能为空")
    store = _load_store()

    if target_topic_id == "uncategorized":
        for t in store["topics"]:
            t["paper_ids"] = [pid for pid in t.get("paper_ids", []) if pid != paper_id]
        _save_store(store)
        return store["topics"]

    found_target = None
    for t in store["topics"]:
        if t["id"] == target_topic_id:
            found_target = t
            break
    if not found_target:
        raise KeyError(f"Topic not found: {target_topic_id}")

    if paper_id not in found_target["paper_ids"]:
        found_target["paper_ids"].append(paper_id)

    if (
        not copy
        and source_topic_id
        and source_topic_id not in ("all", "uncategorized", target_topic_id)
    ):
        for t in store["topics"]:
            if t["id"] == source_topic_id:
                t["paper_ids"] = [pid for pid in t.get("paper_ids", []) if pid != paper_id]
                break

    _save_store(store)
    return store["topics"]
