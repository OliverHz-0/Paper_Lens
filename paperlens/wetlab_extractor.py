"""Wet-Lab Experimental Protocol Extractor & Printable SOP Handbook Exporter.

Supports:
1. Instant deterministic scan of a paper's slices & figures to locate wet-lab paragraphs,
   reagents, conditions, assays, and numeric parameters (temperature, concentration, time, RPM).
2. LLM deep distillation into a structured, bench-ready Wet-Lab Protocol Handbook
   (`wetlab_protocol.json`), honoring purely computational papers honestly (`has_wetlab: false`).
3. Clean export to Markdown (`.md` with checkboxes) and standalone printable A4 HTML/PDF.
"""

from __future__ import annotations

import html
import json
import re
import time
from pathlib import Path
from typing import Any, Callable

from .llm_analyzer import _call_chat_completion, _extract_json_block

# High-signal wet-lab lexical probes (tag -> regex)
WETLAB_PROBES: list[tuple[str, re.Pattern[str]]] = [
    ("多肽/化学合成", re.compile(r"\b(Fmoc|solid[- ]phase|SPPS|resin|cleavage|TFA|HPLC|RP-HPLC|lyophiliz\w*|MALDI|ESI-MS|LC-MS|synthesis|synthesized|purified)\b", re.I)),
    ("抑菌/抗菌测定 (MIC/MBC)", re.compile(r"\b(MIC|MBC|broth microdilution|agar|CFU|colony[- ]forming|time[- ]kill|kill kinetics|persister|biofilm|optical density|OD\s*600|OD600|Mueller[- ]Hinton|7H9|7H10|OADC|Middlebrook|LB broth)\b", re.I)),
    ("溶血与细胞毒性", re.compile(r"\b(hemoly\w*|erythrocyte|red blood cell|RBC|cytotoxic\w*|MTT|CCK-?8|MTS|LDH|cell viability|IC50|CC50|HC50|HeLa|A549|HEK\s*293|Vero|DMEM|RPMI|FBS|trypsin|CO2 incubator)\b", re.I)),
    ("膜作用与理化表征", re.compile(r"\b(circular dichroism|CD spectr\w*|liposome|vesicle|calcein|leakage|PI uptake|propidium iodide|SYTOX|NPN|DiSC3|membrane depolarization|permeabiliz\w*|DLS|zeta potential|FTIR|NMR)\b", re.I)),
    ("显微成像 (SEM/TEM/荧光)", re.compile(r"\b(SEM|TEM|scanning electron|transmission electron|confocal|CLSM|fluorescence microscopy|AFM|glutaraldehyde|fixation|dehydration|staining)\b", re.I)),
    ("分子与生化实验", re.compile(r"\b(PCR|qPCR|RT-qPCR|Western blot|SDS-PAGE|ELISA|flow cytometry|FACS|chromatography|centrifug\w*|sonicat\w*|autoclave|sterile|filter[- ]sterilized)\b", re.I)),
    ("动物/体内实验", re.compile(r"\b(in vivo|mice|mouse|murine|rat|intraperitoneal|intravenous|subcutaneous|oral gavage|histology|H&E|IACUC|animal protocol|CFU/g|organ burden)\b", re.I)),
    ("试剂与缓冲配制", re.compile(r"\b(PBS|DMSO|Tris|HEPES|BSA|Tween[- ]?20|Tween[- ]?80|Triton\s*X-?100|buffer|stock solution|serial dilution|96-well|microplate|incubat\w*)\b", re.I)),
]

PARAM_PATTERN = re.compile(
    r"(?:\d+(?:\.\d+)?\s*(?:°C|℃|µM|μM|uM|mM|nM|mg/mL|µg/mL|μg/mL|ug/mL|ng/mL|mL|µL|μL|uL|rpm|×\s*g|xg|min|h|hr|hrs|hours|days|%)\b)",
    re.I,
)


def _protocol_path(paper_dir: Path) -> Path:
    return paper_dir / "wetlab_protocol.json"


def load_wetlab_protocol(paper_dir: Path) -> dict[str, Any] | None:
    p = _protocol_path(paper_dir)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def scan_wetlab_candidates(paper_dir: Path) -> dict[str, Any]:
    """Deterministic fast scan of manifest slices for wet-lab content."""
    manifest = json.loads((paper_dir / "manifest.json").read_text(encoding="utf-8"))
    analysis = (
        json.loads((paper_dir / "analysis.json").read_text(encoding="utf-8"))
        if (paper_dir / "analysis.json").exists()
        else {}
    )
    slice_notes = analysis.get("slice_notes", {})

    candidates: list[dict[str, Any]] = []
    all_tags: dict[str, int] = {}

    for s in manifest.get("slices", []):
        sec = (s.get("section") or "").lower()
        if sec == "references":
            continue
        text = s.get("text") or ""
        matched_tags: list[str] = []
        hit_score = 0

        for tag, pat in WETLAB_PROBES:
            matches = pat.findall(text)
            if matches:
                matched_tags.append(tag)
                hit_score += min(4, len(matches))
                all_tags[tag] = all_tags.get(tag, 0) + 1

        params = list(dict.fromkeys(m.strip() for m in PARAM_PATTERN.findall(text)))[:10]
        if params:
            hit_score += min(3, len(params))
        if sec == "methods":
            hit_score += 2

        if matched_tags or (sec == "methods" and len(params) >= 2):
            note = slice_notes.get(s["id"], {})
            candidates.append(
                {
                    "slice_id": s["id"],
                    "page": s.get("page"),
                    "section": sec,
                    "section_label": s.get("section_label") or sec,
                    "heading": note.get("heading") or s.get("section_label") or s["id"],
                    "score": hit_score,
                    "tags": matched_tags,
                    "params": params,
                    "excerpt": text[:260] + ("…" if len(text) > 260 else ""),
                }
            )

    candidates.sort(key=lambda x: (-x["score"], x["slice_id"]))
    strong_count = sum(1 for c in candidates if c["score"] >= 4)
    likely_has_wetlab = strong_count >= 2 or (len(candidates) >= 3 and sum(c["score"] for c in candidates) >= 10)

    return {
        "paper_id": manifest.get("paper_id"),
        "title": manifest.get("title"),
        "title_zh": analysis.get("paper_title_zh") or manifest.get("title"),
        "total_slices": len(manifest.get("slices", [])),
        "candidate_count": len(candidates),
        "strong_wetlab_slices": strong_count,
        "likely_has_wetlab": likely_has_wetlab,
        "detected_categories": [
            {"name": k, "count": v}
            for k, v in sorted(all_tags.items(), key=lambda kv: -kv[1])
        ],
        "candidates": candidates[:24],
    }


def _build_extraction_prompt(
    manifest: dict[str, Any],
    analysis: dict[str, Any],
    scan: dict[str, Any],
    focus_note: str = "",
) -> list[dict[str, str]]:
    """Build prompt containing prioritized methods/wet-lab slices & figure captions."""
    slices_by_id = {s["id"]: s for s in manifest.get("slices", [])}
    slice_notes = analysis.get("slice_notes", {})

    # Collect slices: prioritize wet-lab scored slices (skip pure dry-lab/ML slices in Methods!)
    # Also pull immediate continuation slices inside `methods` (e.g., equation/continuation blocks right after a wet-lab slice)
    all_slices = manifest.get("slices", [])
    order_idx = {s["id"]: i for i, s in enumerate(all_slices)}
    cand_scores = {c["slice_id"]: c["score"] for c in scan.get("candidates", [])}
    cand_tags = {c["slice_id"]: c.get("tags", []) for c in scan.get("candidates", [])}

    chosen_ids: list[str] = []
    seen: set[str] = set()

    def _add(sid: str) -> None:
        if sid not in seen and sid in slices_by_id:
            seen.add(sid)
            chosen_ids.append(sid)

    # 1. Abstract for overall study context
    for s in all_slices:
        if (s.get("section") or "").lower() == "abstract":
            _add(s["id"])
            break

    # 2. All wet-lab-matched `methods` slices + their immediate continuation slice inside `methods`
    for i, s in enumerate(all_slices):
        sec = (s.get("section") or "").lower()
        sid = s["id"]
        if sec == "methods" and cand_tags.get(sid):
            _add(sid)
            # Include short continuation/formula slice immediately following inside methods
            if i + 1 < len(all_slices):
                nxt = all_slices[i + 1]
                if (nxt.get("section") or "").lower() == "methods" and len(nxt.get("text") or "") < 600:
                    _add(nxt["id"])

    # 3. Top wet-lab candidate slices from other sections (e.g., results/associated)
    for c in scan.get("candidates", [])[:22]:
        if len(chosen_ids) >= 24:
            break
        _add(c["slice_id"])

    # Fallback if zero wet-lab tags matched (pure computational paper -> include abstract + first methods slices)
    if len(chosen_ids) <= 2:
        for s in all_slices[:10]:
            if (s.get("section") or "").lower() in ("abstract", "methods", "introduction"):
                _add(s["id"])

    chosen_ids.sort(key=lambda sid: order_idx.get(sid, 9999))

    # Build clean context fitting all wet-lab methods slices (~22k chars)
    chunks: list[str] = []
    total_chars = 0
    for sid in chosen_ids:
        s = slices_by_id[sid]
        sec_lbl = s.get("section_label") or s.get("section") or ""
        raw_txt = (s.get("text") or "")[:1600]
        block = f"### [{sid} | P{s.get('page')} | {sec_lbl}]\n{raw_txt}"
        if total_chars + len(block) > 22000:
            break
        chunks.append(block)
        total_chars += len(block)

    fig_lines = [
        f"- {f['id']} ({f.get('label')}, P{f.get('page')}): {(f.get('caption') or '')[:220]}"
        for f in manifest.get("figures", [])[:12]
    ]

    paper_title = manifest.get("title") or ""
    title_zh = analysis.get("paper_title_zh") or paper_title
    focus_clause = f"\n\n【读者特别关注的实验部分】\n{focus_note.strip()}" if focus_note.strip() else ""

    system_msg = (
        "你是一位严谨的学术文献阅读助手，擅长帮助跨学科读者（如计算机/非生物背景）梳理已发表同行评审论文中的「实验方法与湿实验验证章节」，整理成结构清晰、可溯源的《论文湿实验方法整理说明书》。\n"
        "你的任务：仅基于下方提供的已发表论文原文段落，客观提炼论文作者报道的湿实验体系（如样品制备与表征、体外活性/毒性测试、显微或光谱表征等），与纯计算/算法部分区分开，方便读者快速看懂、做文献笔记和审稿核对。\n\n"
        "【整理原则】\n"
        "1. 严格忠实原文报道：仅汇总论文原文中实际写出的材料、仪器、对照设置、条件参数与结果判读；原文未提及或指向 Supporting Information (SI) 的细节，请如实写「论文正文未注明（见 SI）」，切勿补充原文之外的细节。\n"
        "2. 诚实识别纯计算论文：若全文没有开展湿实验（纯干实验/纯算法），将 `has_wetlab` 设为 `false`，`protocols` 设为空数组，说明原因并在 `suggested_wetlab_validations` 中列出高层级验证方向。\n"
        "3. 客观清晰 + 零基础友好：按论文实验逻辑分模块梳理流程要点（每条要点标出原文段落编号如 `S14` 与文中报道的参数摘要），并配大白话导读帮助非专业读者理解每个实验验证了什么科学问题。\n"
        "4. 仅输出合法 JSON，不要输出任何额外说明或多余文本。"
    )

    schema_desc = """
请严格按以下 JSON 结构输出：
{
  "has_wetlab": true,
  "manual_title": "中文说明书标题（例如：《论文名 · 湿实验方法与验证说明书》）",
  "executive_summary": "2-4 句话概括全文湿实验验证框架（包含哪几类测试、如何验证计算预测结论）",
  "beginner_overview": "用 3-5 句零基础大白话，将整套实验设计比喻成通俗生活场景，解释为什么需要做这些测试",
  "no_wetlab_explanation": "仅当 has_wetlab=false 时填写：说明本文为何属于纯计算/干实验论文",
  "biosafety_and_prerequisites": {
    "biosafety_level": "论文涉及的常规实验室条件或合规提示（高层次概括）",
    "estimated_total_duration": "论文报道的典型测试周期范围（如未说明写：正文未注明总周期）",
    "safety_notes": ["论文中提到的合规/伦理/实验注意要点 1", "要点 2"]
  },
  "materials_and_reagents": [
    {
      "name": "文中提到的试剂、样品、细胞/模型或仪器名称（中英对照）",
      "category": "试剂/培养基 | 菌株/细胞/模型 | 耗材 | 仪器设备",
      "spec_or_source": "文中报道的规格、来源或型号（未注明则写：论文正文未注明）",
      "purpose": "在本文实验设计中起什么作用",
      "source_slices": ["S12"]
    }
  ],
  "protocols": [
    {
      "id": "P1",
      "title": "实验模块标题（例如：一、候选分子合成与纯度表征）",
      "objective": "该模块在论文中要验证的核心科学问题",
      "beginner_analogy": "零基础大白话类比（1-2 句）",
      "estimated_time": "文中提到的测定周期（未注明写：正文未注明）",
      "difficulty": "常规表征 | 标准体外测定 | 专项表征",
      "source_slices": ["S14", "S15"],
      "related_figures": ["fig-2"],
      "inputs_and_controls": {
        "sample_input": "文中报道的受试样品与分组设置",
        "positive_control": "文中报道的阳性对照（未提写：正文未明确提及）",
        "negative_control": "文中报道的阴性/空白对照",
        "replicates": "文中报道的重复次数（如 n=3）"
      },
      "steps": [
        {
          "step_no": 1,
          "action": "客观概括该环节的实验流程要点（中文 + 原文关键术语）",
          "key_params": "提炼原文中明确给出的关键测定参数（无则留空）",
          "critical_tip": "阅读或复核该环节时的关键考量/变量控制要点（无则留空）",
          "source_slice": "S14"
        }
      ],
      "readout_and_acceptance": "论文采用的评价指标、判读标准及报道的主要实验结果"
    }
  ],
  "missing_details_and_si_notes": [
    "列出论文正文省略、简写或指向 Supporting Information (SI) 的实验信息，便于查阅 SI 核对"
  ],
  "troubleshooting_guide": [
    {
      "issue": "实验设计或数据解读中的关键质量控制点 / 常见偏差",
      "likely_cause": "影响因素",
      "solution": "论文采用的控制手段或复核建议"
    }
  ],
  "suggested_wetlab_validations": [
    {
      "title": "仅当 has_wetlab=false 时提供 2-4 条高层级验证实验方向标题",
      "goal": "验证目标",
      "outline": "高层级实验思路与评价指标"
    }
  ]
}
"""

    user_msg = (
        f"论文标题（英）：{paper_title}\n"
        f"论文标题（中）：{title_zh}\n"
        f"DOI：{manifest.get('doi') or '未知'}\n"
        f"初步规则扫描提示：检测到 {scan['candidate_count']} 段候选实验段落（强信号 {scan['strong_wetlab_slices']} 段），"
        f"涵盖类别：{', '.join(c['name'] for c in scan.get('detected_categories', [])) or '无明显湿实验词'}\n"
        f"{focus_clause}\n\n"
        f"【论文图表目录】\n" + ("\n".join(fig_lines) or "无") + "\n\n"
        f"【论文实验与相关原文段落】\n" + "\n\n".join(chunks) + "\n\n"
        f"{schema_desc}"
    )

    return [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_msg},
    ]


def _build_deterministic_handbook(
    manifest: dict[str, Any],
    analysis: dict[str, Any],
    scan: dict[str, Any],
    focus_note: str = "",
    fallback_reason: str = "",
) -> dict[str, Any]:
    """Deterministic fallback built directly from manifest.json + analysis.json wet-lab slices."""
    slices_by_id = {s["id"]: s for s in manifest.get("slices", [])}
    slice_notes = analysis.get("slice_notes", {})
    title_zh = analysis.get("paper_title_zh") or manifest.get("title") or ""
    dims = {d.get("key"): d for d in analysis.get("dimensions", [])}
    val_dim = dims.get("validation", {})
    meth_dim = dims.get("methods", {})

    if not scan.get("likely_has_wetlab"):
        return {
            "paper_id": manifest.get("paper_id"),
            "paper_title": manifest.get("title"),
            "paper_title_zh": title_zh,
            "doi": manifest.get("doi") or "",
            "authors": manifest.get("authors") or "",
            "focus_note": focus_note.strip(),
            "extracted_at": int(time.time()),
            "mode": "deterministic_fallback",
            "fallback_reason": fallback_reason,
            "scan_summary": {
                "candidate_count": scan["candidate_count"],
                "strong_wetlab_slices": scan["strong_wetlab_slices"],
                "detected_categories": scan["detected_categories"],
            },
            "has_wetlab": False,
            "manual_title": f"《{title_zh}》湿实验核验说明",
            "executive_summary": "规则扫描未在正文中检测到明显的湿实验测定章节，本文大概率属于纯计算/算法研究。",
            "beginner_overview": "",
            "no_wetlab_explanation": "正文中未检测到抑菌测定、细胞/溶血实验、样品合成或显微表征等典型湿实验段落。",
            "biosafety_and_prerequisites": {},
            "materials_and_reagents": [],
            "protocols": [],
            "missing_details_and_si_notes": [],
            "troubleshooting_guide": [],
            "suggested_wetlab_validations": [],
        }

    # Group candidate slices by primary detected category
    grouped: dict[str, list[dict[str, Any]]] = {}
    for c in scan.get("candidates", []):
        cat = (c.get("tags") or ["常规实验方法"])[0]
        grouped.setdefault(cat, []).append(c)

    protocols: list[dict[str, Any]] = []
    for idx, (cat_name, items) in enumerate(grouped.items(), start=1):
        steps = []
        sids = []
        figs: list[str] = []
        for st_no, c in enumerate(items[:6], start=1):
            sid = c["slice_id"]
            sids.append(sid)
            s = slices_by_id.get(sid, {})
            note = slice_notes.get(sid, {})
            for fid in s.get("cited_figures") or []:
                if fid not in figs:
                    figs.append(fid)
            action = note.get("translation_zh") or note.get("role") or c.get("excerpt") or ""
            steps.append(
                {
                    "step_no": st_no,
                    "action": action[:420],
                    "key_params": " · ".join(c.get("params") or [])[:120],
                    "critical_tip": note.get("plain_explanation", "")[:180],
                    "source_slice": sid,
                }
            )
        protocols.append(
            {
                "id": f"P{idx}",
                "title": f"{cat_name}相关实验段落汇总",
                "objective": f"汇总论文中涉及「{cat_name}」的原文报道内容与关键数值参数。",
                "beginner_analogy": "",
                "estimated_time": "详见原文及 Supporting Information",
                "difficulty": "原文结构化提取",
                "source_slices": sids,
                "related_figures": figs,
                "inputs_and_controls": {
                    "sample_input": "见各步骤原文定位",
                    "positive_control": "见原文方法与图表说明",
                    "negative_control": "见原文方法与图表说明",
                    "replicates": "见原文图注或 SI",
                },
                "steps": steps,
                "readout_and_acceptance": "请点击各步骤右侧原文锚点查看高清段落截图与对应实验结果图。",
            }
        )

    return {
        "paper_id": manifest.get("paper_id"),
        "paper_title": manifest.get("title"),
        "paper_title_zh": title_zh,
        "doi": manifest.get("doi") or "",
        "authors": manifest.get("authors") or "",
        "focus_note": focus_note.strip(),
        "extracted_at": int(time.time()),
        "mode": "deterministic_fallback",
        "fallback_reason": fallback_reason,
        "scan_summary": {
            "candidate_count": scan["candidate_count"],
            "strong_wetlab_slices": scan["strong_wetlab_slices"],
            "detected_categories": scan["detected_categories"],
        },
        "has_wetlab": True,
        "manual_title": f"《{title_zh}》湿实验方法整理说明书",
        "executive_summary": val_dim.get("summary") or meth_dim.get("summary") or f"已自动分离并归类本文 {len(scan.get('candidates', []))} 段湿实验相关原文，共整理为 {len(protocols)} 个模块。",
        "beginner_overview": val_dim.get("beginner_analogy") or meth_dim.get("beginner_analogy") or "",
        "no_wetlab_explanation": "",
        "biosafety_and_prerequisites": {
            "biosafety_level": "请依据论文原始方法章节及所在实验室生物安全规范核对。",
            "estimated_total_duration": "详见原文方法与 Supporting Information",
            "safety_notes": [
                fallback_reason
                or "当前为原文结构化提取模式（已保留全部中文译文、数值参数与原文段落锚点）。"
            ],
        },
        "materials_and_reagents": [],
        "protocols": protocols,
        "missing_details_and_si_notes": [
            "本文实验完整试剂货号与补充步骤请对照论文 Supporting Information (SI) 核验。"
        ],
        "troubleshooting_guide": [],
        "suggested_wetlab_validations": [],
    }


def extract_wetlab_protocol(
    paper_dir: Path,
    focus_note: str = "",
    progress_cb: Callable[[int, str], None] | None = None,
) -> dict[str, Any]:
    """Run LLM extraction of the paper's wet-lab protocols and save wetlab_protocol.json."""
    def _prog(pct: int, msg: str) -> None:
        if progress_cb:
            progress_cb(pct, msg)

    _prog(12, "正在扫描论文实验章节、材料试剂与关键数值参数...")
    manifest = json.loads((paper_dir / "manifest.json").read_text(encoding="utf-8"))
    analysis = (
        json.loads((paper_dir / "analysis.json").read_text(encoding="utf-8"))
        if (paper_dir / "analysis.json").exists()
        else {}
    )
    scan = scan_wetlab_candidates(paper_dir)

    _prog(35, "正在调用大模型提炼湿实验方法整理说明书（物料汇总、模块步骤与对照参数）...")
    messages = _build_extraction_prompt(manifest, analysis, scan, focus_note=focus_note)
    raw = _call_chat_completion(messages, max_tokens=6500)

    _prog(85, "正在校验实验步骤结构与原文段落锚点...")
    lower_raw = raw.lower()
    if "blocked by" in lower_raw and "filters" in lower_raw:
        result = _build_deterministic_handbook(
            manifest,
            analysis,
            scan,
            focus_note=focus_note,
            fallback_reason="当前模型对含病原体关键词的论文触发了安全策略拦截，已自动切换为基于本文已解析原文与中文译文的「无损结构化说明书」模式（可在设置中切换其他兼容 API 模型重新提炼）。",
        )
        _protocol_path(paper_dir).write_text(
            json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        _prog(100, "已生成基于原文与译文的湿实验结构化说明书！")
        return result

    try:
        parsed = _extract_json_block(raw)
    except Exception as exc:
        raise RuntimeError(f"大模型返回内容未能解析为 JSON：{exc}（返回片段：{raw[:160]}）") from exc

    if not isinstance(parsed, dict):
        raise RuntimeError("大模型返回的湿实验说明书格式异常（非 JSON 对象）。")

    result: dict[str, Any] = {
        "paper_id": manifest.get("paper_id"),
        "paper_title": manifest.get("title"),
        "paper_title_zh": analysis.get("paper_title_zh") or manifest.get("title"),
        "doi": manifest.get("doi") or "",
        "authors": manifest.get("authors") or "",
        "focus_note": focus_note.strip(),
        "extracted_at": int(time.time()),
        "mode": "llm_deep",
        "scan_summary": {
            "candidate_count": scan["candidate_count"],
            "strong_wetlab_slices": scan["strong_wetlab_slices"],
            "detected_categories": scan["detected_categories"],
        },
        "has_wetlab": bool(parsed.get("has_wetlab", True)),
        "manual_title": parsed.get("manual_title") or f"《{analysis.get('paper_title_zh') or manifest.get('title')}》湿实验操作说明书",
        "executive_summary": parsed.get("executive_summary") or "",
        "beginner_overview": parsed.get("beginner_overview") or "",
        "no_wetlab_explanation": parsed.get("no_wetlab_explanation") or "",
        "biosafety_and_prerequisites": parsed.get("biosafety_and_prerequisites") or {},
        "materials_and_reagents": parsed.get("materials_and_reagents") or [],
        "protocols": parsed.get("protocols") or [],
        "missing_details_and_si_notes": parsed.get("missing_details_and_si_notes") or [],
        "troubleshooting_guide": parsed.get("troubleshooting_guide") or [],
        "suggested_wetlab_validations": parsed.get("suggested_wetlab_validations") or [],
    }

    _protocol_path(paper_dir).write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    _prog(100, "湿实验操作说明书已提炼完成！")
    return result


def export_wetlab_markdown(paper_dir: Path, protocol_obj: dict[str, Any] | None = None) -> str:
    """Export the distilled wet-lab protocol handbook as clean, checkable Markdown."""
    data = protocol_obj or load_wetlab_protocol(paper_dir)
    if not data:
        raise FileNotFoundError("该论文尚未生成湿实验操作说明书，请先点击提取。")

    lines: list[str] = []
    lines.append(f"# {data.get('manual_title') or '湿实验操作说明书'}")
    lines.append("")
    lines.append(f"> **来源论文（中）**：{data.get('paper_title_zh') or ''}")
    lines.append(f"> **来源论文（英）**：*{data.get('paper_title') or ''}*")
    if data.get("authors"):
        lines.append(f"> **作者**：{data['authors']}")
    if data.get("doi"):
        lines.append(f"> **DOI**：https://doi.org/{data['doi']}")
    if data.get("focus_note"):
        lines.append(f"> **定制关注重点**：{data['focus_note']}")
    lines.append("")

    if not data.get("has_wetlab", True):
        lines.append("## 湿实验判定：本文未包含真实湿实验（纯计算 / 干实验论文）")
        lines.append("")
        lines.append(data.get("no_wetlab_explanation") or data.get("executive_summary") or "")
        lines.append("")
        sugs = data.get("suggested_wetlab_validations") or []
        if sugs:
            lines.append("## 建议补充的湿实验验证方案")
            lines.append("")
            for i, s in enumerate(sugs, 1):
                lines.append(f"### {i}. {s.get('title', '')}")
                if s.get("goal"):
                    lines.append(f"- **验证目标**：{s['goal']}")
                if s.get("outline"):
                    lines.append(f"- **建议方案与指标**：{s['outline']}")
                lines.append("")
        return "\n".join(lines) + "\n"

    # 1. Overview & Beginner guide
    lines.append("## 一、湿实验总览")
    lines.append("")
    if data.get("executive_summary"):
        lines.append(data["executive_summary"])
        lines.append("")
    if data.get("beginner_overview"):
        lines.append(f"> **零基础大白话导读**：{data['beginner_overview']}")
        lines.append("")

    # 2. Biosafety & prerequisites
    bio = data.get("biosafety_and_prerequisites") or {}
    if bio:
        lines.append("## 二、生物安全与前置准备")
        lines.append("")
        if bio.get("biosafety_level"):
            lines.append(f"- **安全等级提示**：{bio['biosafety_level']}")
        if bio.get("estimated_total_duration"):
            lines.append(f"- **预计总周期**：{bio['estimated_total_duration']}")
        for note in bio.get("safety_notes") or []:
            lines.append(f"- **安全注意**：{note}")
        lines.append("")

    # 3. Materials & Reagents Checklist
    mats = data.get("materials_and_reagents") or []
    if mats:
        lines.append("## 三、试剂、材料与仪器准备清单")
        lines.append("")
        lines.append("| 备齐 | 类别 | 名称 | 规格 / 来源 | 用途 | 原文定位 |")
        lines.append("| :---: | :--- | :--- | :--- | :--- | :--- |")
        for m in mats:
            srcs = ", ".join(m.get("source_slices") or [])
            lines.append(
                f"| [ ] | {m.get('category', '')} | **{m.get('name', '')}** | "
                f"{m.get('spec_or_source', '论文正文未注明')} | {m.get('purpose', '')} | {srcs} |"
            )
        lines.append("")

    # 4. Step-by-step SOP Protocols
    protocols = data.get("protocols") or []
    if protocols:
        lines.append("## 四、分模块标准操作流程（SOP）")
        lines.append("")
        for proto in protocols:
            lines.append(f"### {proto.get('id', '')} · {proto.get('title', '')}")
            meta_bits = []
            if proto.get("estimated_time"):
                meta_bits.append(f"预计耗时：{proto['estimated_time']}")
            if proto.get("difficulty"):
                meta_bits.append(f"操作难度：{proto['difficulty']}")
            if proto.get("source_slices"):
                meta_bits.append(f"原文段落：{', '.join(proto['source_slices'])}")
            if proto.get("related_figures"):
                meta_bits.append(f"关联图表：{', '.join(proto['related_figures'])}")
            if meta_bits:
                lines.append(f"*{' | '.join(meta_bits)}*")
            lines.append("")
            if proto.get("objective"):
                lines.append(f"- **实验目的**：{proto['objective']}")
            if proto.get("beginner_analogy"):
                lines.append(f"- **大白话理解**：{proto['beginner_analogy']}")

            ctrl = proto.get("inputs_and_controls") or {}
            if any(ctrl.values()):
                if ctrl.get("sample_input"):
                    lines.append(f"- **待测样品设置**：{ctrl['sample_input']}")
                if ctrl.get("positive_control"):
                    lines.append(f"- **阳性对照**：{ctrl['positive_control']}")
                if ctrl.get("negative_control"):
                    lines.append(f"- **阴性/空白对照**：{ctrl['negative_control']}")
                if ctrl.get("replicates"):
                    lines.append(f"- **重复次数**：{ctrl['replicates']}")
            lines.append("")
            lines.append("#### 操作步骤")
            for st in proto.get("steps") or []:
                num = st.get("step_no", "")
                act = st.get("action", "")
                params = f" `[{st['key_params']}]`" if st.get("key_params") else ""
                src = f" *({st['source_slice']})*" if st.get("source_slice") else ""
                lines.append(f"- [ ] **Step {num}.** {act}{params}{src}")
                if st.get("critical_tip"):
                    lines.append(f"  - *注意 / 技巧*：{st['critical_tip']}")
            lines.append("")
            if proto.get("readout_and_acceptance"):
                lines.append(f"> **检测判读与预期结果**：{proto['readout_and_acceptance']}")
                lines.append("")

    # 5. Missing details / SI notes
    missing = data.get("missing_details_and_si_notes") or []
    if missing:
        lines.append("## 五、正文省略细节与 SI 核对提醒")
        lines.append("")
        for item in missing:
            lines.append(f"- [ ] {item}")
        lines.append("")

    # 6. Troubleshooting
    trouble = data.get("troubleshooting_guide") or []
    if trouble:
        lines.append("## 六、常见问题排查（Troubleshooting）")
        lines.append("")
        lines.append("| 现象 / 隐患 | 可能原因 | 解决建议 |")
        lines.append("| :--- | :--- | :--- |")
        for t in trouble:
            lines.append(
                f"| **{t.get('issue', '')}** | {t.get('likely_cause', '')} | {t.get('solution', '')} |"
            )
        lines.append("")

    return "\n".join(lines) + "\n"


def export_wetlab_html(paper_dir: Path, protocol_obj: dict[str, Any] | None = None) -> str:
    """Export a clean, standalone A4 printable HTML SOP handbook (ready for Save-as-PDF)."""
    data = protocol_obj or load_wetlab_protocol(paper_dir)
    if not data:
        raise FileNotFoundError("该论文尚未生成湿实验操作说明书，请先点击提取。")

    e = html.escape
    title = data.get("manual_title") or "湿实验操作说明书"
    bio = data.get("biosafety_and_prerequisites") or {}

    mats_rows = "".join(
        f"""<tr>
          <td style="text-align:center"><input type="checkbox" /></td>
          <td><span class="pill">{e(m.get('category', ''))}</span></td>
          <td><strong>{e(m.get('name', ''))}</strong></td>
          <td>{e(m.get('spec_or_source', '论文正文未注明'))}</td>
          <td>{e(m.get('purpose', ''))}</td>
          <td class="mono">{e(', '.join(m.get('source_slices') or []))}</td>
        </tr>"""
        for m in (data.get("materials_and_reagents") or [])
    )

    proto_blocks = []
    for p in data.get("protocols") or []:
        ctrl = p.get("inputs_and_controls") or {}
        steps_html = "".join(
            f"""<li class="step-item">
              <label class="step-check">
                <input type="checkbox" />
                <span class="step-num">Step {e(str(st.get('step_no', '')))}</span>
                <span class="step-act">{e(st.get('action', ''))}</span>
              </label>
              {f'<div class="param-line">关键参数：{e(st["key_params"])}</div>' if st.get("key_params") else ''}
              {f'<div class="tip-line">注意：{e(st["critical_tip"])}</div>' if st.get("critical_tip") else ''}
            </li>"""
            for st in (p.get("steps") or [])
        )
        proto_blocks.append(
            f"""<section class="proto-card">
              <div class="proto-head">
                <div>
                  <span class="proto-id">{e(p.get('id', ''))}</span>
                  <h3>{e(p.get('title', ''))}</h3>
                </div>
                <div class="proto-meta">
                  {f'<span class="pill">{e(p["estimated_time"])}</span>' if p.get("estimated_time") else ''}
                  {f'<span class="pill">{e(p["difficulty"])}</span>' if p.get("difficulty") else ''}
                  {f'<span class="pill mono">{e(", ".join(p.get("source_slices") or []))}</span>' if p.get("source_slices") else ''}
                </div>
              </div>
              {f'<p class="obj"><strong>实验目的：</strong>{e(p["objective"])}</p>' if p.get("objective") else ''}
              {f'<div class="well-warm"><strong>零基础大白话：</strong>{e(p["beginner_analogy"])}</div>' if p.get("beginner_analogy") else ''}
              <div class="ctrl-grid">
                <div><strong>待测样品</strong><span>{e(ctrl.get("sample_input") or "—")}</span></div>
                <div><strong>阳性对照</strong><span>{e(ctrl.get("positive_control") or "正文未明确提及")}</span></div>
                <div><strong>阴性对照</strong><span>{e(ctrl.get("negative_control") or "正文未明确提及")}</span></div>
                <div><strong>重复次数</strong><span>{e(ctrl.get("replicates") or "正文未明确提及")}</span></div>
              </div>
              <ol class="steps-list">{steps_html}</ol>
              {f'<div class="well-blue"><strong>检测判读与预期结果：</strong>{e(p["readout_and_acceptance"])}</div>' if p.get("readout_and_acceptance") else ''}
            </section>"""
        )

    missing_html = "".join(
        f"<li><label><input type='checkbox' /> {e(item)}</label></li>"
        for item in (data.get("missing_details_and_si_notes") or [])
    )
    trouble_rows = "".join(
        f"<tr><td><strong>{e(t.get('issue', ''))}</strong></td><td>{e(t.get('likely_cause', ''))}</td><td>{e(t.get('solution', ''))}</td></tr>"
        for t in (data.get("troubleshooting_guide") or [])
    )

    body_main = ""
    if not data.get("has_wetlab", True):
        sug_html = "".join(
            f"<div class='proto-card'><h3>{i}. {e(s.get('title', ''))}</h3><p><strong>验证目标：</strong>{e(s.get('goal', ''))}</p><p><strong>建议方案：</strong>{e(s.get('outline', ''))}</p></div>"
            for i, s in enumerate(data.get("suggested_wetlab_validations") or [], 1)
        )
        body_main = f"""
          <div class="well-warm">
            <strong>湿实验判定：</strong>本文未包含真实湿实验（纯计算 / 干实验论文）。<br/>
            {e(data.get("no_wetlab_explanation") or data.get("executive_summary") or "")}
          </div>
          {f'<h2>建议补充的湿实验验证方案</h2>{sug_html}' if sug_html else ''}
        """
    else:
        safety_list = "".join(f"<li>{e(n)}</li>" for n in (bio.get("safety_notes") or []))
        body_main = f"""
          <section class="card">
            <h2>一、湿实验总览与安全前提</h2>
            <p>{e(data.get("executive_summary") or "")}</p>
            {f'<div class="well-warm"><strong>零基础大白话导读：</strong>{e(data["beginner_overview"])}</div>' if data.get("beginner_overview") else ''}
            <div class="meta-strip">
              {f'<div><strong>安全等级：</strong>{e(bio.get("biosafety_level", ""))}</div>' if bio.get("biosafety_level") else ''}
              {f'<div><strong>预计周期：</strong>{e(bio.get("estimated_total_duration", ""))}</div>' if bio.get("estimated_total_duration") else ''}
            </div>
            {f'<ul class="safety-ul">{safety_list}</ul>' if safety_list else ''}
          </section>

          {f'<section class="card"><h2>二、试剂、材料与仪器准备清单</h2><table><thead><tr><th style="width:42px">备齐</th><th style="width:110px">类别</th><th>名称</th><th>规格 / 来源</th><th>用途</th><th style="width:76px">来源</th></tr></thead><tbody>{mats_rows}</tbody></table></section>' if mats_rows else ''}

          <section>
            <h2>三、分模块标准操作流程（SOP）</h2>
            {"".join(proto_blocks)}
          </section>

          {f'<section class="card"><h2>四、正文省略细节与 SI 核对清单</h2><ul class="check-ul">{missing_html}</ul></section>' if missing_html else ''}

          {f'<section class="card"><h2>五、常见问题排查（Troubleshooting）</h2><table><thead><tr><th>常见现象 / 隐患</th><th>可能原因</th><th>解决建议</th></tr></thead><tbody>{trouble_rows}</tbody></table></section>' if trouble_rows else ''}
        """

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{e(title)}</title>
<style>
  :root {{ --bg:#f6f5f4; --card:#fff; --border:#e6e6e6; --text:#181817; --muted:#615d59; --accent:#0075de; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; padding:28px 20px 60px; background:var(--bg); color:var(--text); font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Inter",sans-serif; line-height:1.65; font-size:14px; }}
  .page {{ max-width:960px; margin:0 auto; }}
  .toolbar {{ display:flex; justify-content:space-between; align-items:center; gap:12px; margin-bottom:18px; padding:12px 16px; background:var(--card); border:1px solid var(--border); border-radius:12px; }}
  .btn-print {{ background:var(--accent); color:#fff; border:none; padding:8px 16px; border-radius:999px; font-weight:600; font-size:13px; cursor:pointer; }}
  header.doc-head {{ background:var(--card); border:1px solid var(--border); border-radius:14px; padding:24px 26px; margin-bottom:18px; }}
  header.doc-head h1 {{ margin:0 0 8px; font-size:24px; letter-spacing:-0.02em; }}
  .doc-sub {{ color:var(--muted); font-size:13px; margin:2px 0; }}
  .card, .proto-card {{ background:var(--card); border:1px solid var(--border); border-radius:14px; padding:20px 22px; margin-bottom:16px; break-inside:avoid; }}
  h2 {{ font-size:17px; margin:0 0 12px; letter-spacing:-0.01em; }}
  h3 {{ font-size:15.5px; margin:4px 0 0; }}
  .well-warm {{ background:#fff6ed; border:1px solid #f4d6bc; padding:11px 14px; border-radius:10px; margin:10px 0; font-size:13.5px; }}
  .well-blue {{ background:#e8f1fb; border:1px solid #c5dff7; padding:11px 14px; border-radius:10px; margin-top:12px; font-size:13.5px; }}
  .meta-strip {{ display:flex; flex-wrap:wrap; gap:18px; margin-top:10px; font-size:13px; color:var(--muted); }}
  .safety-ul, .check-ul {{ margin:10px 0 0; padding-left:18px; }}
  .check-ul {{ list-style:none; padding-left:0; }}
  .check-ul li {{ margin:6px 0; }}
  table {{ width:100%; border-collapse:collapse; font-size:13px; }}
  th, td {{ border:1px solid var(--border); padding:8px 10px; text-align:left; vertical-align:top; }}
  th {{ background:#f6f5f4; font-weight:700; }}
  .pill {{ display:inline-block; padding:2px 8px; border-radius:999px; background:#f2f1ef; color:#31302e; font-size:12px; font-weight:600; }}
  .mono {{ font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:12px; }}
  .proto-head {{ display:flex; justify-content:space-between; align-items:flex-start; gap:12px; flex-wrap:wrap; margin-bottom:10px; }}
  .proto-id {{ display:inline-block; background:var(--accent); color:#fff; font-size:11.5px; font-weight:700; padding:2px 8px; border-radius:6px; }}
  .proto-meta {{ display:flex; gap:6px; flex-wrap:wrap; }}
  .ctrl-grid {{ display:grid; grid-template-columns:repeat(auto-fit, minmax(190px, 1fr)); gap:8px; margin:12px 0; padding:10px 12px; background:#f6f5f4; border-radius:10px; font-size:12.5px; }}
  .ctrl-grid div {{ display:flex; flex-direction:column; gap:2px; }}
  .ctrl-grid span {{ color:var(--muted); }}
  .steps-list {{ list-style:none; padding:0; margin:12px 0 0; display:flex; flex-direction:column; gap:10px; }}
  .step-item {{ padding:10px 12px; border:1px solid var(--border); border-radius:10px; }}
  .step-check {{ display:flex; align-items:flex-start; gap:8px; cursor:pointer; }}
  .step-num {{ font-weight:700; color:var(--accent); white-space:nowrap; }}
  .param-line {{ margin:5px 0 0 24px; font-size:12.5px; font-weight:600; color:#005bab; background:#e8f1fb; display:inline-block; padding:2px 8px; border-radius:6px; }}
  .tip-line {{ margin:5px 0 0 24px; font-size:12.5px; color:#9a4400; }}
  @media print {{
    body {{ background:#fff; padding:0; font-size:12px; }}
    .toolbar {{ display:none !important; }}
    .card, .proto-card, header.doc-head {{ border-color:#d8d8d8; box-shadow:none; }}
  }}
</style>
</head>
<body>
  <div class="page">
    <div class="toolbar">
      <span><strong>PaperLens 湿实验操作说明书</strong> · 可勾选备料清单，或直接打印 / 另存为 PDF</span>
      <button class="btn-print" onclick="window.print()">打印 / 另存为 PDF</button>
    </div>
    <header class="doc-head">
      <h1>{e(title)}</h1>
      <div class="doc-sub">来源论文：{e(data.get("paper_title_zh") or "")}（{e(data.get("paper_title") or "")}）</div>
      {f'<div class="doc-sub">作者：{e(data["authors"])}</div>' if data.get("authors") else ''}
      {f'<div class="doc-sub">DOI：https://doi.org/{e(data["doi"])}</div>' if data.get("doi") else ''}
    </header>
    {body_main}
  </div>
</body>
</html>
"""
