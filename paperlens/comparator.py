"""Cross-paper comparison & relationship synthesis engine (Deterministic Graph + Deep LLM Synthesis)."""

from __future__ import annotations

import json
import re
import time
import uuid
from pathlib import Path
from typing import Any, Callable

from .config import DATA_DIR, PROJECT_ROOT
from .llm_analyzer import _call_chat_completion, _extract_json_block

COMPARISONS_DIR = PROJECT_ROOT / "data" / "comparisons"


def _norm_str(s: str) -> str:
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", (s or "").lower())


def _load_paper_record(paper_id: str) -> dict[str, Any] | None:
    pdir = DATA_DIR / paper_id
    mpath = pdir / "manifest.json"
    if not mpath.exists():
        return None
    manifest = json.loads(mpath.read_text(encoding="utf-8"))
    analysis = (
        json.loads((pdir / "analysis.json").read_text(encoding="utf-8"))
        if (pdir / "analysis.json").exists()
        else {}
    )
    resources = (
        json.loads((pdir / "resources.json").read_text(encoding="utf-8"))
        if (pdir / "resources.json").exists()
        else {}
    )
    return {
        "paper_id": paper_id,
        "manifest": manifest,
        "analysis": analysis,
        "resources": resources,
    }


def compute_deterministic_comparison(paper_ids: list[str]) -> dict[str, Any]:
    """Compute instant evidence-backed cross-paper links: shared refs, direct citations, shared tools/terms & 6-dim matrix."""
    records = []
    for pid in paper_ids:
        rec = _load_paper_record(pid)
        if rec:
            records.append(rec)
    if len(records) < 2:
        raise ValueError("请至少选择 2 篇已解析的论文进行对比分析。")

    papers_meta = []
    for idx, rec in enumerate(records):
        m, a = rec["manifest"], rec["analysis"]
        papers_meta.append(
            {
                "paper_id": rec["paper_id"],
                "short_label": f"P{idx + 1}",
                "title": m.get("title", rec["paper_id"]),
                "title_zh": a.get("paper_title_zh") or m.get("title", rec["paper_id"]),
                "authors": (m.get("authors") or "")[:120],
                "doi": m.get("doi"),
                "page_count": m.get("page_count", 0),
                "reference_count": m.get("reference_count", 0),
                "analysis_mode": a.get("mode", "structural_fallback"),
                "tldr": a.get("one_sentence_tldr") or "",
            }
        )

    # 1. Shared references (Bibliographic coupling by DOI or normalized title)
    ref_buckets: dict[str, dict[str, Any]] = {}
    for rec in records:
        pid = rec["paper_id"]
        for ref in rec["manifest"].get("references", []):
            doi = (ref.get("doi") or "").strip().lower()
            title_norm = _norm_str(ref.get("title") or "")
            key = f"doi:{doi}" if doi else (f"title:{title_norm[:48]}" if len(title_norm) >= 18 else "")
            if not key:
                continue
            bucket = ref_buckets.setdefault(
                key,
                {
                    "title": ref.get("title") or ref.get("raw", "")[:120],
                    "authors": ref.get("authors") or "",
                    "year": ref.get("year"),
                    "doi": ref.get("doi"),
                    "cited_by": {},
                },
            )
            bucket["cited_by"][pid] = ref.get("number")

    shared_references = [
        {
            "title": b["title"],
            "authors": b["authors"],
            "year": b["year"],
            "doi": b["doi"],
            "cited_by": b["cited_by"],
            "count": len(b["cited_by"]),
        }
        for b in ref_buckets.values()
        if len(b["cited_by"]) >= 2
    ]
    shared_references.sort(key=lambda x: (-x["count"], -(x["year"] or 0)))

    # 2. Direct citation links (Does Paper A cite Paper B?)
    direct_citations: list[dict[str, Any]] = []
    for src in records:
        src_pid = src["paper_id"]
        src_refs = src["manifest"].get("references", [])
        for dst in records:
            dst_pid = dst["paper_id"]
            if src_pid == dst_pid:
                continue
            dst_doi = (dst["manifest"].get("doi") or "").strip().lower()
            dst_title_norm = _norm_str(dst["manifest"].get("title") or "")
            for r in src_refs:
                r_doi = (r.get("doi") or "").strip().lower()
                r_raw_norm = _norm_str(r.get("raw") or "")
                matched = (dst_doi and r_doi and dst_doi == r_doi) or (
                    len(dst_title_norm) >= 22 and dst_title_norm[:36] in r_raw_norm
                )
                if matched:
                    direct_citations.append(
                        {
                            "from_paper": src_pid,
                            "to_paper": dst_pid,
                            "ref_number": r.get("number"),
                            "raw": r.get("raw", "")[:180],
                        }
                    )
                    break

    # 3. Shared Glossary Terms & Bio/AI Keywords
    term_map: dict[str, dict[str, Any]] = {}
    for rec in records:
        pid = rec["paper_id"]
        g = rec["analysis"].get("glossary") or {}
        for k, v in g.items():
            nk = _norm_str(k)
            if not nk:
                continue
            entry = term_map.setdefault(
                nk,
                {"term": k, "zh": v.get("zh", ""), "simple": v.get("simple", ""), "papers": []},
            )
            if pid not in entry["papers"]:
                entry["papers"].append(pid)

    # Also scan common domain databases/models across full slice text
    domain_probes = [
        ("DBAASP", "抗菌肽数据库与理化特征工具"),
        ("APD3", "抗菌肽数据库 APD3"),
        ("CAMP", "抗菌肽数据库 CAMP"),
        ("AntiTbPdb", "抗结核多肽数据库"),
        ("ESM-2", "Meta 蛋白语言模型 ESM-2"),
        ("LSTM", "长短期记忆循环神经网络"),
        ("Random Forest", "随机森林机器学习模型"),
        ("Genetic Algorithm", "遗传算法定向进化"),
        ("MIC", "最低抑菌浓度指标"),
        ("Hemolysis", "人红细胞溶血毒性评估"),
        ("ESKAPE", "六大院内耐药菌群"),
        ("M. tuberculosis", "结核分枝杆菌"),
        ("E. coli", "大肠杆菌"),
        ("S. aureus", "金黄色葡萄球菌"),
        ("AlphaFold", "蛋白质 3D 结构预测"),
        ("PCA", "主成分分析降维"),
    ]
    shared_concepts: list[dict[str, Any]] = [
        {"name": v["term"], "desc": v["zh"] or v["simple"][:40], "papers": v["papers"], "kind": "glossary"}
        for v in term_map.values()
        if len(v["papers"]) >= 2
    ]
    seen_concept_norms = {_norm_str(x["name"]) for x in shared_concepts}

    full_texts = {
        rec["paper_id"]: " ".join(s.get("text", "") for s in rec["manifest"].get("slices", []))
        for rec in records
    }
    for kw, desc in domain_probes:
        nk = _norm_str(kw)
        if nk in seen_concept_norms:
            continue
        pat = r"ESM-?2" if kw == "ESM-2" else re.escape(kw)
        hit_pids = [
            pid for pid, txt in full_texts.items() if re.search(pat, txt, re.I)
        ]
        if len(hit_pids) >= 2:
            seen_concept_norms.add(nk)
            shared_concepts.append({"name": kw, "desc": desc, "papers": hit_pids, "kind": "keyword"})

    # 4. Shared Web Tools / Databases (ignore boilerplate license/publisher hosts)
    ignore_hosts = {
        "creativecommons.org", "orcid.org", "doi.org", "dx.doi.org",
        "pubs.acs.org", "nature.com", "www.nature.com", "link.springer.com",
        "springernature.com", "www.springernature.com", "academic.oup.com",
        "www.ncbi.nlm.nih.gov", "pubmed.ncbi.nlm.nih.gov", "crossref.org",
    }
    tool_map: dict[str, set[str]] = {}
    for rec in records:
        pid = rec["paper_id"]
        for t in rec["resources"].get("web_tools", []):
            host = re.sub(r"^https?://", "", t.get("url", "")).split("/")[0].lower()
            if host and host not in ignore_hosts:
                tool_map.setdefault(host, set()).add(pid)
    shared_tools = [
        {"host": h, "papers": sorted(pids)}
        for h, pids in tool_map.items()
        if len(pids) >= 2
    ]

    # 5. Raw 6-Dimension Side-by-Side Matrix directly from each paper's analysis.json
    dim_defs = [
        ("background", "01 · 研究背景"),
        ("objective", "02 · 研究目的"),
        ("methods", "03 · 核心方法"),
        ("validation", "04 · 验证体系"),
        ("results", "05 · 核心结果"),
        ("innovations", "06 · 创新与局限"),
    ]
    raw_six_dim_matrix = []
    for dkey, dlabel in dim_defs:
        cells = {}
        for rec in records:
            pid = rec["paper_id"]
            dims = {d["key"]: d for d in rec["analysis"].get("dimensions", [])}
            d = dims.get(dkey, {})
            cells[pid] = {
                "summary": d.get("summary") or "（该论文尚未完成 AI 深度解读）",
                "bullets": (d.get("bullets") or [])[:3],
                "analogy": d.get("beginner_analogy") or "",
            }
        raw_six_dim_matrix.append({"key": dkey, "label": dlabel, "cells": cells})

    return {
        "papers": papers_meta,
        "shared_references": shared_references[:20],
        "direct_citations": direct_citations,
        "shared_concepts": shared_concepts[:24],
        "shared_tools": shared_tools,
        "raw_six_dim_matrix": raw_six_dim_matrix,
    }


def _save_comparison(cmp_obj: dict[str, Any]) -> dict[str, Any]:
    COMPARISONS_DIR.mkdir(parents=True, exist_ok=True)
    cid = cmp_obj["id"]
    (COMPARISONS_DIR / f"{cid}.json").write_text(
        json.dumps(cmp_obj, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return cmp_obj


def list_comparisons() -> list[dict[str, Any]]:
    COMPARISONS_DIR.mkdir(parents=True, exist_ok=True)
    out = []
    for p in sorted(COMPARISONS_DIR.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            out.append(
                {
                    "id": d.get("id", p.stem),
                    "title": d.get("title", p.stem),
                    "topic_name": d.get("topic_name", ""),
                    "paper_ids": [x["paper_id"] for x in d.get("deterministic", {}).get("papers", [])],
                    "paper_count": len(d.get("deterministic", {}).get("papers", [])),
                    "mode": d.get("mode", "quick"),
                    "created_at": d.get("created_at", 0),
                }
            )
        except Exception:
            continue
    return out


def load_comparison(cmp_id: str) -> dict[str, Any] | None:
    p = COMPARISONS_DIR / f"{cmp_id}.json"
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def delete_comparison(cmp_id: str) -> None:
    p = COMPARISONS_DIR / f"{cmp_id}.json"
    if p.exists():
        p.unlink()


def run_deep_comparison(
    paper_ids: list[str],
    topic_name: str = "",
    focus_question: str = "",
    progress_cb: Callable[[int, str], None] | None = None,
) -> dict[str, Any]:
    """Run deterministic cross-paper evidence extraction + LLM deep comparison & relation synthesis."""
    if progress_cb:
        progress_cb(15, "正在抽取所选论文的六大维度剖析、参考文献交集与共同技术线索...")

    det = compute_deterministic_comparison(paper_ids)
    records = [_load_paper_record(pid) for pid in paper_ids]
    records = [r for r in records if r is not None]

    # Build compact synthesis digest for LLM
    digests = []
    for idx, rec in enumerate(records, start=1):
        m, a = rec["manifest"], rec["analysis"]
        dims_compact = {
            d["key"]: {
                "summary": (d.get("summary") or "")[:360],
                "bullets": (d.get("bullets") or [])[:3],
            }
            for d in a.get("dimensions", [])
        }
        digests.append(
            {
                "short_label": f"P{idx}",
                "paper_id": rec["paper_id"],
                "title": m.get("title"),
                "title_zh": a.get("paper_title_zh") or m.get("title"),
                "tldr": a.get("one_sentence_tldr") or "",
                "dimensions": dims_compact,
                "critical_notes": (a.get("critical_notes") or [])[:4],
                "abstract": next(
                    (s["text"][:900] for s in m.get("slices", []) if s.get("section") == "abstract"),
                    "",
                ),
            }
        )

    evidence_summary = {
        "shared_references_count": len(det["shared_references"]),
        "shared_references_sample": [r["title"] for r in det["shared_references"][:6]],
        "direct_citations": det["direct_citations"],
        "shared_concepts": [c["name"] for c in det["shared_concepts"][:15]],
    }

    if progress_cb:
        progress_cb(45, "正在调用大模型进行跨论文横向对比、关联图谱挖掘与融合创新推理...")

    prompt = f"""你是一位顶级的跨学科科研导师与综述专家，极其擅长把同一个研究方向下的多篇论文做【透彻横向对比 + 深度关联挖掘 + 零基础大白话拆解】。

用户选择了同一方向下的 {len(digests)} 篇论文进行对比分析：
- 所属课题方向：{topic_name or '同一研究方向'}
- 用户额外聚焦问题：{focus_question or '全面对比它们的研究思路、AI方法、数据需求、验证手段、核心结论，找出隐藏关联、互补点、分歧与可融合的课题创新机会'}

请严格返回合法 JSON（不要输出任何 Markdown 之外的多余解释），结构如下：
{{
  "title": "给这份多文对比报告起一个精炼有力的中文标题（14-28字）",
  "synthesis_headline": "一句话全景定位：这几篇论文在这个方向下分别扮演什么角色、构成什么技术图谱？（80-140字）",
  "beginner_analogy": "【零基础大白话流派对决】用生动的生活化类比，30 秒讲清这几篇论文各自是什么流派、差异在哪、谁擅长什么！（120-200字）",
  "paper_roles": [
    {{
      "paper_id": "必须严格使用输入的 paper_id",
      "archetype": "给这篇论文起一个 4-8 字的流派绰号（如：小样本物理派 / 蛋白大模型多标签派）",
      "core_edge": "它最不可替代的核心优势（30-60字）",
      "main_gap": "它最明显的短板或盲区（30-60字）"
    }}
  ],
  "comparison_matrix": [
    {{
      "dimension": "对比维度名（请设计 6-7 个最有洞察力的专业对比维度，如：研究任务与目标病原体、训练数据规模与特征表征、核心 AI 模型架构、实验验证深度与转化程度、量化性能与代表发现、主要局限与适用边界）",
      "cells": {{
        "<paper_id_1>": "精准凝练的对比内容（30-75字，尽量带关键数字或方法名）",
        "<paper_id_2>": "..."
      }},
      "insight": "这一维度的横向洞察一句话（25-55字）"
    }}
  ],
  "relations": [
    {{
      "from_paper": "<paper_id_a>",
      "to_paper": "<paper_id_b>",
      "relation_type": "方法互补 | 技术演进 | 范式分歧 | 靶标重叠 | 证据互印",
      "label": "4-10字连线短标签",
      "explanation": "详细解释这两篇论文之间的深层联系、谁能补谁的短板，或为何得出不同设计选择（60-120字）"
    }}
  ],
  "complementarities": [
    "【互补融合点1】具体说明如何把 A 的优点和 B 的优点组合起来..."
  ],
  "contradictions_or_tensions": [
    "【核心张力/分歧1】指出几篇论文在数据观、特征工程、模型复杂度或验证标准上的核心取舍..."
  ],
  "research_ideas": [
    {{
      "title": "可落地的新课题 / 融合创新 Idea 标题",
      "rationale": "为什么这个 Idea 能同时克服所选论文的共同短板？（60-110字）",
      "how_to_start": "第一步可以怎么借助这几篇论文的开源代码/数据快速做验证？（40-80字）"
    }}
  ]
}}

要求：
1. 所有 `paper_id` 必须严格与下方输入完全一致。
2. `relations` 必须覆盖所有两两组合（至少 {max(1, len(digests) * (len(digests) - 1) // 2)} 条有洞察力的双向/单向联系）。
3. 严禁编造论文中不存在的数据或模型名。

待对比论文完整摘要与剖析：
{json.dumps(digests, ensure_ascii=False)[:24000]}

已抽取的客观共享线索（共同引文/互引/共享关键词）：
{json.dumps(evidence_summary, ensure_ascii=False)}
"""

    raw = _call_chat_completion(
        [{"role": "system", "content": "输出严格有效的 JSON。"}, {"role": "user", "content": prompt}],
        max_tokens=4096,
    )
    synthesis = _extract_json_block(raw)

    if progress_cb:
        progress_cb(92, "正在保存跨文对比报告与关联图谱...")

    cmp_id = f"cmp-{int(time.time())}-{uuid.uuid4().hex[:5]}"
    cmp_obj = {
        "id": cmp_id,
        "mode": "llm_deep",
        "title": synthesis.get("title") or f"{len(digests)} 篇论文深度对比与关联分析",
        "topic_name": topic_name,
        "focus_question": focus_question,
        "paper_ids": [p["paper_id"] for p in det["papers"]],
        "created_at": int(time.time()),
        "deterministic": det,
        "synthesis": synthesis,
    }
    _save_comparison(cmp_obj)

    if progress_cb:
        progress_cb(100, "多文对比与关联分析已完成！")
    return cmp_obj


def export_comparison_markdown(cmp_obj: dict[str, Any]) -> str:
    """Export a saved comparison report into a clean Markdown literature-synthesis table & report."""
    det = cmp_obj.get("deterministic", {})
    syn = cmp_obj.get("synthesis") or {}
    papers = det.get("papers", [])

    lines = [f"# {cmp_obj.get('title', '多文对比与关联分析报告')}\n"]
    if cmp_obj.get("topic_name"):
        lines.append(f"> **研究方向**：{cmp_obj['topic_name']}  ")
    lines.append(
        "> **参与对比论文**："
        + " / ".join(f"[{p['short_label']}] {p['title_zh']}" for p in papers)
    )
    lines.append("")

    if syn.get("synthesis_headline"):
        lines.append("## 一、全景定位与零基础流派对决")
        lines.append(f"- **全景定位**：{syn['synthesis_headline']}")
        if syn.get("beginner_analogy"):
            lines.append(f"- **大白话类比**：{syn['beginner_analogy']}")
        lines.append("")

    if syn.get("comparison_matrix"):
        lines.append("## 二、多维度横向对比矩阵")
        header = "| 对比维度 | " + " | ".join(f"{p['short_label']} · {p['title_zh'][:18]}" for p in papers) + " | 横向洞察 |"
        sep = "| :--- | " + " | ".join(":---" for _ in papers) + " | :--- |"
        lines.extend([header, sep])
        for row in syn["comparison_matrix"]:
            cells = row.get("cells", {})
            vals = [str(cells.get(p["paper_id"], "")).replace("\n", " ") for p in papers]
            lines.append(f"| **{row.get('dimension', '')}** | " + " | ".join(vals) + f" | {row.get('insight', '')} |")
        lines.append("")

    if syn.get("relations"):
        lines.append("## 三、论文间深层关联")
        pmap = {p["paper_id"]: p["short_label"] for p in papers}
        for rel in syn["relations"]:
            a = pmap.get(rel.get("from_paper"), rel.get("from_paper"))
            b = pmap.get(rel.get("to_paper"), rel.get("to_paper"))
            lines.append(f"- **{a} ↔ {b}【{rel.get('relation_type', '')} · {rel.get('label', '')}】**：{rel.get('explanation', '')}")
        lines.append("")

    if syn.get("complementarities") or syn.get("contradictions_or_tensions"):
        lines.append("## 四、互补融合 vs 核心分歧")
        for c in syn.get("complementarities", []):
            lines.append(f"- **互补融合**：{c}")
        for t in syn.get("contradictions_or_tensions", []):
            lines.append(f"- **张力分歧**：{t}")
        lines.append("")

    if syn.get("research_ideas"):
        lines.append("## 五、下一步课题创新切入点")
        for i, idea in enumerate(syn["research_ideas"], start=1):
            lines.append(f"### {i}. {idea.get('title', '')}")
            lines.append(f"- **立意依据**：{idea.get('rationale', '')}")
            lines.append(f"- **快速验证路径**：{idea.get('how_to_start', '')}")
        lines.append("")

    if det.get("shared_references"):
        lines.append("## 附：实证共同引用文献")
        for r in det["shared_references"]:
            lines.append(f"- **{r['title']}** ({r.get('year') or ''}) — 共同被 {r['count']} 篇引用")

    return "\n".join(lines) + "\n"
