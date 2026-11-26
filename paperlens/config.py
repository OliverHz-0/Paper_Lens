"""Local configuration management for PaperLens (LLM API + optional proxy)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "papers"
CONFIG_PATH = Path.home() / ".paperlens" / "config.json"

DEFAULT_CONFIG: dict[str, Any] = {
    "llm_provider": "agy_cli",
    "llm_base_url": "https://api.openai.com/v1",
    "llm_api_key": "",
    "llm_model": "gemini-4-neon-high",
    "http_proxy": "",
    "beginner_mode_default": True,
    "auto_fetch_resources": True,
    "zotero_data_dir": str(Path.home() / "Zotero"),
    "zotero_mcp_command": "",
    "zotero_local_api_url": "http://127.0.0.1:23119/api/users/0",
    "ppt_master_dir": str(Path.home() / "ppt-master"),
}


def load_config() -> dict[str, Any]:
    cfg = dict(DEFAULT_CONFIG)
    if CONFIG_PATH.exists():
        try:
            saved = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            if isinstance(saved, dict):
                cfg.update(saved)
        except Exception:
            pass
    # Allow environment variable overrides
    if os.environ.get("PAPERLENS_API_KEY") and not cfg.get("llm_api_key"):
        cfg["llm_api_key"] = os.environ["PAPERLENS_API_KEY"]
    if os.environ.get("OPENAI_API_KEY") and not cfg.get("llm_api_key"):
        cfg["llm_api_key"] = os.environ["OPENAI_API_KEY"]
    if os.environ.get("PAPERLENS_BASE_URL"):
        cfg["llm_base_url"] = os.environ["PAPERLENS_BASE_URL"]
    if os.environ.get("PAPERLENS_MODEL"):
        cfg["llm_model"] = os.environ["PAPERLENS_MODEL"]
    if os.environ.get("HTTPS_PROXY") and not cfg.get("http_proxy"):
        cfg["http_proxy"] = os.environ["HTTPS_PROXY"]
    return cfg


def save_config(updates: dict[str, Any]) -> dict[str, Any]:
    cfg = load_config()
    for k, v in updates.items():
        if k in DEFAULT_CONFIG:
            # Don't overwrite stored key with masked placeholder
            if k == "llm_api_key" and isinstance(v, str) and v.startswith("••••"):
                continue
            cfg[k] = v
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
    return cfg


def get_public_config() -> dict[str, Any]:
    cfg = load_config()
    key = cfg.get("llm_api_key", "")
    masked = ""
    if key:
        masked = f"••••{key[-4:]}" if len(key) > 6 else "••••••"
    return {
        **cfg,
        "llm_api_key": masked,
        "has_api_key": bool(key),
    }
