"""Export a PaperLens paper bundle into a clean, self-contained Markdown report."""

from __future__ import annotations

import json
from pathlib import Path


def export_markdown(paper_dir: Path) -> str:
    manifest = json.loads((paper_dir / "manifest.json").read_text(encoding="utf-8"))
    analysis = (
        json.loads((paper_dir / "analysis.json").read_text(encoding="utf-8"))
        if (paper_dir / "analysis.json").exists()
        else {}
    )
    resources = (
        json.loads((paper_dir / "resources.json").read_text(encoding="utf-8"))
        if (paper_dir / "resources.json").exists()
        else {}
    )

    lines: list[str] = []
    title_zh = analysis.get("paper_title_zh") or manifest.get("title")
    lines.append(f"# {title_zh}")
    lines.append(f"\n> **原文题名**：*{manifest.get('title')}*  ")
    if manifest.get("authors"):
        lines.append(f"> **作者**：{manifest.get('authors')}  ")
    if manifest.get("doi"):
        lines.append(f"> **DOI**：https://doi.org/{manifest.get('doi')}")
    lines.append("")

    if analysis.get("one_sentence_tldr"):
        lines.append("## 一句话速览 & 零基础直觉")
        lines.append(f"- **核心总结**：{analysis['one_sentence_tldr']}")
        if analysis.get("beginner_hook"):
            lines.append(f"- **大白话类比**：{analysis['beginner_hook']}")
        lines.append("")

    # 6 Core Dimensions
    lines.append("## 一、六大核心维度深度剖析")
    fig_map = {f["id"]: f for f in manifest.get("figures", [])}
    for dim in analysis.get("dimensions", []):
        lines.append(f"\n### {dim['num']}. {dim['title']}（{dim.get('subtitle', '')}）")
        lines.append(dim.get("summary", ""))
        if dim.get("beginner_analogy"):
            lines.append(f"\n> **零基础大白话**：{dim['beginner_analogy']}")
        for b in dim.get("bullets", []):
            lines.append(f"- {b}")
        for fid in dim.get("figure_ids", []):
            f = fig_map.get(fid)
            if f:
                lines.append(f"\n![{f['label']}]({f['image']})")
                lines.append(f"*{f['label']} (P{f['page']})*: {f['caption']}")

    # Glossary
    if analysis.get("glossary"):
        lines.append("\n## 二、零基础专业术语词典")
        lines.append("| 术语 | 中文名 | 大白话解释 | 在本文中的作用 |")
        lines.append("| :--- | :--- | :--- | :--- |")
        for k, v in analysis["glossary"].items():
            lines.append(f"| **{k}** | {v.get('zh', '')} | {v.get('simple', '')} | {v.get('in_paper', '')} |")

    # Slice-by-slice
    lines.append("\n## 三、从头到尾逐段切片对照精读")
    slice_notes = analysis.get("slice_notes", {})
    for s in manifest.get("slices", []):
        note = slice_notes.get(s["id"], {})
        heading = note.get("heading") or s["section_label"]
        lines.append(f"\n### [{s['id']} · P{s['page']}] {heading}")
        lines.append(f"![{s['id']} 原文截图]({s['image']})")
        lines.append(f"\n> **英文原文**：{s['text']}")
        if note.get("translation_zh"):
            lines.append(f"\n> **中文翻译**：{note['translation_zh']}")
        if note.get("role"):
            lines.append(f"\n- **段落作用解析**：{note['role']}")
        if note.get("plain_explanation"):
            lines.append(f"- **零基础大白话**：{note['plain_explanation']}")
        if s.get("refs"):
            lines.append(f"- **本段引用文献**：{', '.join(f'[Ref {r}]' for r in s['refs'])}")

    # Resources
    if resources.get("github") or resources.get("web_tools"):
        lines.append("\n## 四、自动抓取的关联代码仓与资源")
        for g in resources.get("github", []):
            lines.append(f"- **GitHub**: [{g['repo']}]({g['url']}) — {g.get('description', '')}")
        for t in resources.get("web_tools", []):
            lines.append(f"- **在线工具/数据库**: [{t['name']}]({t['url']})")

    # Critical notes
    if analysis.get("critical_notes"):
        lines.append("\n## 五、批判性审读与局限性")
        for c in analysis["critical_notes"]:
            lines.append(f"- {c}")

    return "\n".join(lines) + "\n"
