"""PPT Studio (inspired by hugohe3/ppt-master):
Pre-generation wizard -> Editable Slide Deck JSON -> Natively editable 16:9 .pptx export via python-pptx.
"""

from __future__ import annotations

import json
import re
import time
import uuid
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

from .config import load_config
from .llm_analyzer import _call_chat_completion, _extract_json_block, find_agy_binary

STYLE_TEMPLATES: dict[str, dict[str, Any]] = {
    "nature_minimal": {
        "id": "nature_minimal",
        "name": "Nature 极简白",
        "tag": "学术组会经典",
        "desc": "纯净白底 + 深靛蓝标题条 + 翡翠绿强调，图表清晰度最高，适合日常组会与顶刊精读汇报。",
        "bg": "#FFFFFF",
        "surface": "#F4F6FA",
        "primary": "#1E3A8A",
        "accent": "#0F766E",
        "text": "#171B26",
        "muted": "#5B6476",
        "callout_bg": "#EFF6FF",
        "cover_bg": "#0F1E46",
        "cover_text": "#FFFFFF",
    },
    "deep_tech": {
        "id": "deep_tech",
        "name": "深空蓝科技风",
        "tag": "大报告 / 开题答辩",
        "desc": "深海蓝主视觉配亮青色指标卡片，极具现代 AI+生物 交叉学科气场，适合答辩与学术会议。",
        "bg": "#F8FAFC",
        "surface": "#EEF2F9",
        "primary": "#0F172A",
        "accent": "#0284C7",
        "text": "#0F172A",
        "muted": "#475569",
        "callout_bg": "#E0F2FE",
        "cover_bg": "#0B1120",
        "cover_text": "#F8FAFC",
    },
    "biomed_sage": {
        "id": "biomed_sage",
        "name": "清新科研绿",
        "tag": "生医 / 药学专场",
        "desc": "柔和薄荷白画布配森林墨绿与暖琥珀亮点，层次舒朗耐看，适合医学、生信与材料汇报。",
        "bg": "#FBFCFA",
        "surface": "#EEF5F1",
        "primary": "#065F46",
        "accent": "#D97706",
        "text": "#182620",
        "muted": "#4B6358",
        "callout_bg": "#FEF3C7",
        "cover_bg": "#064E3B",
        "cover_text": "#ECFDF5",
    },
    "editorial_warm": {
        "id": "editorial_warm",
        "name": "暖纸杂志风",
        "tag": "跨学科科普 / 零基础",
        "desc": "温暖象牙米纸底色配砖红与深棕文字，柔和护眼、故事感强，非常适合向跨专业听众讲清复杂论文。",
        "bg": "#FAF7F2",
        "surface": "#F2ECE1",
        "primary": "#9A3412",
        "accent": "#1D4ED8",
        "text": "#231F1D",
        "muted": "#6B625C",
        "callout_bg": "#FEF3C7",
        "cover_bg": "#431407",
        "cover_text": "#FFFBEB",
    },
    "dark_keynote": {
        "id": "dark_keynote",
        "name": "暗夜极客风",
        "tag": "大屏 / 暗室演讲",
        "desc": "深邃炭黑画布配霓虹蓝青数据高亮，在投影仪和暗室报告厅中视觉冲击力极强。",
        "bg": "#111622",
        "surface": "#1B2335",
        "primary": "#60A5FA",
        "accent": "#2DD4BF",
        "text": "#F1F5F9",
        "muted": "#94A3B8",
        "callout_bg": "#1E293B",
        "cover_bg": "#090D16",
        "cover_text": "#F8FAFC",
    },
}

AUDIENCE_PROFILES: dict[str, dict[str, str]] = {
    "lab_group": {
        "id": "lab_group",
        "label": "本课题组同门 / 导师",
        "hint": "重点突出实验设计、模型架构、关键对照数据与可借鉴方法细节",
    },
    "cross_discipline": {
        "id": "cross_discipline",
        "label": "跨学科 / 零生物背景听众",
        "hint": "全程配备大白话类比、术语直译与看图指南，让外行一听就懂",
    },
    "defense_panel": {
        "id": "defense_panel",
        "label": "答辩评委 / 大同行专家",
        "hint": "强调核心创新壁垒、量化提升倍数、外推泛化验证与局限性反思",
    },
    "quick_standup": {
        "id": "quick_standup",
        "label": "5 分钟组会快报",
        "hint": "直奔痛点、核心框架图、关键成绩单与 3 条核心结论，极速高效",
    },
}

FOCUS_OPTIONS: list[dict[str, str]] = [
    {"id": "background", "label": "研究背景与痛点"},
    {"id": "objective", "label": "研究目的与核心假设"},
    {"id": "methods", "label": "核心方法与技术路线"},
    {"id": "validation", "label": "多维验证与对照设计"},
    {"id": "results", "label": "核心数据与图表精讲"},
    {"id": "innovations", "label": "创新点与后验机理"},
    {"id": "critical", "label": "批判性审读与课题启发"},
    {"id": "citations", "label": "关键引文脉络溯源"},
]


def get_ppt_presets() -> dict[str, Any]:
    return {
        "styles": list(STYLE_TEMPLATES.values()),
        "audiences": list(AUDIENCE_PROFILES.values()),
        "focus_options": FOCUS_OPTIONS,
    }


def load_deck(paper_dir: Path) -> dict[str, Any] | None:
    p = paper_dir / "deck.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def save_deck(paper_dir: Path, deck: dict[str, Any]) -> dict[str, Any]:
    deck["updated_at"] = int(time.time())
    (paper_dir / "deck.json").write_text(
        json.dumps(deck, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return deck


def _make_slide(
    layout: str,
    tag: str,
    title: str,
    subtitle: str = "",
    bullets: list[str] | None = None,
    callout: str = "",
    figure_id: str | None = None,
    metrics: list[dict[str, str]] | None = None,
    speaker_notes: str = "",
) -> dict[str, Any]:
    return {
        "id": f"slide-{uuid.uuid4().hex[:6]}",
        "layout": layout,
        "tag": tag,
        "title": title,
        "subtitle": subtitle,
        "bullets": bullets or [],
        "callout": callout,
        "figure_id": figure_id,
        "metrics": metrics or [],
        "speaker_notes": speaker_notes,
    }


def _generate_deterministic_deck(
    manifest: dict[str, Any],
    analysis: dict[str, Any],
    ref_cache: dict[str, Any],
    options: dict[str, Any],
) -> dict[str, Any]:
    """Build a crisp, audience-tailored editable slide deck directly from analysis + figures (zero API key needed)."""
    style_id = options.get("style_id") or "nature_minimal"
    if style_id not in STYLE_TEMPLATES:
        style_id = "nature_minimal"
    audience = options.get("audience") or "cross_discipline"
    focus_list = options.get("focus") or [
        "background",
        "objective",
        "methods",
        "validation",
        "results",
        "innovations",
        "critical",
    ]
    slide_density = options.get("density") or "standard"  # compact | standard | deep
    custom_note = (options.get("custom_note") or "").strip()

    is_beginner = audience == "cross_discipline"
    is_expert = audience == "defense_panel"
    is_quick = audience == "quick_standup" or slide_density == "compact"

    dims = {d["key"]: d for d in analysis.get("dimensions", [])}
    figs = manifest.get("figures", [])
    fig_map = {f["id"]: f for f in figs}
    fig_notes = analysis.get("figure_notes", {})

    title_zh = analysis.get("paper_title_zh") or manifest.get("title") or "文献深度汇报"
    title_en = manifest.get("title") or ""
    authors = (manifest.get("authors") or "")[:140]
    doi = manifest.get("doi") or ""

    slides: list[dict[str, Any]] = []

    # Slide 1: Cover
    aud_label = AUDIENCE_PROFILES.get(audience, {}).get("label", "文献汇报")
    cover_sub = title_en if len(title_en) <= 130 else title_en[:127] + "..."
    slides.append(
        _make_slide(
            layout="cover",
            tag=f"LITERATURE SEMINAR · {aud_label}",
            title=title_zh,
            subtitle=cover_sub,
            bullets=[
                f"作者团队：{authors}" if authors else "PaperLens 文献精读汇报",
                f"文献标识：DOI {doi}" if doi else f"全文 {manifest.get('page_count', '')} 页 · {manifest.get('figure_count', 0)} 张核心图表",
                f"定制重点：{custom_note}" if custom_note else (analysis.get("one_sentence_tldr") or "")[:110],
            ],
            callout=analysis.get("beginner_hook", "")[:140] if is_beginner else "",
            speaker_notes=(
                f"大家好，今天向大家汇报这篇论文《{title_zh}》。"
                + (analysis.get("one_sentence_tldr") or "")
                + (f" 本次汇报特别聚焦：{custom_note}" if custom_note else "")
            ),
        )
    )

    # Slide 2: Agenda & 1-Sentence Takeaway (skip in ultra-compact if needed, keep in standard/deep)
    if not is_quick or len(focus_list) >= 5:
        wf_steps = analysis.get("workflow_steps", [])
        agenda_bullets = [f"Step {s['step']} · {s['title']}：{s['desc']}" for s in wf_steps[:5]]
        if not agenda_bullets:
            agenda_bullets = [f"{d['num']} {d['title']}：{d.get('subtitle', '')}" for d in analysis.get("dimensions", [])[:5]]
        slides.append(
            _make_slide(
                layout="agenda",
                tag="00 · 全文导览",
                title="30 秒看懂这篇论文的完整主线",
                subtitle="研究问题 → 核心方法 → 多维验证 → 关键突破",
                bullets=agenda_bullets,
                callout=(
                    f"💡 零基础直觉：{analysis.get('beginner_hook', '')}"
                    if is_beginner and analysis.get("beginner_hook")
                    else f"📌 一句话结论：{analysis.get('one_sentence_tldr', '')}"
                ),
                speaker_notes="在进入细节之前，先用一张导览图串起整篇论文的五步逻辑闭环，帮助大家建立全局视角。",
            )
        )

    # Helper to create dimension slides
    def _add_dim_slide(key: str, default_fig: str | None = None, extra_tag: str = "") -> None:
        d = dims.get(key)
        if not d:
            return
        fid = default_fig or (d.get("figure_ids") or [None])[0]
        if fid and fid not in fig_map:
            fid = None
        bullets = list(d.get("bullets") or [])
        if not bullets and d.get("summary"):
            bullets = [d["summary"][:140]]
        if is_beginner and d.get("beginner_analogy"):
            callout = f"💡 大白话类比：{d['beginner_analogy']}"
        elif is_expert:
            callout = f"🎯 核心论点：{d.get('summary', '')[:160]}"
        else:
            callout = d.get("summary", "")[:160]

        short_title = d["title"]
        if d.get("subtitle") and len(d["title"]) <= 8:
            # Take clean first clause of subtitle without awkward mid-word cutoff
            first_clause = re.split(r"[？?！!；;—–]", d["subtitle"])[0].strip()
            if 4 <= len(first_clause) <= 22:
                short_title = f"{d['title']}：{first_clause}"
        slides.append(
            _make_slide(
                layout="figure_focus" if fid else "two_column",
                tag=f"{d.get('num', '')} · {extra_tag or d['title']}",
                title=short_title,
                subtitle=d.get("subtitle", ""),
                bullets=bullets[:4],
                callout=callout[:125] + ("…" if len(callout) > 125 else ""),
                figure_id=fid,
                speaker_notes=(
                    f"这一页讲{d['title']}。{d.get('summary', '')}"
                    + (f" 用通俗类比来说：{d.get('beginner_analogy', '')}" if is_beginner and d.get("beginner_analogy") else "")
                ),
            )
        )

    if "background" in focus_list:
        _add_dim_slide("background", default_fig=None, extra_tag="研究背景")

    if "objective" in focus_list:
        _add_dim_slide("objective", default_fig="fig-1" if "fig-1" in fig_map else None, extra_tag="研究目的与框架")

    if "methods" in focus_list:
        _add_dim_slide("methods", default_fig="fig-2" if "fig-2" in fig_map else (figs[0]["id"] if figs else None), extra_tag="核心方法")

    if "validation" in focus_list:
        _add_dim_slide("validation", default_fig="fig-3" if "fig-3" in fig_map else None, extra_tag="验证体系")

    if "results" in focus_list:
        # Dedicated high-impact figure slides for Results!
        res_dim = dims.get("results", {})
        res_figs = [fid for fid in (res_dim.get("figure_ids") or []) if fid in fig_map]
        if not res_figs and figs:
            res_figs = [f["id"] for f in figs[-2:]]

        # If table-1 is present, add a punchy metrics highlight + table slide
        if "table-1" in res_figs:
            tnote = fig_notes.get("table-1", {})
            sub_bullets = [f"{sp['label']}：{sp['detail']}" for sp in (tnote.get("subpanels") or [])[:4]]
            slides.append(
                _make_slide(
                    layout="figure_focus",
                    tag="05 · 核心成绩单",
                    title=tnote.get("title_zh") or "核心湿实验筛选结果总览",
                    subtitle="效价（MIC）、选择性（SI）与宿主安全窗（TI）全面跃升",
                    bullets=sub_bullets or (res_dim.get("bullets") or [])[:4],
                    callout=f"👀 看表指南：{tnote.get('how_to_read', '')}" if is_beginner else tnote.get("plain_summary", ""),
                    figure_id="table-1",
                    metrics=[
                        {"value": "5 μM", "label": "MAD5.1/5.3 强毒 MIC (4×提升)"},
                        {"value": "SI > 16", "label": "细菌选择性 (>8×提升)"},
                        {"value": "TI > 100", "label": "人肺细胞安全窗 (>20×提升)"},
                    ]
                    if manifest.get("paper_id") == "limits-2025"
                    else [],
                    speaker_notes=tnote.get("context_connection") or res_dim.get("summary", ""),
                )
            )

        if "fig-5" in res_figs and not is_quick:
            f5 = fig_notes.get("fig-5", {})
            slides.append(
                _make_slide(
                    layout="figure_focus",
                    tag="05 · 临床转化实战",
                    title=f5.get("title_zh") or "杀菌动力学与联合用药验证",
                    subtitle="攻克休眠持留菌 + 24 组临床抗生素 100% 友好联用",
                    bullets=[f"{sp['label']}：{sp['detail']}" for sp in (f5.get("subpanels") or [])[:4]],
                    callout=f"💡 核心洞察：{f5.get('context_connection', '')[:160]}",
                    figure_id="fig-5",
                    speaker_notes=f5.get("plain_summary", "") + " " + f5.get("context_connection", ""),
                )
            )
        elif "table-1" not in res_figs:
            _add_dim_slide("results", default_fig=res_figs[0] if res_figs else None, extra_tag="核心结果")

    if "innovations" in focus_list:
        f4 = fig_notes.get("fig-4", {})
        inn_dim = dims.get("innovations", {})
        if "fig-4" in fig_map:
            slides.append(
                _make_slide(
                    layout="figure_focus",
                    tag="06 · 创新点与后验机理",
                    title=f4.get("title_zh") or "后验解析与核心科学创新",
                    subtitle="AI 打开黑箱：揭示隐藏在生物复杂性中的物理规律",
                    bullets=[f"{sp['label']}：{sp['detail']}" for sp in (f4.get("subpanels") or [])[:4]]
                    or (inn_dim.get("bullets") or [])[:4],
                    callout=(
                        f"💡 大白话总结：{inn_dim.get('beginner_analogy', '')}"
                        if is_beginner and inn_dim.get("beginner_analogy")
                        else f4.get("plain_summary", "")
                    ),
                    figure_id="fig-4",
                    speaker_notes=f4.get("context_connection") or inn_dim.get("summary", ""),
                )
            )
        else:
            _add_dim_slide("innovations", default_fig=None, extra_tag="创新点与展望")

    if "citations" in focus_list and ref_cache and (slide_density == "deep" or "citations" in focus_list):
        top_refs = list(ref_cache.values())[:5]
        if top_refs:
            slides.append(
                _make_slide(
                    layout="two_column",
                    tag="REF · 关键引文脉络",
                    title="支撑本研究的 5 篇基石文献",
                    subtitle="顺藤摸瓜看清研究传承与关键证据链",
                    bullets=[
                        f"[Ref {r['number']}] {r.get('venue', '')} ({r.get('year', '')})：{r.get('why_cited') or r.get('plain_summary') or r.get('title', '')[:80]}"
                        for r in top_refs
                    ],
                    callout="📌 建议在组会提问环节重点准备这些支撑文献的对照细节。",
                    speaker_notes="这一页梳理了支撑本文立意与核心机理解释的最关键参考文献，便于大家快速回溯领域脉络。",
                )
            )

    if "critical" in focus_list:
        crits = analysis.get("critical_notes") or []
        slides.append(
            _make_slide(
                layout="takeaways",
                tag="07 · 批判性审读与课题启发",
                title="局限性反思 & 对我们课题的借鉴",
                subtitle="不只看亮点，更要看清未验证之处与下一步切入点",
                bullets=crits[:4] if crits else ["评估方法适用边界与数据集局限", "思考如何迁移至本课题组当前研究场景"],
                callout=(
                    f"🚀 结合本次汇报定制聚焦：{custom_note}"
                    if custom_note
                    else "💬 Q&A 讨论建议：可围绕『小样本特征工程迁移』『第二无序簇湿实验验证』展开组内头脑风暴。"
                ),
                speaker_notes="最后我们客观审视这篇论文的局限性和精读发现的细节问题，也欢迎各位老师同学围绕如何借鉴到我们自己的课题展开讨论。谢谢大家！",
            )
        )

    # Extra deep glossary slide for cross-discipline audience in deep mode
    if is_beginner and slide_density == "deep" and analysis.get("glossary"):
        top_terms = list(analysis["glossary"].items())[:6]
        slides.insert(
            2,
            _make_slide(
                layout="two_column",
                tag="GLOSSARY · 零基础术语速通",
                title="听懂本报告只需记住这 6 个核心概念",
                subtitle="跨学科大白话翻译，扫清专业术语障碍",
                bullets=[f"{k}（{v.get('zh', '')}）：{v.get('simple', '')}" for k, v in top_terms],
                callout="🎓 先建立直觉再看实验数据，整场报告就能丝滑听懂！",
                speaker_notes="考虑到在座有不同专业背景的同学，我们花 1 分钟先把后面反复出现的 6 个核心术语用大白话统一一下。",
            ),
        )

    return {
        "paper_id": manifest.get("paper_id"),
        "title": f"{title_zh} — 文献汇报",
        "style_id": style_id,
        "audience": audience,
        "focus": focus_list,
        "density": slide_density,
        "custom_note": custom_note,
        "generated_by": "paperlens_studio_rules",
        "created_at": int(time.time()),
        "updated_at": int(time.time()),
        "slides": slides,
    }


def generate_deck(paper_dir: Path, options: dict[str, Any]) -> dict[str, Any]:
    """Generate a tailored editable slide deck (uses LLM if configured & requested, otherwise high-craft adaptive engine)."""
    manifest = json.loads((paper_dir / "manifest.json").read_text(encoding="utf-8"))
    analysis = (
        json.loads((paper_dir / "analysis.json").read_text(encoding="utf-8"))
        if (paper_dir / "analysis.json").exists()
        else {}
    )
    ref_cache = (
        json.loads((paper_dir / "ref_cache.json").read_text(encoding="utf-8"))
        if (paper_dir / "ref_cache.json").exists()
        else {}
    )

    use_llm = bool(options.get("use_llm", False))
    cfg = load_config()
    has_llm = (
        ((cfg.get("llm_provider") or "agy_cli") == "agy_cli" and bool(find_agy_binary()))
        or bool((cfg.get("llm_api_key") or "").strip())
        or ("localhost" in (cfg.get("llm_base_url") or "") or "127.0.0.1" in (cfg.get("llm_base_url") or ""))
    )

    if use_llm and has_llm:
        try:
            style_id = options.get("style_id") or "nature_minimal"
            audience = options.get("audience") or "cross_discipline"
            aud_info = AUDIENCE_PROFILES.get(audience, {})
            focus_ids = options.get("focus") or ["background", "objective", "methods", "results", "innovations", "critical"]
            density = options.get("density") or "standard"
            target_n = {"compact": "7-8", "standard": "10-12", "deep": "13-15"}.get(density, "10-12")
            custom_note = options.get("custom_note") or ""
            avail_figs = [f"{f['id']} ({f['label']}, P{f['page']})" for f in manifest.get("figures", [])]

            prompt = f"""请参考顶刊学术文献汇报规范（类似 PPT-Master 风格），基于下面这篇论文的深度解读结果，生成一份结构化、可直接二次编辑并导出 .pptx 的汇报幻灯片 JSON。

前置要求：
- 汇报对象：{aud_info.get('label', audience)}（{aud_info.get('hint', '')}）
- 汇报重点：{', '.join(focus_ids)}
- 目标页数：{target_n} 页
- 用户定制补充要求：{custom_note or '无'}
- 可选嵌入原图 ID（只能从中选择或填 null）：{', '.join(avail_figs) or '无'}

严格输出 JSON 数组（字段如下）：
[
  {{
    "layout": "cover | agenda | two_column | figure_focus | takeaways",
    "tag": "左上角短标签如 01 · 研究背景",
    "title": "页面主标题（简洁有力，10-22字）",
    "subtitle": "一句话副标题",
    "bullets": ["要点1（精炼数据或逻辑）", "要点2", "要点3"],
    "callout": "底部高亮结论/大白话类比/看图提示（可选）",
    "figure_id": "fig-1 或 null",
    "metrics": [{{"value": "5 μM", "label": "强毒 MIC"}}],
    "speaker_notes": "80-150字的口语化演讲逐字稿"
  }}
]

论文核心剖析素材：
{json.dumps({
    "title": manifest.get("title"),
    "title_zh": analysis.get("paper_title_zh"),
    "tldr": analysis.get("one_sentence_tldr"),
    "beginner_hook": analysis.get("beginner_hook"),
    "dimensions": analysis.get("dimensions"),
    "figure_notes": analysis.get("figure_notes"),
    "critical_notes": analysis.get("critical_notes"),
}, ensure_ascii=False)[:22000]}
"""
            raw = _call_chat_completion(
                [{"role": "system", "content": "输出严格合法的 JSON 数组。"}, {"role": "user", "content": prompt}],
                max_tokens=4096,
            )
            slides_raw = _extract_json_block(raw)
            if isinstance(slides_raw, list) and len(slides_raw) >= 3:
                slides = [
                    _make_slide(
                        layout=s.get("layout", "two_column"),
                        tag=s.get("tag", ""),
                        title=s.get("title", ""),
                        subtitle=s.get("subtitle", ""),
                        bullets=s.get("bullets") or [],
                        callout=s.get("callout", ""),
                        figure_id=s.get("figure_id"),
                        metrics=s.get("metrics") or [],
                        speaker_notes=s.get("speaker_notes", ""),
                    )
                    for s in slides_raw
                ]
                deck = {
                    "paper_id": manifest.get("paper_id"),
                    "title": f"{analysis.get('paper_title_zh') or manifest.get('title')} — 文献汇报",
                    "style_id": style_id,
                    "audience": audience,
                    "focus": focus_ids,
                    "density": density,
                    "custom_note": custom_note,
                    "generated_by": "llm_ppt_studio",
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                    "slides": slides,
                }
                return save_deck(paper_dir, deck)
        except Exception:
            pass

    deck = _generate_deterministic_deck(manifest, analysis, ref_cache, options)
    return save_deck(paper_dir, deck)


def _rgb(hex_str: str) -> RGBColor:
    h = hex_str.lstrip("#")
    return RGBColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _add_rect(slide, x, y, w, h, fill_hex: str, line_hex: str | None = None, rounded: bool = False):
    shape_type = MSO_SHAPE.ROUNDED_RECTANGLE if rounded else MSO_SHAPE.RECTANGLE
    shp = slide.shapes.add_shape(shape_type, Inches(x), Inches(y), Inches(w), Inches(h))
    shp.fill.solid()
    shp.fill.fore_color.rgb = _rgb(fill_hex)
    if line_hex:
        shp.line.color.rgb = _rgb(line_hex)
        shp.line.width = Pt(1.0)
    else:
        shp.line.fill.background()
    return shp


def _add_textbox(
    slide,
    x,
    y,
    w,
    h,
    text: str,
    font_size: int = 16,
    color_hex: str = "#171B26",
    bold: bool = False,
    align=PP_ALIGN.LEFT,
    font_name: str = "PingFang SC",
):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.TOP
    tf.margin_left = Inches(0.06)
    tf.margin_right = Inches(0.06)
    tf.margin_top = Inches(0.04)
    tf.margin_bottom = Inches(0.04)
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.name = font_name
    run.font.size = Pt(font_size)
    run.font.bold = bold
    run.font.color.rgb = _rgb(color_hex)
    return tb


def _add_bullets_box(
    slide,
    x,
    y,
    w,
    h,
    bullets: list[str],
    font_size: int = 15,
    color_hex: str = "#171B26",
    accent_hex: str = "#0F766E",
):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = Inches(0.08)
    tf.margin_right = Inches(0.08)
    tf.margin_top = Inches(0.06)
    tf.margin_bottom = Inches(0.06)

    for idx, item in enumerate(bullets):
        p = tf.paragraphs[0] if idx == 0 else tf.add_paragraph()
        p.space_after = Pt(10)
        p.line_spacing = 1.25
        r_dot = p.add_run()
        r_dot.text = "▸ "
        r_dot.font.name = "PingFang SC"
        r_dot.font.size = Pt(font_size)
        r_dot.font.bold = True
        r_dot.font.color.rgb = _rgb(accent_hex)

        r_txt = p.add_run()
        r_txt.text = item
        r_txt.font.name = "PingFang SC"
        r_txt.font.size = Pt(font_size)
        r_txt.font.color.rgb = _rgb(color_hex)
    return tb


def _add_fitted_picture(slide, img_path: Path, box_x: float, box_y: float, box_w: float, box_h: float) -> None:
    if not img_path.exists():
        return
    with Image.open(img_path) as im:
        iw, ih = im.size
    if iw <= 0 or ih <= 0:
        return
    ratio = min(box_w / iw, box_h / ih)
    final_w = iw * ratio
    final_h = ih * ratio
    left = box_x + (box_w - final_w) / 2.0
    top = box_y + (box_h - final_h) / 2.0
    slide.shapes.add_picture(str(img_path), Inches(left), Inches(top), width=Inches(final_w), height=Inches(final_h))


def export_pptx_bytes(paper_dir: Path, deck: dict[str, Any] | None = None) -> bytes:
    """Compile deck.json into a natively editable 16:9 PowerPoint (.pptx) with vector shapes, figures & speaker notes."""
    if deck is None:
        deck = load_deck(paper_dir)
    if not deck:
        raise ValueError("尚未生成 PPT 幻灯片，请先在 PPT 制作板块选择前置条件并生成。")

    manifest = json.loads((paper_dir / "manifest.json").read_text(encoding="utf-8"))
    fig_map = {f["id"]: f for f in manifest.get("figures", [])}
    theme = STYLE_TEMPLATES.get(deck.get("style_id") or "nature_minimal", STYLE_TEMPLATES["nature_minimal"])

    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    slides_data = deck.get("slides") or []
    total = len(slides_data)

    for idx, s in enumerate(slides_data, start=1):
        sl = prs.slides.add_slide(blank_layout)
        layout = s.get("layout", "two_column")

        if layout == "cover":
            # Full rich cover slide
            _add_rect(sl, 0, 0, 13.333, 7.5, theme["cover_bg"])
            _add_rect(sl, 0, 0, 0.28, 7.5, theme["accent"])
            _add_rect(sl, 0.9, 1.05, 4.2, 0.42, theme["accent"], rounded=True)
            _add_textbox(sl, 0.98, 1.08, 4.0, 0.36, s.get("tag") or "LITERATURE SEMINAR", 12, "#FFFFFF", bold=True)
            _add_textbox(sl, 0.9, 1.75, 11.4, 1.65, s.get("title") or "", 34, theme["cover_text"], bold=True)
            if s.get("subtitle"):
                _add_textbox(sl, 0.9, 3.45, 11.4, 0.85, s["subtitle"], 16, "#CBD5E1")
            if s.get("bullets"):
                _add_bullets_box(sl, 0.9, 4.45, 11.2, 2.2, s["bullets"], font_size=14, color_hex="#E2E8F0", accent_hex=theme["accent"])
        else:
            # Content slide canvas
            _add_rect(sl, 0, 0, 13.333, 7.5, theme["bg"])
            # Top slim accent bar
            _add_rect(sl, 0, 0, 13.333, 0.12, theme["primary"])

            # Tag pill + Title + Subtitle
            _add_textbox(sl, 0.65, 0.32, 6.0, 0.32, s.get("tag") or f"SLIDE {idx}", 11, theme["accent"], bold=True)
            _add_textbox(sl, 0.65, 0.62, 11.4, 0.65, s.get("title") or "", 24, theme["primary"], bold=True)
            if s.get("subtitle"):
                _add_textbox(sl, 0.65, 1.26, 11.6, 0.38, s["subtitle"], 13, theme["muted"])

            # Divider line
            _add_rect(sl, 0.65, 1.68, 12.03, 0.02, theme["surface"])

            fig = fig_map.get(s.get("figure_id") or "")
            img_path = (paper_dir / fig["image"]) if fig else None
            has_fig = bool(img_path and img_path.exists())
            metrics = s.get("metrics") or []

            body_top = 1.85
            if metrics:
                # Render metric KPI cards strip across top
                card_w = (12.03 - 0.25 * (len(metrics) - 1)) / len(metrics)
                for m_i, m in enumerate(metrics[:4]):
                    cx = 0.65 + m_i * (card_w + 0.25)
                    _add_rect(sl, cx, body_top, card_w, 0.92, theme["surface"], line_hex=theme["accent"], rounded=True)
                    _add_textbox(sl, cx + 0.12, body_top + 0.08, card_w - 0.24, 0.44, m.get("value", ""), 22, theme["accent"], bold=True, align=PP_ALIGN.CENTER)
                    _add_textbox(sl, cx + 0.12, body_top + 0.52, card_w - 0.24, 0.32, m.get("label", ""), 11, theme["muted"], align=PP_ALIGN.CENTER)
                body_top += 1.08

            callout_h = 0.92 if s.get("callout") else 0.0
            content_h = 6.95 - body_top - callout_h - (0.18 if callout_h else 0.0)

            if has_fig and img_path is not None:
                # Left: structured bullets; Right: crisp white framed original figure
                _add_rect(sl, 0.65, body_top, 5.45, content_h, theme["surface"], rounded=True)
                _add_bullets_box(sl, 0.80, body_top + 0.12, 5.15, content_h - 0.24, s.get("bullets") or [], font_size=14, color_hex=theme["text"], accent_hex=theme["accent"])

                _add_rect(sl, 6.32, body_top, 6.36, content_h, "#FFFFFF", line_hex=theme["surface"], rounded=True)
                _add_fitted_picture(sl, img_path, 6.44, body_top + 0.12, 6.12, content_h - 0.48)
                _add_textbox(sl, 6.44, body_top + content_h - 0.34, 6.12, 0.28, f"{fig['label']} (Page {fig['page']})", 10, theme["muted"], align=PP_ALIGN.CENTER)
            else:
                # Full-width clean structured card(s)
                bullets = s.get("bullets") or []
                if layout == "two_column" and len(bullets) >= 4:
                    mid = (len(bullets) + 1) // 2
                    _add_rect(sl, 0.65, body_top, 5.88, content_h, theme["surface"], rounded=True)
                    _add_bullets_box(sl, 0.82, body_top + 0.16, 5.54, content_h - 0.32, bullets[:mid], font_size=15, color_hex=theme["text"], accent_hex=theme["accent"])
                    _add_rect(sl, 6.80, body_top, 5.88, content_h, theme["surface"], rounded=True)
                    _add_bullets_box(sl, 6.97, body_top + 0.16, 5.54, content_h - 0.32, bullets[mid:], font_size=15, color_hex=theme["text"], accent_hex=theme["accent"])
                else:
                    _add_rect(sl, 0.65, body_top, 12.03, content_h, theme["surface"], rounded=True)
                    _add_bullets_box(sl, 0.88, body_top + 0.18, 11.55, content_h - 0.36, bullets, font_size=16, color_hex=theme["text"], accent_hex=theme["accent"])

            # Bottom Callout Banner
            if s.get("callout"):
                cy = 6.95 - callout_h
                _add_rect(sl, 0.65, cy, 12.03, callout_h, theme["callout_bg"], rounded=True)
                _add_rect(sl, 0.65, cy, 0.10, callout_h, theme["accent"])
                _add_textbox(sl, 0.88, cy + 0.12, 11.65, callout_h - 0.20, s["callout"], 13, theme["text"], bold=False)

            # Footer page number
            _add_textbox(sl, 0.65, 7.08, 8.0, 0.30, f"PaperLens 文献汇报 · {manifest.get('doi') or manifest.get('paper_id')}", 9, theme["muted"])
            _add_textbox(sl, 11.6, 7.08, 1.08, 0.30, f"{idx} / {total}", 10, theme["muted"], bold=True, align=PP_ALIGN.RIGHT)

        # Speaker notes (natively editable in PowerPoint!)
        if s.get("speaker_notes"):
            notes_slide = sl.notes_slide
            notes_slide.notes_text_frame.text = s["speaker_notes"]

    buf = BytesIO()
    prs.save(buf)
    return buf.getvalue()
