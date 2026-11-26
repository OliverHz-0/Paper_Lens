"""Native integration with the local `ppt-master` toolchain (e.g. ~/ppt-master).

Executes the official ppt-master Quick Generate pipeline end-to-end:
  1. project_manager.py init <project_name> --quick-generate
  2. Export PaperLens deep analysis into sources/ + copy crisp paper figures into images/
  3. Author canonical 1280x720 flat semantic SVGs under svg_output/ + notes/total.md
  4. total_md_split.py <project_path>
  5. svg_quality_checker.py <project_path> --quick-generate --canonical-authoring --stage final --json
  6. svg_to_pptx.py <project_path> --quick-generate --with-notes [-t <transition>] [-a <animation>]
  7. Optional live launch of ppt-master's own `scripts/svg_editor/server.py --live --daemon --no-browser`
"""

from __future__ import annotations

import datetime as _dt
import html
import json
import re
import shutil
import socket
import subprocess
import time
from pathlib import Path
from typing import Any

from PIL import Image

from .config import load_config
from .exporter import export_markdown
from .ppt_studio import (
    AUDIENCE_PROFILES,
    FOCUS_OPTIONS,
    STYLE_TEMPLATES,
    generate_deck,
    load_deck,
    save_deck,
)

# Color palettes mapped to official ppt-master styles (fallback to clean academic palettes)
STYLE_PALETTES: dict[str, dict[str, str]] = {
    "academic-research": {
        "bg": "#FFFFFF",
        "surface": "#F4F6FA",
        "primary": "#1E3A8A",
        "accent": "#0F766E",
        "text": "#181C24",
        "muted": "#526074",
        "callout_bg": "#EFF6FF",
        "cover_bg": "#0F2447",
        "cover_text": "#FFFFFF",
        "cover_sub": "#CBD5E1",
        "zh_name": "学术研究 (academic-research)",
        "tag": "论文答辩 / 学术组会首推",
    },
    "science-explainer": {
        "bg": "#FAF8F4",
        "surface": "#F1ECE3",
        "primary": "#0F5C63",
        "accent": "#E4572E",
        "text": "#1E2A2F",
        "muted": "#5B6B70",
        "callout_bg": "#FEF3C7",
        "cover_bg": "#0F5C63",
        "cover_text": "#FFFFFF",
        "cover_sub": "#D7ECEE",
        "zh_name": "科学科普 (science-explainer)",
        "tag": "零基础 / 跨学科听众首推",
    },
    "technical-deepdive": {
        "bg": "#F8FAFC",
        "surface": "#EBF1F8",
        "primary": "#0F172A",
        "accent": "#0284C7",
        "text": "#0F172A",
        "muted": "#475569",
        "callout_bg": "#E0F2FE",
        "cover_bg": "#0B1120",
        "cover_text": "#F8FAFC",
        "cover_sub": "#94A3B8",
        "zh_name": "技术深潜 (technical-deepdive)",
        "tag": "AI 算法 / 机制深度剖析",
    },
    "mbb-consulting": {
        "bg": "#FFFFFF",
        "surface": "#F3F5F8",
        "primary": "#003A70",
        "accent": "#008272",
        "text": "#1A1F2C",
        "muted": "#5A6577",
        "callout_bg": "#E6F4F1",
        "cover_bg": "#002B54",
        "cover_text": "#FFFFFF",
        "cover_sub": "#BFD7EA",
        "zh_name": "MBB 咨询结论先行 (mbb-consulting)",
        "tag": "结构化证据链 / 高密度汇报",
    },
    "narrative-keynote": {
        "bg": "#111622",
        "surface": "#1B2335",
        "primary": "#60A5FA",
        "accent": "#2DD4BF",
        "text": "#F1F5F9",
        "muted": "#94A3B8",
        "callout_bg": "#1E293B",
        "cover_bg": "#090D16",
        "cover_text": "#F8FAFC",
        "cover_sub": "#CBD5E1",
        "zh_name": "暗夜演讲 Keynote (narrative-keynote)",
        "tag": "大屏演讲 / 会议报告厅",
    },
    "workshop-teaching": {
        "bg": "#FBFCFA",
        "surface": "#EDF5F0",
        "primary": "#065F46",
        "accent": "#D97706",
        "text": "#182620",
        "muted": "#4B6358",
        "callout_bg": "#FEF3C7",
        "cover_bg": "#064E3B",
        "cover_text": "#ECFDF5",
        "cover_sub": "#A7F3D0",
        "zh_name": "教学工作坊 (workshop-teaching)",
        "tag": "循序渐进 / 课题组新人培训",
    },
    "consulting-decision": {
        "bg": "#FFFFFF",
        "surface": "#F4F5F7",
        "primary": "#1F2937",
        "accent": "#2563EB",
        "text": "#111827",
        "muted": "#6B7280",
        "callout_bg": "#EFF6FF",
        "cover_bg": "#111827",
        "cover_text": "#FFFFFF",
        "cover_sub": "#D1D5DB",
        "zh_name": "决策分析 (consulting-decision)",
        "tag": "利弊权衡 / 方案对比",
    },
}

TRANSITION_OPTIONS = [
    {"id": "fade", "label": "淡入淡出 (fade · 推荐)"},
    {"id": "morph", "label": "平滑变形 (morph)"},
    {"id": "push", "label": "推进切换 (push)"},
    {"id": "wipe", "label": "擦除 (wipe)"},
    {"id": "none", "label": "无切换 (none)"},
]

ANIMATION_OPTIONS = [
    {"id": "none", "label": "静态无动画 (none · 组会推荐)"},
    {"id": "fade", "label": "柔和渐显 (fade)"},
    {"id": "entrance_rise_up", "label": "上浮出现 (entrance_rise_up)"},
]

# Track launched svg_editor servers per project path
_EDITOR_PORTS: dict[str, int] = {}


def get_ppt_master_paths() -> dict[str, Path]:
    cfg = load_config()
    root = Path((cfg.get("ppt_master_dir") or str(Path.home() / "ppt-master"))).expanduser()
    skill_dir = root / "skills" / "ppt-master"
    scripts_dir = skill_dir / "scripts"
    venv_py = root / ".venv" / "bin" / "python3"
    py_exe = venv_py if venv_py.exists() else Path("python3")
    return {
        "root": root,
        "skill_dir": skill_dir,
        "scripts_dir": scripts_dir,
        "templates_dir": skill_dir / "templates",
        "projects_dir": root / "projects",
        "python": py_exe,
    }


def get_ppt_master_status() -> dict[str, Any]:
    paths = get_ppt_master_paths()
    root = paths["root"]
    scripts = paths["scripts_dir"]
    ok = (
        root.exists()
        and (scripts / "project_manager.py").exists()
        and (scripts / "svg_to_pptx.py").exists()
        and (scripts / "svg_quality_checker.py").exists()
    )

    # Read official styles_index.json from ppt-master
    styles: list[dict[str, Any]] = []
    styles_idx = paths["templates_dir"] / "styles" / "styles_index.json"
    if styles_idx.exists():
        try:
            raw = json.loads(styles_idx.read_text(encoding="utf-8"))
            # Order academic/science/technical styles first
            priority = [
                "academic-research",
                "science-explainer",
                "technical-deepdive",
                "mbb-consulting",
                "narrative-keynote",
                "workshop-teaching",
                "consulting-decision",
            ]
            ordered_keys = [k for k in priority if k in raw] + [k for k in raw if k not in priority]
            for k in ordered_keys:
                info = raw[k]
                pal = STYLE_PALETTES.get(k, STYLE_PALETTES["academic-research"])
                styles.append(
                    {
                        "id": k,
                        "name": pal.get("zh_name", k),
                        "tag": pal.get("tag", ", ".join((info.get("keywords") or [])[:2])),
                        "desc": info.get("summary", ""),
                        "bg": pal["bg"],
                        "surface": pal["surface"],
                        "primary": pal["primary"],
                        "accent": pal["accent"],
                        "text": pal["text"],
                        "muted": pal["muted"],
                        "callout_bg": pal["callout_bg"],
                        "cover_bg": pal["cover_bg"],
                        "cover_text": pal["cover_text"],
                    }
                )
        except Exception:
            pass

    if not styles:
        styles = list(STYLE_TEMPLATES.values())

    brands: list[str] = []
    brands_dir = paths["templates_dir"] / "brands"
    if brands_dir.exists():
        brands = sorted(p.name for p in brands_dir.iterdir() if p.is_dir())

    return {
        "installed": ok,
        "ppt_master_dir": str(root),
        "python": str(paths["python"]),
        "styles": styles,
        "brands": brands,
        "audiences": list(AUDIENCE_PROFILES.values()),
        "focus_options": FOCUS_OPTIONS,
        "transitions": TRANSITION_OPTIONS,
        "animations": ANIMATION_OPTIONS,
    }


def _link_file(paper_dir: Path) -> Path:
    return paper_dir / "ppt_master_link.json"


def load_ppt_master_link(paper_dir: Path) -> dict[str, Any] | None:
    p = _link_file(paper_dir)
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        # Attach live svg list & latest pptx
        proj = Path(data.get("project_path", ""))
        if proj.exists():
            svgs = sorted((proj / "svg_output").glob("*.svg"))
            data["svg_files"] = [f.name for f in svgs]
            exports_dir = proj / "exports"
            if exports_dir.exists():
                pptxs = sorted(exports_dir.glob("*.pptx"), key=lambda f: f.stat().st_mtime, reverse=True)
                data["latest_pptx"] = str(pptxs[0]) if pptxs else None
                data["latest_pptx_name"] = pptxs[0].name if pptxs else None
            qrep = proj / "validation" / "svg_quality_report.json"
            if qrep.exists():
                try:
                    qr = json.loads(qrep.read_text(encoding="utf-8"))
                    data["quality_summary"] = {
                        "passed": qr.get("passed", True),
                        "errors": qr.get("total_errors", qr.get("errors", 0)),
                        "warnings": qr.get("total_warnings", qr.get("warnings", 0)),
                    }
                except Exception:
                    pass
            if str(proj) in _EDITOR_PORTS:
                data["svg_editor_url"] = f"http://127.0.0.1:{_EDITOR_PORTS[str(proj)]}"
        return data
    except Exception:
        return None


def _save_link(paper_dir: Path, data: dict[str, Any]) -> dict[str, Any]:
    data["updated_at"] = int(time.time())
    _link_file(paper_dir).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return load_ppt_master_link(paper_dir) or data


def _wrap_cjk_lines(text: str, max_units: float) -> list[str]:
    """Wrap mixed Chinese/English string cleanly by display width units (CJK=1.0, ASCII=0.56)."""
    text = re.sub(r"\s+", " ", (text or "").strip())
    if not text:
        return []
    lines: list[str] = []
    cur = ""
    units = 0.0
    for ch in text:
        w = 1.0 if ord(ch) > 127 else 0.56
        if units + w > max_units and cur:
            lines.append(cur.rstrip())
            cur = ch if ch != " " else ""
            units = w if ch != " " else 0.0
        else:
            cur += ch
            units += w
    if cur.strip():
        lines.append(cur.rstrip())
    return lines


def _svg_text_multiline(
    x: float,
    y: float,
    lines: list[str],
    font_size: int,
    line_height: float,
    fill: str,
    bold: bool = False,
    anchor: str | None = None,
) -> str:
    if not lines:
        return ""
    attrs = [f'x="{x:.1f}"', f'y="{y:.1f}"', f'font-size="{font_size}"', f'fill="{fill}"']
    if bold:
        attrs.append('font-weight="bold"')
    if anchor:
        attrs.append(f'text-anchor="{anchor}"')
    parts = [html.escape(lines[0])]
    for ln in lines[1:]:
        parts.append(f'<tspan x="{x:.1f}" dy="{line_height:.1f}">{html.escape(ln)}</tspan>')
    return f'<text {" ".join(attrs)}>{"".join(parts)}</text>'


def _fit_image_rect(img_path: Path, box_x: float, box_y: float, box_w: float, box_h: float) -> tuple[float, float, float, float]:
    if not img_path.exists():
        return box_x, box_y, box_w, box_h
    with Image.open(img_path) as im:
        iw, ih = im.size
    if iw <= 0 or ih <= 0:
        return box_x, box_y, box_w, box_h
    scale = min(box_w / iw, box_h / ih)
    fw = iw * scale
    fh = ih * scale
    fx = box_x + (box_w - fw) / 2.0
    fy = box_y + (box_h - fh) / 2.0
    return fx, fy, fw, fh


def _render_slide_to_pptmaster_svg(
    slide: dict[str, Any],
    idx: int,
    total: int,
    style_id: str,
    project_path: Path,
    fig_map: dict[str, dict[str, Any]],
    footer_source: str,
) -> str:
    """Author a canonical 1280x720 flat semantic SVG passing ppt-master's --canonical-authoring checker."""
    pal = STYLE_PALETTES.get(style_id, STYLE_PALETTES["academic-research"])
    layout = slide.get("layout", "two_column")
    page_role = {
        "cover": "cover",
        "agenda": "toc",
        "takeaways": "ending",
    }.get(layout, "content")

    elems: list[str] = []
    if layout == "cover":
        elems.append(f'  <rect id="bg" data-pptx-role="background" x="0" y="0" width="1280" height="720" fill="{pal["cover_bg"]}"/>')
        elems.append(f'  <rect id="cover-bar" data-pptx-role="decoration" x="0" y="0" width="24" height="720" fill="{pal["accent"]}"/>')

        # Kicker badge
        tag_txt = (slide.get("tag") or "LITERATURE SEMINAR")[:44]
        elems.append('  <g id="cover-kicker" data-pptx-bounds="84 72 680 46">')
        elems.append(f'    <rect x="84" y="74" width="12" height="36" rx="4" fill="{pal["accent"]}"/>')
        elems.append(f'    <text x="112" y="100" font-size="22" font-weight="bold" fill="{pal["cover_sub"]}">{html.escape(tag_txt)}</text>')
        elems.append("  </g>")

        # Cover Title
        title_lines = _wrap_cjk_lines(slide.get("title") or "文献深度汇报", 22)[:3]
        elems.append('  <g id="cover-title" data-pptx-bounds="84 150 1110 210">')
        elems.append("    " + _svg_text_multiline(84, 206, title_lines, 46, 62, pal["cover_text"], bold=True))
        elems.append("  </g>")

        # Subtitle
        sub_lines = _wrap_cjk_lines(slide.get("subtitle") or "", 46)[:2]
        if sub_lines:
            elems.append('  <g id="cover-subtitle" data-pptx-bounds="84 374 1110 78">')
            elems.append("    " + _svg_text_multiline(84, 404, sub_lines, 24, 34, pal["cover_sub"]))
            elems.append("  </g>")

        # Meta bullets
        meta_lines: list[str] = []
        for b in (slide.get("bullets") or [])[:3]:
            meta_lines.extend(_wrap_cjk_lines(f"▸ {b}", 48)[:2])
        if meta_lines:
            elems.append('  <g id="cover-meta" data-pptx-bounds="84 476 1110 190">')
            elems.append(f'    <line x1="84" y1="478" x2="1194" y2="478" stroke="{pal["accent"]}" stroke-width="2" opacity="0.6"/>')
            elems.append("    " + _svg_text_multiline(84, 514, meta_lines[:5], 20, 32, pal["cover_sub"]))
            elems.append("  </g>")
    else:
        elems.append(f'  <rect id="bg" data-pptx-role="background" x="0" y="0" width="1280" height="720" fill="{pal["bg"]}"/>')
        elems.append(f'  <rect id="top-bar" data-pptx-role="decoration" x="0" y="0" width="1280" height="10" fill="{pal["primary"]}"/>')

        # Header block
        tag_txt = (slide.get("tag") or f"SLIDE {idx:02d}")[:42]
        title_lines = _wrap_cjk_lines(slide.get("title") or "", 34)[:2]
        sub_lines = _wrap_cjk_lines(slide.get("subtitle") or "", 58)[:1]
        header_h = 128 if len(title_lines) == 1 else 160
        elems.append(f'  <g id="header" data-pptx-bounds="56 26 1168 {header_h}">')
        elems.append(f'    <text x="56" y="48" font-size="16" font-weight="bold" fill="{pal["accent"]}">{html.escape(tag_txt)}</text>')
        elems.append("    " + _svg_text_multiline(56, 86, title_lines, 30, 38, pal["primary"], bold=True))
        sub_y = 86 + (len(title_lines) - 1) * 38 + 30
        if sub_lines:
            elems.append("    " + _svg_text_multiline(56, sub_y, sub_lines, 18, 24, pal["muted"]))
        sep_y = 26 + header_h - 4
        elems.append(f'    <line x1="56" y1="{sep_y}" x2="1224" y2="{sep_y}" stroke="{pal["surface"]}" stroke-width="2"/>')
        elems.append("  </g>")

        body_top = 26 + header_h + 12

        # Optional KPI strip
        metrics = (slide.get("metrics") or [])[:4]
        if metrics:
            n_m = len(metrics)
            gap = 18
            card_w = (1168 - gap * (n_m - 1)) / n_m
            kpi_h = 82
            for mi, m in enumerate(metrics):
                cx = 56 + mi * (card_w + gap)
                elems.append(f'  <g id="kpi-{mi+1}" data-pptx-bounds="{cx:.0f} {body_top:.0f} {card_w:.0f} {kpi_h}">')
                elems.append(f'    <rect x="{cx:.1f}" y="{body_top:.1f}" width="{card_w:.1f}" height="{kpi_h}" rx="10" fill="{pal["surface"]}" stroke="{pal["accent"]}" stroke-width="1.5"/>')
                elems.append(f'    <text x="{cx + card_w/2:.1f}" y="{body_top + 38:.1f}" font-size="28" font-weight="bold" fill="{pal["accent"]}" text-anchor="middle">{html.escape(m.get("value", ""))}</text>')
                elems.append(f'    <text x="{cx + card_w/2:.1f}" y="{body_top + 66:.1f}" font-size="15" fill="{pal["muted"]}" text-anchor="middle">{html.escape(m.get("label", "")[:24])}</text>')
                elems.append("  </g>")
            body_top += kpi_h + 14

        callout_txt = (slide.get("callout") or "").strip()
        callout_h = 74 if callout_txt else 0
        footer_top = 674
        body_bottom = footer_top - (callout_h + 14 if callout_h else 10)
        body_h = max(180, body_bottom - body_top)

        # Figure check
        fig_id = slide.get("figure_id")
        fig_info = fig_map.get(fig_id) if fig_id else None
        fig_file = (project_path / "images" / f"{fig_id}.png") if fig_info else None
        has_fig = bool(fig_file and fig_file.exists())

        bullets = slide.get("bullets") or []

        if has_fig and fig_file is not None and fig_info is not None:
            # Left card: bullets (540px wide); Right card: fitted crisp figure (606px wide)
            left_w = 542
            right_x = 56 + left_w + 20
            right_w = 1224 - right_x

            elems.append(f'  <g id="bullets-panel" data-pptx-bounds="56 {body_top:.0f} {left_w} {body_h:.0f}">')
            elems.append(f'    <rect x="56" y="{body_top:.1f}" width="{left_w}" height="{body_h:.1f}" rx="12" fill="{pal["surface"]}"/>')
            cur_y = body_top + 34
            max_y = body_top + body_h - 14
            for b in bullets[:5]:
                wrapped = _wrap_cjk_lines(f"▸ {b}", 24.5)[:3]
                if cur_y + (len(wrapped) - 1) * 26 > max_y:
                    break
                elems.append("    " + _svg_text_multiline(78, cur_y, wrapped, 18, 26, pal["text"]))
                cur_y += len(wrapped) * 26 + 14
            elems.append("  </g>")

            elems.append(f'  <g id="figure-panel" data-pptx-bounds="{right_x:.0f} {body_top:.0f} {right_w:.0f} {body_h:.0f}">')
            elems.append(f'    <rect x="{right_x:.1f}" y="{body_top:.1f}" width="{right_w:.1f}" height="{body_h:.1f}" rx="12" fill="#FFFFFF" stroke="{pal["surface"]}" stroke-width="2"/>')
            fx, fy, fw, fh = _fit_image_rect(fig_file, right_x + 14, body_top + 12, right_w - 28, body_h - 46)
            elems.append(f'    <image href="../images/{fig_file.name}" x="{fx:.1f}" y="{fy:.1f}" width="{fw:.1f}" height="{fh:.1f}" preserveAspectRatio="xMidYMid meet"/>')
            cap_label = f"{fig_info['label']} (Page {fig_info['page']})"
            elems.append(f'    <text x="{right_x + right_w/2:.1f}" y="{body_top + body_h - 12:.1f}" font-size="14" fill="{pal["muted"]}" text-anchor="middle">{html.escape(cap_label)}</text>')
            elems.append("  </g>")
        elif layout == "two_column" and len(bullets) >= 4:
            mid = (len(bullets) + 1) // 2
            col_w = 572
            for ci, col_bullets in enumerate((bullets[:mid], bullets[mid:])):
                cx = 56 + ci * (col_w + 24)
                elems.append(f'  <g id="col-{ci+1}" data-pptx-bounds="{cx} {body_top:.0f} {col_w} {body_h:.0f}">')
                elems.append(f'    <rect x="{cx}" y="{body_top:.1f}" width="{col_w}" height="{body_h:.1f}" rx="12" fill="{pal["surface"]}"/>')
                cur_y = body_top + 38
                max_y = body_top + body_h - 16
                for b in col_bullets[:4]:
                    wrapped = _wrap_cjk_lines(f"▸ {b}", 25.5)[:3]
                    if cur_y + (len(wrapped) - 1) * 28 > max_y:
                        break
                    elems.append("    " + _svg_text_multiline(cx + 22, cur_y, wrapped, 19, 28, pal["text"]))
                    cur_y += len(wrapped) * 28 + 16
                elems.append("  </g>")
        else:
            elems.append(f'  <g id="main-panel" data-pptx-bounds="56 {body_top:.0f} 1168 {body_h:.0f}">')
            elems.append(f'    <rect x="56" y="{body_top:.1f}" width="1168" height="{body_h:.1f}" rx="12" fill="{pal["surface"]}"/>')
            cur_y = body_top + 42
            max_y = body_top + body_h - 16
            for b in bullets[:6]:
                wrapped = _wrap_cjk_lines(f"▸ {b}", 53)[:2]
                if cur_y + (len(wrapped) - 1) * 30 > max_y:
                    break
                elems.append("    " + _svg_text_multiline(84, cur_y, wrapped, 20, 30, pal["text"]))
                cur_y += len(wrapped) * 30 + 16
            elems.append("  </g>")

        # Bottom Callout Banner
        if callout_h > 0:
            cy = footer_top - callout_h - 8
            clines = _wrap_cjk_lines(callout_txt, 58)[:2]
            elems.append(f'  <g id="callout" data-pptx-bounds="56 {cy:.0f} 1168 {callout_h}">')
            elems.append(f'    <rect x="56" y="{cy:.1f}" width="1168" height="{callout_h}" rx="10" fill="{pal["callout_bg"]}"/>')
            elems.append(f'    <rect x="56" y="{cy:.1f}" width="8" height="{callout_h}" rx="4" fill="{pal["accent"]}"/>')
            ty = cy + (42 if len(clines) == 1 else 30)
            elems.append("    " + _svg_text_multiline(82, ty, clines, 17, 25, pal["text"]))
            elems.append("  </g>")

        # Footer
        elems.append(f'  <g id="footer" data-pptx-role="footer" data-pptx-bounds="56 {footer_top} 1168 30">')
        elems.append(f'    <text x="56" y="{footer_top + 22}" font-size="14" fill="{pal["muted"]}">{html.escape(footer_source[:72])}</text>')
        elems.append(f'    <text x="1224" y="{footer_top + 22}" font-size="14" font-weight="bold" fill="{pal["muted"]}" text-anchor="end">{idx:02d} / {total:02d}</text>')
        elems.append("  </g>")

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" lang="zh-CN" '
        f'data-pptx-page-role="{page_role}" font-family="Microsoft YaHei, Arial, sans-serif">\n'
        + "\n".join(elems)
        + "\n</svg>\n"
    )


def _slide_filename(idx: int, slide: dict[str, Any]) -> str:
    layout = slide.get("layout", "content")
    slug = {
        "cover": "cover",
        "agenda": "agenda",
        "figure_focus": "figure",
        "two_column": "content",
        "takeaways": "takeaways",
    }.get(layout, "slide")
    return f"{idx:02d}_{slug}.svg"


def _run_cmd(argv: list[str], cwd: Path, timeout: int = 90) -> tuple[int, str, str]:
    proc = subprocess.run(
        argv,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return proc.returncode, proc.stdout, proc.stderr


def sync_and_build_ppt_master(
    paper_dir: Path,
    deck: dict[str, Any],
    reinit: bool = False,
) -> dict[str, Any]:
    """Write canonical SVGs + notes into the official ppt-master project, run quality checker & svg_to_pptx.py."""
    paths = get_ppt_master_paths()
    if not paths["scripts_dir"].exists():
        raise RuntimeError(f"未找到本机 ppt-master 目录：{paths['root']}")

    manifest = json.loads((paper_dir / "manifest.json").read_text(encoding="utf-8"))
    paper_id = manifest.get("paper_id", paper_dir.name)
    fig_map = {f["id"]: f for f in manifest.get("figures", [])}

    existing_link = load_ppt_master_link(paper_dir)
    project_path: Path | None = None
    if existing_link and not reinit:
        cand = Path(existing_link.get("project_path", ""))
        if cand.exists() and (cand / "svg_output").exists():
            project_path = cand

    steps_log: list[dict[str, Any]] = []

    # Step 1: Initialize real ppt-master project via project_manager.py
    if project_path is None:
        today = _dt.date.today().strftime("%Y%m%d")
        base_name = re.sub(r"[^a-zA-Z0-9_-]+", "_", f"paperlens_{paper_id}")[:36]
        proj_slug = f"{base_name}_{today}"
        # Avoid collision if reinit
        candidate_dir = paths["projects_dir"] / proj_slug
        if candidate_dir.exists() and reinit:
            proj_slug = f"{base_name}_{today}_{int(time.time()) % 10000}"

        rc, out, err = _run_cmd(
            [
                str(paths["python"]),
                str(paths["scripts_dir"] / "project_manager.py"),
                "init",
                proj_slug,
                "--quick-generate",
            ],
            cwd=paths["root"],
        )
        steps_log.append({"step": "project_manager.py init", "rc": rc, "output": (out or err)[-500:]})
        # Resolve exact created project directory
        created = paths["projects_dir"] / proj_slug
        if not created.exists():
            # project_manager may append date suffix automatically
            matches = sorted(paths["projects_dir"].glob(f"{proj_slug}*"), key=lambda p: p.stat().st_mtime, reverse=True)
            created = matches[0] if matches else created
        project_path = created
        (project_path / "svg_output").mkdir(parents=True, exist_ok=True)
        (project_path / "images").mkdir(parents=True, exist_ok=True)
        (project_path / "notes").mkdir(parents=True, exist_ok=True)
        (project_path / "sources").mkdir(parents=True, exist_ok=True)

    # Step 2: Sync PaperLens sources + crisp paper figures into ppt-master project
    md_text = export_markdown(paper_dir)
    (project_path / "sources" / "paper_deep_analysis.md").write_text(md_text, encoding="utf-8")
    for f in manifest.get("figures", []):
        src_img = paper_dir / f["image"]
        if src_img.exists():
            shutil.copy2(src_img, project_path / "images" / f"{f['id']}.png")

    # Step 3: Write canonical 1280x720 SVGs into svg_output/ and notes/total.md
    svg_dir = project_path / "svg_output"
    for old_svg in svg_dir.glob("*.svg"):
        old_svg.unlink()

    slides = deck.get("slides") or []
    style_id = deck.get("style_id") or "academic-research"
    footer_source = f"PaperLens × PPT-Master · {manifest.get('doi') or manifest.get('title', '')[:45]}"

    notes_chunks: list[str] = []
    svg_filenames: list[str] = []
    for idx, s in enumerate(slides, start=1):
        fname = _slide_filename(idx, s)
        s["svg_filename"] = fname
        svg_filenames.append(fname)
        svg_code = _render_slide_to_pptmaster_svg(
            s, idx, len(slides), style_id, project_path, fig_map, footer_source
        )
        (svg_dir / fname).write_text(svg_code, encoding="utf-8")
        stem = fname[:-4]
        note_body = (s.get("speaker_notes") or f"本页讲解：{s.get('title', '')}").strip()
        notes_chunks.append(f"# {stem}\n\n{note_body}")

    save_deck(paper_dir, deck)

    notes_dir = project_path / "notes"
    notes_dir.mkdir(parents=True, exist_ok=True)
    for old_n in notes_dir.glob("*.md"):
        old_n.unlink()
    (notes_dir / "total.md").write_text("\n\n---\n\n".join(notes_chunks) + "\n", encoding="utf-8")

    # Step 4: Run official total_md_split.py
    rc_split, out_split, err_split = _run_cmd(
        [str(paths["python"]), str(paths["scripts_dir"] / "total_md_split.py"), str(project_path)],
        cwd=paths["root"],
    )
    steps_log.append({"step": "total_md_split.py", "rc": rc_split, "output": (out_split or err_split)[-400:]})

    # Step 5: Run official svg_quality_checker.py (--quick-generate --canonical-authoring --stage final --json)
    rc_chk, out_chk, err_chk = _run_cmd(
        [
            str(paths["python"]),
            str(paths["scripts_dir"] / "svg_quality_checker.py"),
            str(project_path),
            "--quick-generate",
            "--canonical-authoring",
            "--stage",
            "final",
            "--json",
        ],
        cwd=paths["root"],
    )
    steps_log.append({"step": "svg_quality_checker.py", "rc": rc_chk, "output": (out_chk or err_chk)[-800:]})

    # Step 6: Run official svg_to_pptx.py (--quick-generate --with-notes)
    transition = deck.get("transition") or "fade"
    animation = deck.get("animation") or "none"
    export_cmd = [
        str(paths["python"]),
        str(paths["scripts_dir"] / "svg_to_pptx.py"),
        str(project_path),
        "--quick-generate",
        "--with-notes",
        "-t",
        transition,
        "-a",
        animation,
    ]
    rc_exp, out_exp, err_exp = _run_cmd(export_cmd, cwd=paths["root"], timeout=120)
    steps_log.append({"step": "svg_to_pptx.py", "rc": rc_exp, "output": (out_exp or err_exp)[-800:]})

    link_data = _save_link(
        paper_dir,
        {
            "paper_id": paper_id,
            "project_path": str(project_path),
            "project_name": project_path.name,
            "style_id": style_id,
            "transition": transition,
            "animation": animation,
            "checker_rc": rc_chk,
            "export_rc": rc_exp,
            "steps_log": steps_log,
        },
    )
    return link_data


def run_ppt_master_from_wizard(paper_dir: Path, options: dict[str, Any]) -> dict[str, Any]:
    """Full end-to-end PPT-Master pipeline driven by the PaperLens precondition wizard."""
    deck = generate_deck(paper_dir, options)
    deck["style_id"] = options.get("style_id") or "academic-research"
    deck["transition"] = options.get("transition") or "fade"
    deck["animation"] = options.get("animation") or "none"
    deck["brand"] = options.get("brand") or ""
    deck["engine"] = "ppt-master"
    save_deck(paper_dir, deck)

    link = sync_and_build_ppt_master(paper_dir, deck, reinit=bool(options.get("reinit", False)))
    return {"deck": load_deck(paper_dir), "ppt_master": link}


def recompile_existing_svgs(paper_dir: Path) -> dict[str, Any]:
    """Re-run quality checker + svg_to_pptx.py directly on the current svg_output/ (e.g. after editing in ppt-master's SVG Editor)."""
    paths = get_ppt_master_paths()
    link = load_ppt_master_link(paper_dir)
    if not link:
        raise ValueError("尚未初始化 PPT-Master 工程")
    project_path = Path(link["project_path"])
    deck = load_deck(paper_dir) or {}

    rc_chk, out_chk, err_chk = _run_cmd(
        [
            str(paths["python"]),
            str(paths["scripts_dir"] / "svg_quality_checker.py"),
            str(project_path),
            "--quick-generate",
            "--canonical-authoring",
            "--stage",
            "final",
            "--json",
        ],
        cwd=paths["root"],
    )
    rc_exp, out_exp, err_exp = _run_cmd(
        [
            str(paths["python"]),
            str(paths["scripts_dir"] / "svg_to_pptx.py"),
            str(project_path),
            "--quick-generate",
            "--with-notes",
            "-t",
            deck.get("transition") or "fade",
            "-a",
            deck.get("animation") or "none",
        ],
        cwd=paths["root"],
        timeout=120,
    )
    link["checker_rc"] = rc_chk
    link["export_rc"] = rc_exp
    link["steps_log"] = [
        {"step": "svg_quality_checker.py", "rc": rc_chk, "output": (out_chk or err_chk)[-800:]},
        {"step": "svg_to_pptx.py", "rc": rc_exp, "output": (out_exp or err_exp)[-800:]},
    ]
    return _save_link(paper_dir, link)


def _find_free_port(start: int = 6060) -> int:
    for port in range(start, start + 60):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    return start


def launch_ppt_master_svg_editor(paper_dir: Path) -> dict[str, Any]:
    """Start ppt-master's official live SVG editor daemon for this paper's project and return its URL."""
    paths = get_ppt_master_paths()
    link = load_ppt_master_link(paper_dir)
    if not link:
        raise ValueError("尚未生成 PPT-Master 工程，请先完成前置条件生成。")
    project_path = Path(link["project_path"])
    key = str(project_path)

    # Reuse if port already alive
    if key in _EDITOR_PORTS:
        p = _EDITOR_PORTS[key]
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", p)) == 0:
                return {"url": f"http://127.0.0.1:{p}", "port": p, "project_path": key}

    port = _find_free_port(6060)
    rc, out, err = _run_cmd(
        [
            str(paths["python"]),
            str(paths["scripts_dir"] / "svg_editor" / "server.py"),
            str(project_path),
            "--live",
            "--daemon",
            "--no-browser",
            "--port",
            str(port),
        ],
        cwd=paths["root"],
        timeout=20,
    )
    if rc != 0:
        raise RuntimeError(f"启动 PPT-Master SVG 编辑器失败：{(err or out)[-300:]}")
    _EDITOR_PORTS[key] = port
    link["svg_editor_url"] = f"http://127.0.0.1:{port}"
    _save_link(paper_dir, link)
    return {"url": f"http://127.0.0.1:{port}", "port": port, "project_path": key}


def get_ppt_master_pptx_bytes(paper_dir: Path) -> tuple[bytes, str]:
    """Return the latest compiled ppt-master native DrawingML .pptx bytes & filename."""
    link = load_ppt_master_link(paper_dir)
    if link and link.get("latest_pptx"):
        p = Path(link["latest_pptx"])
        if p.exists():
            return p.read_bytes(), p.name
    # Recompile on demand if link exists
    if link:
        fresh = recompile_existing_svgs(paper_dir)
        if fresh.get("latest_pptx") and Path(fresh["latest_pptx"]).exists():
            p = Path(fresh["latest_pptx"])
            return p.read_bytes(), p.name
    raise FileNotFoundError("未找到 PPT-Master 编译的 .pptx 文件，请先生成。")
