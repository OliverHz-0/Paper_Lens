"""Zero-dependency multithreaded HTTP server for PaperLens Web Reader, Topics, Zotero Bridge & PPT Studio."""

from __future__ import annotations

import json
import mimetypes
import re
import threading
import time
import traceback
import uuid
from email.parser import BytesParser
from email.policy import default as email_default_policy
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from .config import DATA_DIR, PROJECT_ROOT, get_public_config, load_config, save_config
from .comparator import (
    compute_deterministic_comparison,
    delete_comparison,
    export_comparison_markdown,
    list_comparisons,
    load_comparison,
    run_deep_comparison,
)
from .exporter import export_markdown
from .llm_analyzer import build_structural_fallback, find_agy_binary, run_llm_deep_analysis, test_llm_connection
from .pdf_parser import ingest_pdf
from .ppt_master_bridge import (
    get_ppt_master_pptx_bytes,
    get_ppt_master_status,
    launch_ppt_master_svg_editor,
    load_ppt_master_link,
    recompile_existing_svgs,
    run_ppt_master_from_wizard,
    sync_and_build_ppt_master,
)
from .ppt_studio import export_pptx_bytes, generate_deck, get_ppt_presets, load_deck, save_deck
from .ref_tracer import trace_reference
from .resource_fetcher import fetch_all_resources
from .topics import (
    assign_paper,
    create_topic,
    delete_topic,
    list_topics,
    move_paper_topic,
    remove_paper,
    set_paper_topics,
    update_topic,
)
from .zotero_bridge import (
    get_zotero_status,
    lookup_zotero_pdf,
    probe_zotero_mcp,
    read_zotero_library,
)

WEB_DIR = PROJECT_ROOT / "web"

JOBS: dict[str, dict[str, Any]] = {}
JOBS_LOCK = threading.Lock()


def _set_job(job_id: str, **updates: Any) -> None:
    with JOBS_LOCK:
        job = JOBS.setdefault(job_id, {"id": job_id, "created_at": time.time()})
        job.update(updates)


def _slugify(name: str) -> str:
    base = re.sub(r"\.pdf$", "", name, flags=re.I)
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", base).strip("-").lower()
    if not slug:
        slug = f"paper-{int(time.time())}"
    if (DATA_DIR / slug).exists():
        slug = f"{slug}-{uuid.uuid4().hex[:5]}"
    return slug[:60]


def _list_papers() -> list[dict[str, Any]]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    items: list[dict[str, Any]] = []
    for pdir in sorted(DATA_DIR.iterdir()):
        manifest_path = pdir / "manifest.json"
        if not pdir.is_dir() or not manifest_path.exists():
            continue
        try:
            m = json.loads(manifest_path.read_text(encoding="utf-8"))
            a = {}
            if (pdir / "analysis.json").exists():
                a = json.loads((pdir / "analysis.json").read_text(encoding="utf-8"))
            items.append(
                {
                    "paper_id": m.get("paper_id", pdir.name),
                    "title": m.get("title", pdir.name),
                    "title_zh": a.get("paper_title_zh") or m.get("title", pdir.name),
                    "authors": m.get("authors", ""),
                    "doi": m.get("doi"),
                    "page_count": m.get("page_count", 0),
                    "slice_count": m.get("slice_count", 0),
                    "figure_count": m.get("figure_count", 0),
                    "reference_count": m.get("reference_count", 0),
                    "analysis_mode": a.get("mode", "none"),
                    "has_ppt": (pdir / "deck.json").exists(),
                }
            )
        except Exception:
            continue
    return items


def _load_paper_bundle(paper_id: str) -> dict[str, Any] | None:
    pdir = DATA_DIR / paper_id
    if not (pdir / "manifest.json").exists():
        return None
    manifest = json.loads((pdir / "manifest.json").read_text(encoding="utf-8"))
    analysis = (
        json.loads((pdir / "analysis.json").read_text(encoding="utf-8"))
        if (pdir / "analysis.json").exists()
        else build_structural_fallback(pdir)
    )
    resources = (
        json.loads((pdir / "resources.json").read_text(encoding="utf-8"))
        if (pdir / "resources.json").exists()
        else {}
    )
    ref_cache = (
        json.loads((pdir / "ref_cache.json").read_text(encoding="utf-8"))
        if (pdir / "ref_cache.json").exists()
        else {}
    )
    deck = load_deck(pdir)
    ppt_master = load_ppt_master_link(pdir)
    return {
        "manifest": manifest,
        "analysis": analysis,
        "resources": resources,
        "ref_cache": ref_cache,
        "deck": deck,
        "ppt_master": ppt_master,
    }


def _parse_multipart_pdf(content_type: str, body: bytes) -> tuple[str, bytes, bool, str | None]:
    header = f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode("utf-8")
    msg = BytesParser(policy=email_default_policy).parsebytes(header + body)
    filename = "uploaded.pdf"
    file_bytes = b""
    run_llm = True
    topic_id = None
    for part in msg.iter_parts():
        cd = part.get("Content-Disposition", "")
        name_m = re.search(r'name="([^"]+)"', cd)
        fname_m = re.search(r'filename="([^"]+)"', cd)
        field = name_m.group(1) if name_m else ""
        if field == "file" or fname_m:
            if fname_m:
                filename = Path(fname_m.group(1)).name
            file_bytes = part.get_payload(decode=True) or b""
        elif field == "run_llm":
            val = (part.get_payload(decode=True) or b"").decode("utf-8", errors="ignore").strip().lower()
            run_llm = val not in ("false", "0", "no")
        elif field == "topic_id":
            val = (part.get_payload(decode=True) or b"").decode("utf-8", errors="ignore").strip()
            if val and val not in ("all", "uncategorized"):
                topic_id = val
    return filename, file_bytes, run_llm, topic_id


def _has_configured_llm() -> bool:
    cfg = load_config()
    if (cfg.get("llm_provider") or "agy_cli") == "agy_cli":
        return bool(find_agy_binary())
    return bool((cfg.get("llm_api_key") or "").strip()) or (
        "localhost" in (cfg.get("llm_base_url") or "") or "127.0.0.1" in (cfg.get("llm_base_url") or "")
    )


def _run_ingest_job(
    job_id: str,
    paper_id: str,
    pdf_bytes: bytes,
    run_llm: bool,
    topic_id: str | None = None,
) -> None:
    try:
        pdir = DATA_DIR / paper_id
        pdir.mkdir(parents=True, exist_ok=True)
        pdf_path = pdir / "source.pdf"
        pdf_path.write_bytes(pdf_bytes)

        _set_job(job_id, status="running", progress=15, message="正在解析 PDF 双栏版面、切分段落与自动裁剪高清图表...")
        ingest_pdf(pdf_path, pdir, paper_id)

        if topic_id:
            try:
                assign_paper(topic_id, paper_id)
            except Exception:
                pass

        _set_job(job_id, status="running", progress=45, message="正在自动抓取论文关联的 GitHub 仓库、DOI 与补充材料 (SI)...")
        fetch_all_resources(pdir, force=True)

        if run_llm and _has_configured_llm():
            run_llm_deep_analysis(
                pdir,
                progress_cb=lambda pct, msg: _set_job(
                    job_id, status="running", progress=min(98, 45 + int(pct * 0.53)), message=msg
                ),
            )
        else:
            _set_job(job_id, status="running", progress=85, message="正在生成零 Key 快速结构化视图（配置 API Key 后可随时升级为 AI 深度解读）...")
            build_structural_fallback(pdir)

        _set_job(
            job_id,
            status="done",
            progress=100,
            paper_id=paper_id,
            topic_id=topic_id,
            message="解析完成！正在打开交互式论文解读器...",
        )
    except Exception as exc:
        traceback.print_exc()
        _set_job(job_id, status="error", progress=100, message=f"解析失败：{exc}")


def _run_zotero_import_job(
    job_id: str,
    attachment_keys: list[str],
    target_topic_id: str | None,
    auto_create_topic: bool,
    run_llm: bool,
) -> None:
    try:
        total = max(1, len(attachment_keys))
        imported_ids: list[str] = []
        last_topic_id = target_topic_id

        for idx, akey in enumerate(attachment_keys, start=1):
            base_pct = int(((idx - 1) / total) * 100)
            _set_job(
                job_id,
                status="running",
                progress=max(5, base_pct),
                message=f"[{idx}/{total}] 正在从 Zotero 读取文献附件 ({akey})...",
            )
            entry = lookup_zotero_pdf(akey)
            if not entry:
                continue
            pdf_path = Path(entry["pdf_path"])
            if not pdf_path.exists():
                continue

            paper_id = _slugify(entry.get("title") or pdf_path.stem)
            pdir = DATA_DIR / paper_id
            pdir.mkdir(parents=True, exist_ok=True)

            _set_job(
                job_id,
                status="running",
                progress=min(95, base_pct + int(25 / total)),
                message=f"[{idx}/{total}] 正在切图与解析版面：{entry['title'][:40]}...",
            )
            ingest_pdf(pdf_path, pdir, paper_id)

            # Determine target topic
            tid = target_topic_id
            if not tid and auto_create_topic and entry.get("collection_names"):
                col_name = entry["collection_names"][0]
                col_id = entry["collection_ids"][0] if entry.get("collection_ids") else None
                t = create_topic(
                    name=col_name,
                    description=f"从 Zotero 分类「{col_name}」同步导入的课题",
                    zotero_collection_id=col_id,
                )
                tid = t["id"]
                last_topic_id = tid
            if tid:
                try:
                    assign_paper(tid, paper_id)
                except Exception:
                    pass

            _set_job(
                job_id,
                status="running",
                progress=min(96, base_pct + int(55 / total)),
                message=f"[{idx}/{total}] 正在自动抓取 GitHub/SI 与外部资源...",
            )
            fetch_all_resources(pdir, force=False)

            if run_llm and _has_configured_llm():
                run_llm_deep_analysis(pdir)
            else:
                build_structural_fallback(pdir)

            imported_ids.append(paper_id)

        if not imported_ids:
            _set_job(job_id, status="error", progress=100, message="未能导入任何有效 PDF，请确认所选 Zotero 条目存在本地 PDF。")
            return

        _set_job(
            job_id,
            status="done",
            progress=100,
            paper_id=imported_ids[0],
            imported_ids=imported_ids,
            topic_id=last_topic_id,
            message=f"成功从 Zotero 导入并解析 {len(imported_ids)} 篇文献！",
        )
    except Exception as exc:
        traceback.print_exc()
        _set_job(job_id, status="error", progress=100, message=f"Zotero 导入失败：{exc}")


def _run_analyze_job(job_id: str, paper_id: str) -> None:
    try:
        pdir = DATA_DIR / paper_id
        run_llm_deep_analysis(
            pdir,
            progress_cb=lambda pct, msg: _set_job(job_id, status="running", progress=pct, message=msg),
        )
        _set_job(job_id, status="done", progress=100, paper_id=paper_id, message="AI 深度解读已完成！")
    except Exception as exc:
        traceback.print_exc()
        _set_job(job_id, status="error", progress=100, message=f"AI 解读失败：{exc}")


def _run_compare_job(
    job_id: str, paper_ids: list[str], topic_name: str, focus_question: str
) -> None:
    try:
        cmp_obj = run_deep_comparison(
            paper_ids,
            topic_name=topic_name,
            focus_question=focus_question,
            progress_cb=lambda pct, msg: _set_job(job_id, status="running", progress=pct, message=msg),
        )
        _set_job(
            job_id,
            status="done",
            progress=100,
            comparison_id=cmp_obj["id"],
            message="多文深度对比与关联图谱已生成！",
        )
    except Exception as exc:
        traceback.print_exc()
        _set_job(job_id, status="error", progress=100, message=f"跨文对比失败：{exc}")


class PaperLensHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format: str, *args: Any) -> None:
        pass

    def _read_json_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length > 0 else b"{}"
        return json.loads(raw.decode("utf-8"))

    def _send_json(self, data: Any, status: int = 200) -> None:
        raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def _send_bytes(self, data: bytes, content_type: str, status: int = 200, filename: str | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        if filename:
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.end_headers()
        self.wfile.write(data)

    def _serve_file(self, path: Path) -> None:
        if not path.exists() or not path.is_file():
            self._send_json({"error": "Not found"}, status=404)
            return
        ctype, _ = mimetypes.guess_type(str(path))
        if path.suffix == ".js":
            ctype = "application/javascript; charset=utf-8"
        elif path.suffix == ".css":
            ctype = "text/css; charset=utf-8"
        elif path.suffix == ".html":
            ctype = "text/html; charset=utf-8"
        self._send_bytes(path.read_bytes(), ctype or "application/octet-stream")

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        qs = parse_qs(parsed.query)

        if path == "/api/health":
            self._send_json({"ok": True, "version": "0.2.0"})
            return

        if path == "/api/config":
            self._send_json(get_public_config())
            return

        if path == "/api/papers":
            self._send_json({"papers": _list_papers()})
            return

        if path == "/api/topics":
            self._send_json({"topics": list_topics()})
            return

        if path == "/api/zotero/status":
            self._send_json(get_zotero_status())
            return

        if path == "/api/zotero/library":
            self._send_json(read_zotero_library())
            return

        if path == "/api/ppt/presets":
            self._send_json(get_ppt_master_status())
            return

        if path == "/api/comparisons":
            self._send_json({"comparisons": list_comparisons()})
            return

        m_cmp_md = re.match(r"^/api/comparisons/([a-zA-Z0-9_-]+)/export-md$", path)
        if m_cmp_md:
            obj = load_comparison(m_cmp_md.group(1))
            if not obj:
                self._send_json({"error": "Comparison not found"}, status=404)
                return
            md = export_comparison_markdown(obj)
            self._send_bytes(md.encode("utf-8"), "text/markdown; charset=utf-8", filename=f"{obj['id']}.md")
            return

        m_cmp = re.match(r"^/api/comparisons/([a-zA-Z0-9_-]+)$", path)
        if m_cmp:
            obj = load_comparison(m_cmp.group(1))
            if not obj:
                self._send_json({"error": "Comparison not found"}, status=404)
                return
            self._send_json(obj)
            return

        m_job = re.match(r"^/api/jobs/([a-zA-Z0-9_-]+)$", path)
        if m_job:
            with JOBS_LOCK:
                job = JOBS.get(m_job.group(1))
            if not job:
                self._send_json({"error": "Job not found"}, status=404)
                return
            self._send_json(job)
            return

        m_paper = re.match(r"^/api/papers/([a-zA-Z0-9_-]+)$", path)
        if m_paper:
            bundle = _load_paper_bundle(m_paper.group(1))
            if not bundle:
                self._send_json({"error": "Paper not found"}, status=404)
                return
            self._send_json(bundle)
            return

        m_ppt_get = re.match(r"^/api/papers/([a-zA-Z0-9_-]+)/ppt$", path)
        if m_ppt_get:
            pdir = DATA_DIR / m_ppt_get.group(1)
            if not (pdir / "manifest.json").exists():
                self._send_json({"error": "Paper not found"}, status=404)
                return
            self._send_json({"deck": load_deck(pdir), "ppt_master": load_ppt_master_link(pdir)})
            return

        m_ppt_svg = re.match(r"^/api/papers/([a-zA-Z0-9_-]+)/ppt/svg/([a-zA-Z0-9_.-]+\.svg)$", path)
        if m_ppt_svg:
            pid, fname = m_ppt_svg.group(1), m_ppt_svg.group(2)
            pdir = DATA_DIR / pid
            link = load_ppt_master_link(pdir)
            if not link:
                self._send_json({"error": "No ppt-master project"}, status=404)
                return
            svg_path = (Path(link["project_path"]) / "svg_output" / fname).resolve()
            svg_root = (Path(link["project_path"]) / "svg_output").resolve()
            if not str(svg_path).startswith(str(svg_root)) or not svg_path.is_file():
                self._send_json({"error": "SVG not found"}, status=404)
                return
            svg_txt = svg_path.read_text(encoding="utf-8")
            # Rewrite relative ../images/ hrefs so browser renders embedded figures cleanly
            svg_txt = svg_txt.replace('href="../images/', f'href="/api/papers/{pid}/ppt/images/')
            self._send_bytes(svg_txt.encode("utf-8"), "image/svg+xml; charset=utf-8")
            return

        m_ppt_img = re.match(r"^/api/papers/([a-zA-Z0-9_-]+)/ppt/images/([a-zA-Z0-9_.-]+)$", path)
        if m_ppt_img:
            pid, fname = m_ppt_img.group(1), m_ppt_img.group(2)
            pdir = DATA_DIR / pid
            link = load_ppt_master_link(pdir)
            if not link:
                self._send_json({"error": "No ppt-master project"}, status=404)
                return
            img_path = (Path(link["project_path"]) / "images" / fname).resolve()
            img_root = (Path(link["project_path"]) / "images").resolve()
            if not str(img_path).startswith(str(img_root)) or not img_path.is_file():
                self._send_json({"error": "Image not found"}, status=404)
                return
            self._serve_file(img_path)
            return

        m_pptx = re.match(r"^/api/papers/([a-zA-Z0-9_-]+)/ppt/export-pptx$", path)
        if m_pptx:
            pid = m_pptx.group(1)
            pdir = DATA_DIR / pid
            if not (pdir / "manifest.json").exists():
                self._send_json({"error": "Paper not found"}, status=404)
                return
            try:
                try:
                    data, fname = get_ppt_master_pptx_bytes(pdir)
                except FileNotFoundError:
                    data = export_pptx_bytes(pdir)
                    fname = f"{pid}-seminar.pptx"
                self._send_bytes(
                    data,
                    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                    filename=fname,
                )
            except Exception as exc:
                self._send_json({"error": str(exc)}, status=400)
            return

        m_trace = re.match(r"^/api/papers/([a-zA-Z0-9_-]+)/trace-ref/(\d+)$", path)
        if m_trace:
            pid, rnum = m_trace.group(1), int(m_trace.group(2))
            force = qs.get("force", ["0"])[0] in ("1", "true", "yes")
            pdir = DATA_DIR / pid
            if not (pdir / "manifest.json").exists():
                self._send_json({"error": "Paper not found"}, status=404)
                return
            traced = trace_reference(pdir, rnum, force=force)
            self._send_json(traced)
            return

        m_export = re.match(r"^/api/papers/([a-zA-Z0-9_-]+)/export-md$", path)
        if m_export:
            pid = m_export.group(1)
            pdir = DATA_DIR / pid
            if not (pdir / "manifest.json").exists():
                self._send_json({"error": "Paper not found"}, status=404)
                return
            md = export_markdown(pdir)
            self._send_bytes(md.encode("utf-8"), "text/markdown; charset=utf-8", filename=f"{pid}-deep-dive.md")
            return

        m_asset = re.match(r"^/papers/([a-zA-Z0-9_-]+)/(assets/.+|source\.pdf)$", path)
        if m_asset:
            pid, rel = m_asset.group(1), m_asset.group(2)
            target = (DATA_DIR / pid / rel).resolve()
            root = (DATA_DIR / pid).resolve()
            if not str(target).startswith(str(root)):
                self._send_json({"error": "Forbidden"}, status=403)
                return
            self._serve_file(target)
            return

        if path in ("/", "/index.html"):
            self._serve_file(WEB_DIR / "index.html")
            return
        candidate = (WEB_DIR / path.lstrip("/")).resolve()
        if str(candidate).startswith(str(WEB_DIR.resolve())) and candidate.is_file():
            self._serve_file(candidate)
            return

        self._send_json({"error": "Not found"}, status=404)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = unquote(parsed.path)

        if path == "/api/upload":
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length) if length > 0 else b""
            ctype = self.headers.get("Content-Type", "")
            if "multipart/form-data" not in ctype:
                self._send_json({"error": "Expected multipart/form-data"}, status=400)
                return
            filename, file_bytes, run_llm, topic_id = _parse_multipart_pdf(ctype, body)
            if not file_bytes or not file_bytes[:5].startswith(b"%PDF"):
                self._send_json({"error": "请上传有效的 PDF 论文文件"}, status=400)
                return
            paper_id = _slugify(filename)
            job_id = uuid.uuid4().hex[:12]
            _set_job(job_id, status="queued", progress=5, paper_id=paper_id, message="已接收 PDF，准备启动解析管线...")
            threading.Thread(
                target=_run_ingest_job,
                args=(job_id, paper_id, file_bytes, run_llm, topic_id),
                daemon=True,
            ).start()
            self._send_json({"job_id": job_id, "paper_id": paper_id}, status=HTTPStatus.ACCEPTED)
            return

        try:
            payload = self._read_json_body()
        except Exception as exc:
            self._send_json({"error": f"Invalid JSON: {exc}"}, status=400)
            return

        if path == "/api/config":
            save_config(payload)
            self._send_json(get_public_config())
            return

        if path == "/api/llm/test":
            res = test_llm_connection(payload)
            self._send_json(res)
            return

        if path == "/api/comparisons/quick":
            try:
                pids = payload.get("paper_ids") or []
                det = compute_deterministic_comparison(pids)
                self._send_json({"mode": "quick", "deterministic": det, "synthesis": None})
            except Exception as exc:
                self._send_json({"error": str(exc)}, status=400)
            return

        if path == "/api/comparisons/analyze":
            pids = payload.get("paper_ids") or []
            if not isinstance(pids, list) or len(pids) < 2:
                self._send_json({"error": "请至少选择 2 篇论文进行对比分析"}, status=400)
                return
            job_id = uuid.uuid4().hex[:12]
            _set_job(job_id, status="queued", progress=5, message=f"准备对 {len(pids)} 篇论文启动跨文深度对比...")
            threading.Thread(
                target=_run_compare_job,
                args=(
                    job_id,
                    pids,
                    str(payload.get("topic_name") or ""),
                    str(payload.get("focus_question") or ""),
                ),
                daemon=True,
            ).start()
            self._send_json({"job_id": job_id}, status=HTTPStatus.ACCEPTED)
            return

        if path == "/api/topics":
            try:
                t = create_topic(
                    name=payload.get("name", ""),
                    description=payload.get("description", ""),
                    color=payload.get("color", "blue"),
                    zotero_collection_id=payload.get("zotero_collection_id"),
                )
                self._send_json({"topic": t, "topics": list_topics()}, status=201)
            except Exception as exc:
                self._send_json({"error": str(exc)}, status=400)
            return

        if path == "/api/topics/move-paper":
            try:
                topics = move_paper_topic(
                    paper_id=payload.get("paper_id", ""),
                    target_topic_id=payload.get("target_topic_id", ""),
                    source_topic_id=payload.get("source_topic_id"),
                    copy=bool(payload.get("copy", False)),
                )
                self._send_json({"topics": topics})
            except Exception as exc:
                self._send_json({"error": str(exc)}, status=400)
            return

        m_topic_assign = re.match(r"^/api/topics/([^/]+)/papers$", path)
        if m_topic_assign:
            try:
                t = assign_paper(m_topic_assign.group(1), payload.get("paper_id", ""))
                self._send_json({"topic": t, "topics": list_topics()})
            except Exception as exc:
                self._send_json({"error": str(exc)}, status=400)
            return

        if path == "/api/zotero/mcp-probe":
            res = probe_zotero_mcp(payload.get("command"))
            self._send_json(res)
            return

        if path == "/api/zotero/import":
            keys = payload.get("attachment_keys") or []
            if not isinstance(keys, list) or not keys:
                self._send_json({"error": "请至少勾选一篇 Zotero 文献进行导入"}, status=400)
                return
            job_id = uuid.uuid4().hex[:12]
            _set_job(job_id, status="queued", progress=3, message=f"准备从 Zotero 导入 {len(keys)} 篇 PDF...")
            threading.Thread(
                target=_run_zotero_import_job,
                args=(
                    job_id,
                    keys,
                    payload.get("target_topic_id"),
                    bool(payload.get("auto_create_topic", True)),
                    bool(payload.get("run_llm", False)),
                ),
                daemon=True,
            ).start()
            self._send_json({"job_id": job_id}, status=HTTPStatus.ACCEPTED)
            return

        m_ppt_gen = re.match(r"^/api/papers/([a-zA-Z0-9_-]+)/ppt/generate$", path)
        if m_ppt_gen:
            pid = m_ppt_gen.group(1)
            pdir = DATA_DIR / pid
            if not (pdir / "manifest.json").exists():
                self._send_json({"error": "Paper not found"}, status=404)
                return
            try:
                status = get_ppt_master_status()
                if status.get("installed"):
                    result = run_ppt_master_from_wizard(pdir, payload)
                    self._send_json(result)
                else:
                    deck = generate_deck(pdir, payload)
                    self._send_json({"deck": deck, "ppt_master": None})
            except Exception as exc:
                traceback.print_exc()
                self._send_json({"error": str(exc)}, status=500)
            return

        m_ppt_recomp = re.match(r"^/api/papers/([a-zA-Z0-9_-]+)/ppt/recompile$", path)
        if m_ppt_recomp:
            pid = m_ppt_recomp.group(1)
            pdir = DATA_DIR / pid
            try:
                pm = recompile_existing_svgs(pdir)
                self._send_json({"ppt_master": pm})
            except Exception as exc:
                traceback.print_exc()
                self._send_json({"error": str(exc)}, status=500)
            return

        m_ppt_ed = re.match(r"^/api/papers/([a-zA-Z0-9_-]+)/ppt/launch-editor$", path)
        if m_ppt_ed:
            pid = m_ppt_ed.group(1)
            pdir = DATA_DIR / pid
            try:
                info = launch_ppt_master_svg_editor(pdir)
                self._send_json(info)
            except Exception as exc:
                traceback.print_exc()
                self._send_json({"error": str(exc)}, status=500)
            return

        m_fetch = re.match(r"^/api/papers/([a-zA-Z0-9_-]+)/fetch-resources$", path)
        if m_fetch:
            pid = m_fetch.group(1)
            pdir = DATA_DIR / pid
            if not (pdir / "manifest.json").exists():
                self._send_json({"error": "Paper not found"}, status=404)
                return
            res = fetch_all_resources(pdir, force=True)
            self._send_json(res)
            return

        m_analyze = re.match(r"^/api/papers/([a-zA-Z0-9_-]+)/analyze$", path)
        if m_analyze:
            pid = m_analyze.group(1)
            pdir = DATA_DIR / pid
            if not (pdir / "manifest.json").exists():
                self._send_json({"error": "Paper not found"}, status=404)
                return
            job_id = uuid.uuid4().hex[:12]
            _set_job(job_id, status="queued", progress=10, paper_id=pid, message="正在启动大模型深度解剖...")
            threading.Thread(target=_run_analyze_job, args=(job_id, pid), daemon=True).start()
            self._send_json({"job_id": job_id, "paper_id": pid}, status=HTTPStatus.ACCEPTED)
            return

        self._send_json({"error": "Not found"}, status=404)

    def do_PUT(self) -> None:
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        try:
            payload = self._read_json_body()
        except Exception as exc:
            self._send_json({"error": f"Invalid JSON: {exc}"}, status=400)
            return

        m_paper_topics = re.match(r"^/api/papers/([a-zA-Z0-9_-]+)/topics$", path)
        if m_paper_topics:
            try:
                topics = set_paper_topics(m_paper_topics.group(1), payload.get("topic_ids") or [])
                self._send_json({"topics": topics})
            except Exception as exc:
                self._send_json({"error": str(exc)}, status=400)
            return

        m_topic = re.match(r"^/api/topics/([^/]+)$", path)
        if m_topic:
            try:
                t = update_topic(m_topic.group(1), payload)
                self._send_json({"topic": t, "topics": list_topics()})
            except Exception as exc:
                self._send_json({"error": str(exc)}, status=400)
            return

        m_ppt_save = re.match(r"^/api/papers/([a-zA-Z0-9_-]+)/ppt$", path)
        if m_ppt_save:
            pdir = DATA_DIR / m_ppt_save.group(1)
            if not (pdir / "manifest.json").exists():
                self._send_json({"error": "Paper not found"}, status=404)
                return
            deck = save_deck(pdir, payload)
            pm = None
            if get_ppt_master_status().get("installed") and load_ppt_master_link(pdir):
                try:
                    pm = sync_and_build_ppt_master(pdir, deck, reinit=False)
                except Exception:
                    traceback.print_exc()
            self._send_json({"deck": load_deck(pdir), "ppt_master": pm})
            return

        self._send_json({"error": "Not found"}, status=404)

    def do_DELETE(self) -> None:
        parsed = urlparse(self.path)
        path = unquote(parsed.path)

        m_topic_paper = re.match(r"^/api/topics/([^/]+)/papers/([^/]+)$", path)
        if m_topic_paper:
            try:
                t = remove_paper(m_topic_paper.group(1), m_topic_paper.group(2))
                self._send_json({"topic": t, "topics": list_topics()})
            except Exception as exc:
                self._send_json({"error": str(exc)}, status=400)
            return

        m_cmp_del = re.match(r"^/api/comparisons/([a-zA-Z0-9_-]+)$", path)
        if m_cmp_del:
            delete_comparison(m_cmp_del.group(1))
            self._send_json({"comparisons": list_comparisons()})
            return

        m_topic = re.match(r"^/api/topics/([^/]+)$", path)
        if m_topic:
            delete_topic(m_topic.group(1))
            self._send_json({"topics": list_topics()})
            return

        self._send_json({"error": "Not found"}, status=404)


def run_server(host: str = "127.0.0.1", port: int = 8765) -> None:
    server = ThreadingHTTPServer((host, port), PaperLensHandler)
    print(f"PaperLens server running at http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down PaperLens server.")
        server.server_close()
